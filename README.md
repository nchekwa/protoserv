# protoserv
Apstra Protobuf Servere Decode Messages (and save to text file / or transmit via WebSocket)

### Before you start
'streaming-telemetry-schema.proto' file from Apstra Servere is required to be transform to .py lib based on "proto2py.sh" file (ie. inside folder proto/4.2.1/streaming-telemetry-schema.proto).

### Run
Build and run in interactive mode:
```
docker-compose up
```
This will build based on Docerfile and start the protoserv container which runs a Protobuf server listening on port 4444 for Protobuf messages. It will decode any received messages and log stats to the console and save decoded data to a DATA_LOGGER_FILE_OUTPUT_FILEPATH (default: data/protoserv.data.log).
<img src=docs/img/protoserv.png>
Websocket is also started on port 8765 and any received messages from protobuf are decoded and broadcast to all websocket clients.
The protobuf message types and schemas are defined in proto/4.x.x folder. Ensure that file 'proto/4.x.x/streaming_telemetry_schema_pb2.py' exist before you start (Run).
