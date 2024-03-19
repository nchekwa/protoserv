#
# pip install protobuf
# apt install protobuf-compiler

protoc --python_out=. streaming-telemetry-schema.proto
