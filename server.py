#!/usr/bin/env python


import os
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

import socket
import threading
import time
import signal
import sys
import binascii
import json
import logging
import argparse
import gc
import asyncio


from protoserv import WSServer, Buffer, ZLogger
from protoserv.utils import get_current_datetime, ensure_directory_exists, encode_address, decode_address

from google.protobuf.internal.decoder import _DecodeVarint
from google.protobuf.json_format import MessageToDict

# -----------------------------------------------
# Parameters
client_socket_timeout=21600         # 6h

LOG_REFRESH_INTERVAL             = int(os.getenv('LOG_REFRESH_INTERVAL', 5))  # 5 sec


# -----------------------------------------------
# Internal variables
server_socket = None  # Global variable for the server socket
shutdown_flag = False  # Flag to indicate shutdown process
accept_thread = None  # Global variable to hold the accept thread

msg_counter = {}
decoded_sessions = {}
stream_mode = {}

pb2buffer = Buffer()


# -----------------------------------------------
# Signal Handler
def signal_handler(sig, frame):
    global shutdown_flag, accept_thread, ws_server
    if not shutdown_flag:
        logger.info("Signal Handler -> Shutting down... please wait for propere close socket... ")
        shutdown_flag = True
        ws_server.shutdown_server()
        if accept_thread:
            accept_thread.join()  # Wait for the accept thread to terminate
        if server_socket:
            server_socket.close()
        sys.exit(0)
    
#-----------------------------------------------
# Thread Connection Socket
#  continuously check for new connections, accept them, and start threads to receive data from each client.
def accept_connections():
    global server_socket, shutdown_flag, decoded_sessions, client_socket_timeout
    while not shutdown_flag:
        try:
            client_socket, client_address = server_socket.accept()
            client_socket.settimeout(client_socket_timeout)
            client_ip, client_port = client_address # Unpack client address tuple
            session_id = encode_address(client_ip,client_port)
            decoded_sessions[session_id] = f"{client_ip}:{client_port}"
            zlogger.info(f"> protobuf client {decoded_sessions.get(session_id)}", 
                        f"new connection", 
                        f"{get_current_datetime()}")
            threading.Thread(target=receive_data, args=(client_socket,session_id,), daemon=True).start()
        except socket.timeout as e:
            # server_socket is set as server_socket.settimeout(1) -> 1sec (nessesery for propere way of kiiling thread)
            # we not react on timeouts from servere to allow constance accept of connections
            # just keep running the loop and accept connections all the time
            pass
        except e:
            logger.error(f"accept_connections error: {str(e)}")
        #time.sleep(0.01)

def receive_data(client_socket,session_id):
    global msg_counter, decoded_sessions
    
    if session_id not in pb2buffer.get_sessions():
        zlogger.info(f"> protobuf client {decoded_sessions.get(session_id)}", 
                    f"buffer size: 0", 
                    f"count: 0")
        pb2buffer.create_session(session_id)
        msg_counter[session_id] = 0
        stream_mode[session_id] = None
    
    stop_event_pb2_consumer = threading.Event()
    threading.Thread(target=pb2_consumer, args=(session_id,stop_event_pb2_consumer), daemon=True).start()

    while True:
        try:
            data = client_socket.recv(8196)  # Receive up to 1024 bytes of data
            if not data:  # If no data is received, break the loop
                time.sleep(0.01)
                logger.info(f"... no data - break : {session_id} | {get_current_datetime()}")
                break
            b0 = pb2buffer.get_size(session_id)
            pb2buffer.append(session_id, data)
            b1 = pb2buffer.get_size(session_id)
            zlogger.info(f"> protobuf client {decoded_sessions.get(session_id)}", 
                        f"sock.recv: {len(data)}", 
                        f"buffer size: {b0} -> {b1}")
        except socket.timeout:
            # Do not close connection from client
            # just report error and continue
            logger.warning(f"client socket timeout : {session_id} | {get_current_datetime()}")
            pass

    pb2buffer.destroy_session(session_id)
    stream_mode[session_id] = None
    stop_event_pb2_consumer.set()
    client_socket.close()
    return


