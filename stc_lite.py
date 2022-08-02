import asyncio
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
from logging import handlers
import math
import os
import platform
from typing import Any
import requests
import sqlite3
import sys
import time

@dataclass
class SaniTrendLogging():
    log_enable: bool = True
    logger = logging.getLogger('STC_Logs')
    logger.setLevel(logging.DEBUG)
    logger_formatter = logging.Formatter('%(levelname)s %(asctime)s - %(funcName)s: %(message)s')
    logger_handler = handlers.TimedRotatingFileHandler('stc.log', when='midnight', interval=1, backupCount=30)
    logger_handler.setFormatter(logger_formatter)
    logger.addHandler(logger_handler)
    def add_log_entry(log_level, log_message, log_enable: bool = True) -> None:
        if log_enable:
            async def log(log_level, log_message) -> None:
                level = log_level.lower()
                log_levels = [
                    {
                        'log_level_logger': SaniTrendLogging.logger.debug,
                        'search': [
                            'de',
                            'bug'
                        ]
                    },
                    {
                        'log_level_logger': SaniTrendLogging.logger.info,
                        'search': [
                            'in',
                            'fo'
                        ]
                    },
                    {
                        'log_level_logger': SaniTrendLogging.logger.warning,
                        'search': [
                            'war',
                            'arn'
                        ]
                    },
                    {
                        'log_level_logger': SaniTrendLogging.logger.error,
                        'search': [
                            'er',
                            'or'
                        ]
                    },
                    {
                        'log_level_logger': SaniTrendLogging.logger.critical,
                        'search': [
                            'cr',
                            'it'
                        ]
                    }
                ]

                log_level_to_use = SaniTrendLogging.logger.info
                for log_dict in log_levels:
                    for search_term in log_dict['search']:
                        if level.find(search_term) > -1:
                            log_level_to_use = log_dict['log_level_logger']
                            break
                
                log_level_to_use(log_message)
            
            asyncio.run(log(log_level, log_message))



class SimpleTimer():
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
    delta: float = 0.49
    plc_ipaddress: str = ''
    plc_path: str = ''
    plc_scan_rate: int = 1000
    tags: list = field(default_factory=list)
    tag_data: list = field(default_factory=list)
    tag_data_buffer: list = field(default_factory=list)
    virtual_analog_input_tag: str = ''
    virtual_digital_input_tag: str = ''
    virtual_string_tag: str = ''
    virtual_analog_inputs_enable: bool = False
    virtual_digital_inputs_enable: bool = False
    virtual_string_input_enable: bool = False
    virtual_tag_config: list = field(default_factory=list)
    
    def plc_scan_timer(self,preset: int = plc_scan_rate) -> bool:
        """simple looping timer

        Args:
            preset (int, optional): Timer preset in milliseconds. Defaults to plc_scan_rate.

        Returns:
            bool: accumulated time >= timer preset
        """
        timer = SimpleTimer(self._plc_last_scan_time, self.plc_scan_rate)
        if timer.DN:
            self._plc_last_scan_time = timer.timestamp
        return timer.DN

    def set_tag_data_buffer(self) -> None:
        pass


@dataclass
class Thingworx:
    """Thingworx class
    """
    http_headers = {
        'Connection': 'keep-alive',
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

    twx_connected: bool = False
    thingworx_session = requests.Session()
    _twx_last_connection_test: int = 0
    _twx_conn_test_in_progress: bool = False

    def twx_conn_timer(self,) -> bool:
        timer = SimpleTimer(self._twx_last_connection_test, 10000)
        if timer.DN:
            self._twx_last_connection_test = timer.timestamp
        return timer.DN

    def get_twx_connection_status(self) -> None:
        timer_dn = self.txw_conn_timer()
        if timer_dn and not self._twx_conn_test_in_progress:
            self._twx_conn_test_in_progress = True
            async def _get_twx_connection_status(self) -> None:
                url = 'http://localhost:8000/Thingworx/Things/LocalEms/Properties/isConnected'
                try:
                    connection_response = self._connection_status_session.get(url, headers=self.headers, timeout=5)
                    if  connection_response.status_code == 200:
                        self.twx_connected = (connection_response.json())['rows'][0]['isConnected']

                    else:
                        SaniTrendLogging.add_log_entry('error', connection_response)
                        self.twx_connected = False

                except Exception as e:
                    self.twx_connected = False
                    self._twx_last_connection_test = self._twx_last_connection_test + 30000

                self._twx_conn_test_in_progress = False


        
        

@dataclass
class SaniTrendCloud(SaniTrendLogging, SaniTrendPLC, Thingworx):
    pass
    




def main():
    # sanitrend_logger.log_error('test', 'test123')
    SaniTrendLogging.add_log_entry('info', 'test123')

if __name__ == '__main__':
    main()

# while True:
    # log_error('twx_connected', test.twx_connected)
    # time.sleep(10)