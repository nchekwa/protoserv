from typing import Union, Dict, Set

class Buffer:        
    def __init__(self, buffer:Dict = None):
        if buffer == None:
            self.buffer = {}
        else:
            self.buffer = buffer

    def get_size(self, session_id) -> int:
        return(len(self.buffer[session_id]))

    def append(self, session_id, data) -> int:
        self.buffer[session_id] += data
        return(len(self.buffer[session_id]))

    def get(self, session_id, number_of_elements = 0) -> bytes:
        if number_of_elements == 0:
            return b''
        else:
            return bytes(self.buffer[session_id][:number_of_elements])
        
    def get_range(self, session_id, start_element=0, end_elements = 0) -> bytes:
        if end_elements == 0:
            return b''
        else:
            return bytes(self.buffer[session_id][start_element:end_elements])

    def remove_elements(self, session_id, number_of_elements: int) -> int:
        if number_of_elements == 0:
            return len(self.buffer[session_id])
        else:
            self.buffer[session_id] = self.buffer[session_id][number_of_elements:]
        return len(self.buffer[session_id])
    
    def get_sessions(self) -> list:
        return list(self.buffer.keys())
    
    def create_session(self, session_id) -> bool:
        self.buffer[session_id] = []
        return True
    
    def destroy_session(self, session_id) -> bool:
        self.buffer.pop(session_id, None)
        return True