#-----------------------------------------------


def decode_first_uint64_field(byte_stream):
    """Decode the first uint64 field from a byte stream."""
    pos = 0
    while pos < len(byte_stream):
        # Decode the field number and wire type
        field_wire_type, pos = _DecodeVarint(byte_stream, pos)
        field_number = field_wire_type >> 3
        wire_type = field_wire_type & 0x07
        
        # Check if the wire type is compatible with varint encoding and field number is the first field
        if wire_type == 0 and field_number == 1:
            # Decode the uint64 value
            uint64_value, pos = _DecodeVarint(byte_stream, pos)
            return uint64_value
        else:
            # Skip the field value based on wire type
            if wire_type == 0:  # Varint
                _, pos = _DecodeVarint(byte_stream, pos)
            elif wire_type == 2:  # Length-delimited
                field_length, pos = _DecodeVarint(byte_stream, pos)
                pos += field_length
            else:
                raise ValueError("Unsupported wire type")
    
    raise ValueError("No uint64 field found")

def recognize_stream_mode(msg_bytes) -> int:
    varint_value = decode_first_uint64_field(msg_bytes)
    if varint_value > 1700000000000000:
        stream_mode = 'unsequenced'
    else:
        stream_mode = 'sequenced'
    return stream_mode
    

#-----------------------------------------------
# Protobuf Deserialize
def pb2_msg_slicer(session_id) -> str:
    buf = pb2buffer.get_range(session_id, 0, 200)
    logger.debug(f"pb2buffer-debug - session: {session_id}")
    logger.debug(f"pb2buffer-debug - full 200 bytes")
    logger.debug(f"pb2buffer-debug : {buf}")
    logger.debug(f"pb2buffer-debug-int : {int.from_bytes(buf, byteorder='big') }")
    logger.debug(f"pb2buffer-debug-hex : {binascii.hexlify(buf).decode()}")
    
    logger.debug(f"--- pb2buffer size on start: {pb2buffer.get_size(session_id)}")
    logger.debug(f"--- Search... for next Varint...")


    buf = pb2buffer.get_range(session_id, 0, 2)
    logger.debug(f"buf: {buf} - int: {int.from_bytes(buf, byteorder='big') } - hex: {binascii.hexlify(buf).decode()}")
    msg_len = int(binascii.hexlify(buf), 16)
    logger.debug(f"-msg_len: {msg_len}")
    csize = pb2buffer.get_size(session_id)
    if msg_len+2 > csize:
        logger.error(f"Error - buffer too low - need to wait - we have truncated message in the pb2buffer: msg_len: {msg_len} > pb2buffer: {csize}")
        return b''

    logger.debug("")
    full_msg = pb2buffer.get_range(session_id, 0, 2+msg_len)
    logger.debug(f"full_msg_lenght: {msg_len+2}")
    logger.debug(f"full_msg: {full_msg}")
    logger.debug(f"full_msg_hex: {binascii.hexlify(full_msg).decode()}")
    
    logger.debug("")
    msg = pb2buffer.get_range(session_id, 2, msg_len+2)
    logger.debug(f"msg_real_lenght: {len(msg)}")
    logger.debug(f"msg: {msg}")
    logger.debug(f"msg_hex: {binascii.hexlify(msg).decode()}")

    logger.debug("")
    logger.debug(f"---> remove from pb2buffer {2+msg_len} bytess")
    
    pb2buffer.remove_elements(session_id, msg_len+2)
    msg_counter[session_id] += 1

    return msg

