import asyncio
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


class SaniTrendLogging:
    logger = logging.getLogger('STC_Logs')
    logger.setLevel(logging.DEBUG)
    logger_formatter = logging.Formatter('%(levelname)s-%(asctime)s: %(message)s')
    logger_handler = handlers.TimedRotatingFileHandler('stc.log', when='midnight', interval=1, backupCount=30)
    logger_handler.setFormatter(logger_formatter)
    logger.addHandler(logger_handler)
    async def add_log_entry(log_level, log_message) -> None:
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
        
        await log(log_level, log_message)
              
        
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


class STC:
    
    def __init__(self, config_file= 'SaniTrendConfig.json'):
        self.plc_config = {
            'delta': 0.495,
            'ipaddress': '',
            'path': '',
            'scan_rate': 1000,
            'tags': [],
            'virt_analog_tag' : '',
            'virt_digital_tag': '',
            'virt_string_tag': '',
            'virt_analog_enable': False,
            'virt_digital_enable': False,
            'virt_string_enable': False,
            'virt_tag_config': []
        }
        self.plc_data = []
        self.plc_data_buffer = []

        self.twx_config = {
            'headers': {
                'Connection': 'keep-alive',
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
        }

        self.twx_connected: bool = False
        self._twx_connection_session = requests.Session()
        self._twx_last_connection_test: int = 0
        self._twx_conn_test_in_progress: bool = False
    


    def plc_scan_timer(self,) -> bool:
        """PLC Scan Rate Timer\n
        Scan Rate set in config file

        Returns:
            bool: accumulated time >= timer preset
        """
        timer = SimpleTimer(self._plc_last_scan_time, self.plc_config['scan_rate'])
        if timer.DN:
            self._plc_last_scan_time = timer.timestamp
        return timer.DN
        
    
    def _twx_conn_timer(self,) -> bool:
        """Thingworx connection check timer

        Returns:
            bool: timer done
        """
        timer = SimpleTimer(self._twx_last_connection_test, 10000)
        if timer.DN:
            self._twx_last_connection_test = timer.timestamp
        return timer.DN


    async def get_twx_connection_status(self,) -> None:
        """Get Thingworx connection status
        """
        timer_done = self._twx_conn_timer()
        if timer_done and not self._twx_conn_test_in_progress:
            self._twx_conn_test_in_progress = True
            async def _get_twx_connection_status(self,) -> None:
                """asyncio function to make request to Thingworx EMS for isConnected Property
                """
                url = 'http://localhost:8000/Thingworx/Things/LocalEms/Properties/isConnected'
                try:
                    connection_response = self._twx_connection_session.get(url, headers=self.twx_config['headers'], timeout=5)
                    if  connection_response.status_code == 200:
                        self.twx_connected = (connection_response.json())['rows'][0]['isConnected']

                    else:
                        SaniTrendLogging.add_log_entry('error', connection_response)
                        self.twx_connected = False

                except Exception as e:
                    self.twx_connected = False
                    self._twx_last_connection_test = self._twx_last_connection_test + 30000
                    SaniTrendLogging.add_log_entry('error', e)

                self._twx_conn_test_in_progress = False

            asyncio.create_task(_get_twx_connection_status(self))

    def get_tag_data(self, tag_data: list = []) -> None:
        for tag in tag_data:
            add_tag = True
            if isinstance(tag.Value, float):
                tag.Value = round(tag.Value,2)
            for tag_buffer in self.data_buffer:
                if tag.TagName == tag_buffer.TagName:
                    add_tag = False
                    if isinstance(tag_buffer.Value, float):
                        difference = abs(tag.Value - tag_buffer.Value)
                        if difference > self.delta:
                            tag_buffer.Value = tag.Value
                    else:
                        if tag.Value != tag_buffer.Value:
                            tag_buffer.Value = tag.Value

                    continue
                    
            if add_tag:
                self.tag_data_buffer.append(tag)





class SaniTrendDatabase:
    """Class for database data logging
    """
    database: str = os.path.join(os.path.dirname(__file__), 'stc.db')
    logging_active: bool = False


async def main():
    test = STC()
    # test.get_twx_connection_status()
    asyncio.create_task(SaniTrendLogging.add_log_entry('warn', 'testing 1 2 3'))
    # await SaniTrendLogging.add_log_entry('warn', 'testing 1 2 3')
    print('test')

if __name__ == '__main__':
    asyncio.run(main())

# while True:
    # log_error('twx_connected', test.twx_connected)
    # time.sleep(10)