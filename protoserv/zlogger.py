import os
import logging
from logging.handlers import TimedRotatingFileHandler
from .utils import ensure_directory_exists


class ZLogger:
    def __init__(self):
        self.STD_LOGGER_LEVEL = getattr(logging, os.getenv('STD_LOGGER_LEVEL', 'INFO').upper())
        
        self.STD_LOGGER_FILE_OUTPUT_FILEPATH = os.getenv('STD_LOGGER_FILE_OUTPUT_FILEPATH', 'log/stdout.log')
        self.STD_LOGGER_FILE_ROTATION_WHEN = os.getenv('STD_LOGGER_FILE_ROTATION_WHEN', 'midnight')
        self.STD_LOGGER_FILE_ROTATION_INTERVAL = int(os.getenv('STD_LOGGER_FILE_ROTATION_INTERVAL', 1))
        self.STD_LOGGER_FILE_ROTATION_BACKUP_COUNT = int(os.getenv('STD_LOGGER_FILE_ROTATION_BACKUP_COUNT', 10))   # keep 10 files by default
        self.STD_LOGGER_FILE_LEVEL = getattr(logging, os.getenv('STD_LOGGER_FILE_LEVEL', 'INFO').upper())

        self.DATA_LOGGER_FILE_OUTPUT_FILEPATH = os.getenv('DATA_LOGGER_FILE_OUTPUT_FILEPATH', 'data/data_logger.txt')
        self.DATA_LOGGER_FILE_ROTATION_WHEN = os.getenv('DATA_LOGGER_FILE_ROTATION_WHEN', 'midnight')
        self.DATA_LOGGER_FILE_ROTATION_INTERVAL = int(os.getenv('DATA_LOGGER_FILE_ROTATION_INTERVAL', 1))
        self.DATA_LOGGER_FILE_ROTATION_BACKUP_COUNT = int(os.getenv('DATA_LOGGER_FILE_ROTATION_BACKUP_COUNT', 10))
        
    def std_logger(self):
         # Create a logger and default level
        self.stdlogger = logging.getLogger('stdlogger')
        self.stdlogger .setLevel(logging.DEBUG)

        self.stdlogger_stream_handler = logging.StreamHandler()
        self.stdlogger_stream_handler.setLevel(self.STD_LOGGER_LEVEL)
        self.stdlogger_stream_handler.setFormatter(logging.Formatter('%(message)s'))

        self.stdlogger_file_handler = TimedRotatingFileHandler(ensure_directory_exists(self.STD_LOGGER_FILE_OUTPUT_FILEPATH), 
                                                               when=self.STD_LOGGER_FILE_ROTATION_WHEN, 
                                                               interval=self.STD_LOGGER_FILE_ROTATION_INTERVAL, 
                                                               backupCount=self.STD_LOGGER_FILE_ROTATION_BACKUP_COUNT)
        self.stdlogger_file_handler.setLevel(self.STD_LOGGER_FILE_LEVEL)
        self.stdlogger_file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

        self.stdlogger.addHandler(self.stdlogger_file_handler)
        self.stdlogger.addHandler(self.stdlogger_stream_handler)
        
        return self.stdlogger
    
    def data_logger(self):
        self.datalogger = logging.getLogger('data_logger')
        self.datalogger.setLevel(logging.DEBUG)
        
        self.datalogger_file_handler = TimedRotatingFileHandler(ensure_directory_exists(self.DATA_LOGGER_FILE_OUTPUT_FILEPATH), 
                                                              when=self.DATA_LOGGER_FILE_ROTATION_WHEN, 
                                                              interval=self.DATA_LOGGER_FILE_ROTATION_INTERVAL, 
                                                              backupCount=self.DATA_LOGGER_FILE_ROTATION_BACKUP_COUNT)
        self.datalogger_file_handler.setLevel(logging.DEBUG)
        self.datalogger_file_handler.setFormatter(logging.Formatter('%(message)s'))
        
        self.datalogger.addHandler(self.datalogger_file_handler)
        return self.datalogger
    
    def info(self, *args):
        formatted_args = [arg.ljust(40) for arg in args]
        self.stdlogger.info(" | ".join(formatted_args))
        
        
        

    def set_std_logger_level(self, level):
        """Sets the overall log level for the standard logger.
        
        Args:
            level (str): The overall log level, e.g. 'INFO', 'DEBUG'. 
                Defaults to 'INFO' unless overridden by the environment variable STD_LOGGER_LEVEL.
        """
        self.STD_LOGGER_LEVEL = level
    
    def set_std_logger_file_output_filepath(self, path):
        """Sets the file output filepath for the standard logger.

        Args:
            path (str): The file path to write standard log output to. 
                Defaults to 'log/stdout.log' unless overridden by the environment variable STD_LOGGER_FILE_OUTPUT_FILEPATH.
        """
        self.STD_LOGGER_FILE_OUTPUT_FILEPATH = path
    
    def set_std_logger_file_rotation_when(self, when):
        """Sets the rotation schedule for the standard logger's file handler.
        
        Args:
            when (str): The rotation schedule, e.g. 'midnight'. 
                Defaults to 'midnight' unless overridden by the environment variable STD_LOGGER_FILE_ROTATION_WHEN.
        """
        self.STD_LOGGER_FILE_ROTATION_WHEN = when
    
    def set_std_logger_file_rotation_interval(self, interval):
        """Sets the rotation interval for the standard logger's file handler.
        
        Args:
            interval (int): The rotation interval in days. 
                Defaults to 1 unless overridden by the environment variable STD_LOGGER_FILE_ROTATION_INTERVAL.
        """
        self.STD_LOGGER_FILE_ROTATION_INTERVAL = interval
    
    def set_std_logger_file_rotation_backup_count(self, count):
        """Sets the backup count for the standard logger's file handler rotation.
        
        Args:
            count (int): The number of backup log files to retain. 
                Defaults to 10 unless overridden by the environment variable STD_LOGGER_FILE_ROTATION_BACKUP_COUNT.
        """
        self.STD_LOGGER_FILE_ROTATION_BACKUP_COUNT = count
    
    def set_std_logger_file_level(self, level):
        """Sets the log level for the standard logger's file handler.
        
        Args:
            level (str): The log level, e.g. 'INFO', 'DEBUG'. 
                Defaults to 'DEBUG' unless overridden by the environment variable STD_LOGGER_FILE_LEVEL.
        """
        self.STD_LOGGER_FILE_LEVEL = level

    def set_data_logger_file_output_filepath(self, path):
        """Sets the file output filepath for the data logger.

        Args:
            path (str): The file path to write data log output to. 
                Defaults to 'data/data_logger.txt' unless overridden by the environment variable DATA_LOGGER_FILE_OUTPUT_FILEPATH.
        """
        self.DATA_LOGGER_FILE_OUTPUT_FILEPATH = path
    
    def set_data_logger_file_rotation_when(self, when):
        """Sets the rotation schedule for the data logger's file handler.
        
        Args:
            when (str): The rotation schedule, e.g. 'midnight'. 
                Defaults to 'midnight' unless overridden by the environment variable DATA_LOGGER_FILE_ROTATION_WHEN.
        """
        self.DATA_LOGGER_FILE_ROTATION_WHEN = when
    
    def set_data_logger_file_rotation_interval(self, interval):
        """Sets the rotation interval for the data logger's file handler.
        
        Args:
            interval (int): The rotation interval in days. 
                Defaults to 1 unless overridden by the environment variable DATA_LOGGER_FILE_ROTATION_INTERVAL.
        """
        self.DATA_LOGGER_FILE_ROTATION_INTERVAL = interval
    
    def set_data_logger_file_rotation_backup_count(self, count):
        """Sets the backup count for the data logger's file handler rotation.
        
        Args:
            count (int): The number of backup log files to retain. 
                Defaults to 10 unless overridden by the environment variable DATA_LOGGER_FILE_ROTATION_BACKUP_COUNT.
        """
        self.DATA_LOGGER_FILE_ROTATION_BACKUP_COUNT = count