def pb2_decoder(message, output_type="dict", json_sort_keys=False, source = None):
    """Decodes a protobuf message into a Python dict or JSON string.

    Args:
    message: The protobuf message to decode.
    output_type: The desired output format. Can be 'dict', 'json', or 'json4'.

    Returns:
    The decoded message in the requested format.
    """
    global decoded_sessions
    result_dict = MessageToDict(message, preserving_proto_field_name=True)

    if 'aos_proto' in result_dict and 'seq_num' in result_dict:
        nested_message = streaming_telemetry_schema_pb2.AosMessage()
        nested_message.ParseFromString(message.aos_proto)
        seq = result_dict['seq_num']
        result_dict = pb2_decoder(nested_message, output_type='dict')
        result_dict['seq_num'] = seq

    if 'seq_num' not in result_dict:
        result_dict['seq_num'] = 0

    if source is not None:
        result_dict['source'] = decoded_sessions[source]
        
    if output_type == "json":
        result = json.dumps(result_dict, sort_keys=json_sort_keys)
    elif output_type == "json4":
        result = json.dumps(result_dict, indent=4, sort_keys=json_sort_keys)
    elif output_type == "dict":
        result = result_dict
    else:
        raise ValueError("Invalid output_type. Choose either 'dict', 'json', or 'json4'.")

    return result

def pb2_consumer(session_id, stop_event):
    global stream_mode, pb_logger
    msg_no = 0
    while not stop_event.is_set():
        csize = pb2buffer.get_size(session_id)
        if csize > 4:
            try:
                msg = pb2_msg_slicer(session_id)
                logger.debug(f"pb2_consumer msg: {msg}")
                logger.debug(f"pb2_consumer stream_mode: {stream_mode[session_id]}")
                if len(msg) == 0:
                    time.sleep(0.005)
                    continue
                msg_length = int(len(msg))+2


                if stream_mode[session_id] == None:
                    stream_mode[session_id] = recognize_stream_mode(msg)
                    logger.debug(f"Stream mode detected as: {stream_mode[session_id]}")

                if stream_mode[session_id] == "sequenced":
                    pb2Message = streaming_telemetry_schema_pb2.AosSequencedMessage()
                    pb2Message.ParseFromString(msg)
                
                if stream_mode[session_id] == "unsequenced":
                    pb2Message = streaming_telemetry_schema_pb2.AosMessage()
                    pb2Message.ParseFromString(msg)
                
                if zlogger.STD_LOGGER_FILE_LEVEL <= logging.DEBUG or zlogger.STD_LOGGER_FILE_LEVEL <= logging.DEBUG:
                    pb_dec = pb2_decoder(pb2Message, output_type="json4", source=session_id)
                    logger.debug(pb_dec)
                
                # File storage or publish to downstream systems
                if pb_logger_file_output_format is not None:
                    pb_dec = pb2_decoder(pb2Message, output_type=pb_logger_file_output_format, source=session_id)
                    pb_logger.info(pb_dec)
                
                asyncio.run(ws_server.send_message(pb_dec))
                
                msg_no+=1
                zlogger.info(f"> protobuf client {decoded_sessions.get(session_id)}", 
                            f"buffer size: {csize}", 
                            f"consumed: msg {msg_no} size {msg_length}")
            except Exception as e:
                logger.error(f"Error Exception 2 -> {str(e)}")
                time.sleep(LOG_REFRESH_INTERVAL)
        # Keep CPU more quiet...
        if csize == 0:
            msg_no = 0
            zlogger.info(f"> protobuf client {decoded_sessions.get(session_id)}", 
                        f"buffer size: {csize}", 
                        f"nothing to do... waiting...")
            time.sleep(LOG_REFRESH_INTERVAL)       
                
    # Set stop_event to signal thread to stop
    stop_event.set()    

      
