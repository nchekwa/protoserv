import asyncio
import threading
import websockets
import logging
from websockets.legacy.server import WebSocketServerProtocol
from typing import Set

from typing import Union
from dataclasses import dataclass

@dataclass
class ClientStats:
    ip: str
    port: int
    rx: int = 0
    tx: int = 0
    
    def __post_init__(self):
        if self.rx is None:
            self.rx = 0
        if self.tx is None:
            self.tx = 0

class AddressAlreadyInUseError(Exception):
    pass




class WSServer:
    def __init__(self, listen_ip="0.0.0.0", port=8765, logger=None):
        self.msg_counter = {}
        self.listen_ip = listen_ip
        self.listen_port = port
        self.shutdown_flag = False
        self.server_thread = None
        self.server_running = False
        self.connected_clients:Set[WebSocketServerProtocol] = set()
        self.logger = logger if logger else self._create_default_logger()

    async def websocket_server(self):
        try:
            self.logger.info(f"ws server: {self.listen_ip}:{self.listen_port}")
            async with websockets.serve(self.handler, self.listen_ip, self.listen_port):
                self.server_running = True
                while not self.shutdown_flag:
                    await asyncio.sleep(1)
                self.logger.info("WebSocket Server going down....")
        except OSError as e:
            self.server_running = False
            self.logger.error(f"Failed to start server: {e}")
            raise AddressAlreadyInUseError("Address already in use.")
            
    async def handler(self, incoming_websocket: WebSocketServerProtocol, path: str):
        self.connected_clients.add(incoming_websocket)
        client_ip, client_port = incoming_websocket.remote_address
        self.logger.info(f"> ws client: {client_ip}:{client_port} - incomming connection")
        try:
            async for message in incoming_websocket:
                self.logger.debug(f"ws client: {client_ip}:{client_port} - received msg: {message}")
                await self.msg_handler(incoming_websocket, message)
        finally:
            self.logger.info(f"   > ws client disconnected: {client_ip}:{client_port} - disconnected")
            self.connected_clients.remove(incoming_websocket)
        
    async def msg_handler(self, incoming_websocket: WebSocketServerProtocol, message):
        # Only allow send message from localhost connected websocket
        # all othere ignore / log
        incoming_client_ip, incoming_client_port = incoming_websocket.remote_address
        self.client_stats_update(incoming_client_ip, incoming_client_port, "rx")
        if incoming_client_ip != '127.0.0.1':
            self.logger.error(f"websocket msg from {incoming_client_ip}:{incoming_client_port} not allowed - msg: {message}")
            return
        else:
            for client_websocket in self.connected_clients:
                client_ip, client_port = client_websocket.remote_address
                if incoming_websocket != client_websocket:
                    self.client_stats_update(client_ip, client_port, "tx")
                    self.logger.debug(f"websocket msg from {incoming_client_ip}:{incoming_client_port}->{client_ip}:{client_port} - msg: {message}")
                    await client_websocket.send(message)
    
    async def send_message(self, message):
        # this is python method for send message to all connected clientts
        for client_websocket in self.connected_clients:
            client_ip, client_port = client_websocket.remote_address
            self.client_stats_update(client_ip, client_port, "tx")
            # Get the event loop associated with the current thread
            loop = asyncio.get_event_loop()
            # Use the event loop to send the message
            await loop.create_task(client_websocket.send(message))
            
    def client_stats_update(self, ip, port, direction="tx"):
        session_key = f"{ip}:{port}:{direction}"
        if session_key not in self.msg_counter:
            self.msg_counter[session_key] = 1
        else:
            self.msg_counter[session_key] += 1
    def start_server(self):
        try:
            self.server_thread = threading.Thread(target=self._run_server)
            self.server_thread.start()
        except AddressAlreadyInUseError:
            pass


    def _run_server(self):
        self.server_running = True
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.websocket_server())
        except AddressAlreadyInUseError:
            self.logger.error("Address already in use, terminating")
            pass

    def shutdown_server(self):
        self.shutdown_flag = True
        if self.server_thread:
            self.server_thread.join()

    def get_server_status(self):
        return self.server_running
    
    def get_connected_clients(self) -> ClientStats:
        rlist = []
        for client in self.connected_clients:
            client_ip, client_port = client.remote_address
            session_key = f"{client_ip}:{client_port}"
            c = ClientStats(ip=client_ip, port=client_port, rx=self.msg_counter.get(f"{session_key}:rx"), tx=self.msg_counter.get(f"{session_key}:tx"))
            rlist.append(c)
        return rlist

    def _create_default_logger(self):
        logger = logging.getLogger('logger')
        logger.setLevel(logging.DEBUG)

        logger_stream_handler = logging.StreamHandler()
        logger_stream_handler.setLevel(logging.INFO)  # Adjust level as needed
        logger_stream_handler.setFormatter(logging.Formatter('%(message)s'))

        logger.addHandler(logger_stream_handler)

        return logger


# Usage:
# from protoserv import WSServer

# Create an instance of the server
# ws_server = WSServer()

# Start the server
# ws_server.start_server()

# To shutdown the server
# ws_server.shutdown_server()
