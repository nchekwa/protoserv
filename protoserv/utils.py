#from datetime import timedelta
from datetime import datetime
import os
from ipaddress import IPv4Address
from typing import Tuple

def get_current_datetime():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_directory_exists(file_path):
    """Ensure that the directory containing the file exists."""
    directory = os.path.dirname(file_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    return str(file_path)


#-----------------------------------------------
# IP+Port Encoder/Decoder
def encode_address(ip, port) -> int:
    ip_int = int(IPv4Address(ip))
    return (ip_int << 16) | port

def decode_address(encoded: int) -> Tuple[str, int]:
    ip_int = encoded >> 16
    port = encoded & 0xFFFF
    ip = IPv4Address(ip_int)
    return str(ip), port