def main():
    global shutdown_flag, server_socket, accept_thread

    # Create a TCP/IP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Set SO_REUSEADDR option 
    server_socket.bind((ip_address, int(port)))
    server_socket.listen(1)
    server_socket.settimeout(1)  # Set timeout to handle KeyboardInterrupt gracefully

    logger.info(f"protobuf server: {ip_address}:{port}")
    
    # Start accepting connections in a separate thread
    accept_thread = threading.Thread(target=accept_connections, daemon=True)
    accept_thread.start()

    # Keep reporting status until shutdown
    while True:
        prefix = f"#--- stats ---> {get_current_datetime()}"
        padding = '-' * max(150 - len(prefix), 0)  
        logger.info(f"{prefix} {padding}")
        
        for session_id in pb2buffer.get_sessions():
            zlogger.info(f"# protobuf client {decoded_sessions.get(session_id)}", 
                        f"buffer size: {pb2buffer.get_size(session_id)}", 
                        f"consumed: {msg_counter[session_id]} msg")
        for ws_client in ws_server.get_connected_clients():
            zlogger.info(f"# ws client {ws_client.ip}:{ws_client.port}", 
                        f"socket rx: {ws_client.rx} msg", 
                        f"socket tx: {ws_client.tx} msg")
        
        prefix = f"#--->"
        padding = '-' * max(150 - len(prefix), 0)  
        logger.info(f"{prefix} {padding}")
        
        gc.collect()
        logger.debug(f"garbage collection> {gc.get_stats()}")
        time.sleep(LOG_REFRESH_INTERVAL) # Check sessions periodically


if __name__ == "__main__":
    # Set up signal handler for SIGINT (Ctrl+C)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create an ArgumentParser object
    parser = argparse.ArgumentParser(description="Process some arguments")
    parser.add_argument("--apstra-version", default=os.getenv('APSTRA_VERSION', '4.2.1'), help="Specify Apstra version. Default: 4.2.1")
    parser.add_argument("--port", default=os.getenv('LISTEN_PORT', 4444), help="Specify port number to listen on. Default: 4444")
    parser.add_argument("--ip-address", default=os.getenv('LISTEN_IPADDRESS', "0.0.0.0"), help="Specify IP address to listen on. Default: 0.0.0.0")
    parser.add_argument("--pb-logger-file-output-format", default=os.getenv('PB_LOGGER_FILE_OUTPUT_FORMAT', "json"), help="Specify data log format: json, json4, dict. Default: json")

    # Retrieve values from Args
    args = parser.parse_args()
    apstra_version = args.apstra_version
    port = args.port
    ip_address = args.ip_address
    pb_logger_file_output_format = args.pb_logger_file_output_format
    
    # Get the directory where the current schema is located
    script_dir = os.path.dirname(os.path.realpath(__file__))
    print(f"Script dir: {script_dir}")
    proto_dir = os.path.join(script_dir, 'proto', apstra_version)
    print(f"Proto dir path: {proto_dir}")
    sys.path.append(proto_dir)
    for path in sys.path:
        print(path)
    import streaming_telemetry_schema_pb2

    # Create a logger and default level
    zlogger = ZLogger()
    zlogger.set_std_logger_file_output_filepath(os.getenv('STD_LOGGER_FILE_OUTPUT_FILEPATH', 'log/protoserv.log'))
    zlogger.set_data_logger_file_output_filepath(os.getenv('STD_LOGGER_FILE_OUTPUT_FILEPATH', 'data/protoserv.data.log'))
    logger = zlogger.std_logger()
    pb_logger = zlogger.data_logger()

    # Start WebSocket Server-Transmiter
    ws_server = WSServer(logger=logger)
    ws_server.start_server()
    if ws_server.get_server_status() == False:
        signal_handler(signal.SIGINT, None)

    main()



# ----------
# APSTRA_VERSION
# LISTEN_PORT
# LISTEN_IPADDRESS

# LOGGER_LEVEL

# LOGGER_FILE_PATH
# LOGGER_FILE_LEVEL
# LOGGER_FILE_ROTATION_INTERVAL
# LOGGER_FILE_ROTATION_BACKUP_COUNT
# LOGGER_FILE_ROTATION_WHEN

# PB_FILE_OUTPUT_PATH
# PB_LOGGER_FILE_ROTATION_INTERVAL
# PB_LOGGER_FILE_ROTATION_WHEN
# PB_LOGGER_FILE_ROTATION_BACKUP_COUNT
# PB_LOGGER_FILE_OUTPUT_FORMAT

# If backupCount is > 0, when rollover is done, no more than backupCount files are kept - the oldest ones are deleted.