from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
from logging import handlers
import math
import os
import platform
import requests
from sqlite3 import connect
import threading
import time



class TimerResponse():
    def __init__(self, entered_time: int = 0, preset: int = 0):
        self.ACC = 0
        self.DN = False
        self.timestamp = 0
        self._simple_timer(entered_time, preset)
    
    def _simple_timer(self,entered_time, preset) -> None:
        """Allen-Bradley PLC Timer replica

        Args:
            entered_time (int, optional): timestamp in milliseconds. Defaults to 0.
            preset (int, optional): preset in milliseconds. Defaults to 0.

        Returns:
            None: 
        """
        current_datetime = int(round(time.time() * 1000))
        time_elapsed = current_datetime - entered_time
        self.ACC = time_elapsed
        self.timestamp = current_datetime
        self.DN = True if time_elapsed >= preset else False
            



class SaniTrendLogging:
    # Set up error logger
    stc_error_log_enable = True
    stc_error_logger = logging.getLogger('STC_Errors')
    stc_error_logger.setLevel(logging.WARN)
    stc_error_logger_formater = logging.Formatter('%(asctime)s: %(message)s')
    stc_error_logger_file_handler = handlers.TimedRotatingFileHandler('errors.log', when='midnight', interval=1, backupCount=30)
    stc_error_logger_file_handler.setFormatter(stc_error_logger_formater)
    stc_error_logger.addHandler(stc_error_logger_file_handler)

    # Set up data logger
    stc_data_log_enable = True
    stc_data_logger = logging.getLogger('STC_Data')
    stc_data_logger.setLevel(logging.INFO)
    stc_data_logger_formater = logging.Formatter('%(asctime)s: %(message)s')
    stc_data_logger_file_handler = handlers.TimedRotatingFileHandler('data.log', when='midnight', interval=1, backupCount=30)
    stc_data_logger_file_handler.setFormatter(stc_data_logger_formater)
    stc_data_logger.addHandler(stc_data_logger_file_handler)

    def log_error(self, name, message) -> None:
        """Threading wrapper to log errors using python built-in logging

        Args:
            name (str): name of function calling error log (ex. __name__)
            message (str): error message
        """
        if self.stc_error_log_enable:
            log_message = f'{name} - {message}'
            threading.Thread(target=self._log_error(log_message)).start()
        
    def _log_error(self, message) -> None:
        """Threaded execution of error log

        Args:
            message (str): error message
        """
        self.stc_error_logger.error(message)

    def log_data(self, data: list = []) -> None:
        """Threading wrapper to log data using python built-in logging

        Args:
            data (list, optional): data to be logged. Defaults to [].
        """
        if self.stc_data_log_enable:
            message = ''
            for i in data:
                message = message + f'{i}, '
            threading.Thread(target=self._log_data(self, message)).start()
        
    def _log_data(self, message) -> None:
        """Threaded execution of data log

        Args:
            message (str): data to be logged
        """
        self.stc_data_logger.info(message)
# Initialize the Logger
SaniTrend_Logger = SaniTrendLogging()




@dataclass
class SaniTrendDatabase:
    """Class for database data logging
    """
    database: str = os.path.join(os.path.dirname(__file__), 'stc.db')
    logging_active: bool = False




@dataclass
class SaniTrendPLC:
    """PLC communication class
    """
    plc_ipaddress: str = ''
    plc_path: str = ''
    plc_scan_rate: int = 1000
    tags: list = field(default_factory=list)
    tag_data: list = field(default_factory=list)
    virtual_analog_input_tag: str = ''
    virtual_digital_input_tag: str = ''
    virtual_string_tag: str = ''
    virtual_analog_inputs_enable: bool = False
    virtual_digital_inputs_enable: bool = False
    virtual_string_input_enable: bool = False
    virtual_tag_config: list = field(default_factory=list)
    _plc_last_scan_time = 0

    def plc_scan_timer(self,preset: int = plc_scan_rate) -> bool:
        """simple looping timer

        Args:
            preset (int, optional): Timer preset in milliseconds. Defaults to plc_scan_rate.

        Returns:
            bool: accumulated time >= timer preset
        """
        timer = TimerResponse(self._plc_last_scan_time, preset)
        if timer.DN:
            self._plc_last_scan_time = timer.timestamp
        return timer.DN




@dataclass
class Thingworx:
    """Thingworx connectivity class
    """
    headers = {
        'Connection': 'keep-alive',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    twx_connected: bool = False
    thingworx_session = requests.Session()
    _twx_last_connection_test: int = 0
    _twx_conn_test_in_progress: bool = False
    
    def twx_conn_timer(self, preset: int = 4000) -> bool:
        """simple looping timer

        Args:
            preset (int, optional): Timer preset in milliseconds. Defaults to 4000.

        Returns:
            bool: accumulated time >= timer preset
        """
        timer = TimerResponse(self._twx_last_connection_test, preset)
        if timer.DN:
            self._twx_last_connection_test = timer.timestamp
        return timer.DN

    def get_twx_connection_status(self, preset: int = 5) -> None:
        """Threading wrapper function to check for Thingworx connectivity.

        Args:
            preset (int, optional): Seconds to repeat check for connectivity. Defaults to 5.
        """
        if not self._twx_conn_test_in_progress:
            current_ms_time = get_ms_time()
            time_accumulated = current_ms_time - self._twx_last_connection_test
            if time_accumulated > preset:
                self._twx_conn_test_in_progress = True
                self._twx_last_connection_test = current_ms_time
                threading.Thread(target=self._get_twx_connection_status).start()

    def _get_twx_connection_status(self,) -> None:
        """Threaded function for Thingworx connectivity check
        """
        url = 'http://localhost:8000/Thingworx/Things/LocalEms/Properties/isConnected'
        
        try:
            connection_response = self._connection_status_session.get(url, headers=self.headers, timeout=30)
            if  connection_response.status_code == 200:
                self.twx_connected = (connection_response.json())['rows'][0]['isConnected']

            else:
                SaniTrend_Logger.log_error(__name__, connection_response)
                self.twx_connected = False

        except Exception as e:
            self.twx_connected = False
            self._twx_last_connection_test = get_ms_time() + 30000

        self._twx_conn_test_in_progress = False

        
        
@dataclass
class SaniTrendCloud(SaniTrendDatabase, Thingworx, SaniTrendPLC):
    """Set up initial SaniTrend™ Cloud class that will hold all the data in memory that is needed.
    """
    
    # def __post_init__(self):
    #     self.plc_path = 'test'
    #     self.connection_headers = 
    # twxData: list = field(default_factory=list)
    




def main():
    # sanitrend_logger.log_error('test', 'test123')
    SaniTrend_Logger.log_error('test', 'test123')

if __name__ == '__main__':
    main()

# while True:
    # log_error('twx_connected', test.twx_connected)
    # time.sleep(10)