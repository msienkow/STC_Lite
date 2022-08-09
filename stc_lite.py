import asyncio
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
from logging import handlers
import math
import os
import platform
from unittest import result
import requests
import sqlite3
import sys
import time


class SaniTrendLogging:
    logger = logging.getLogger("STC_Logs")
    logger.setLevel(logging.DEBUG)
    logger_formatter = logging.Formatter("%(levelname)s %(asctime)s: %(funcName)s @ line %(lineno)d - %(message)s")
    logger_handler = handlers.TimedRotatingFileHandler("stc.log", when="midnight", interval=1, backupCount=30)
    logger_handler.setFormatter(logger_formatter)
    logger.addHandler(logger_handler)


@dataclass
class SimpleTimer():
    '''Simple timer class that mimics a PLC timer instruction.'''
    compare_time: int = field(repr = False)
    preset: int = field(repr = False)
    done: bool = field(init=False)
    timestamp: int = field(init=False)

    def __post_init__(self):
        self.timestamp = int(round(time.time() * 1000))
        self.done = True if (self.timestamp - self.compare_time) >= self.preset else False


        
@dataclass
class STC:
    plc_tag_data: list = field(default_factory = list)
    plc_data: list = field(default_factory = list)
    plc_tag_list: list = field(default_factory = list)
    plc_tag_delta: float = 0.495,
    plc_ip_address: str = ''
    plc_path: str = ''
    plc_scan_rate: int = 1000
    plc_last_scan_time: int = 0
    
    plc_analog_tag: str = ''
    plc_digital_tag: str = ''
    plc_string_tag: str = ''
    plc_enable_analog: bool = False
    plc_enable_digital: bool = False
    plc_enable_string: bool = False

    twx_tag_table: dict = field(default_factory = dict)
    twx_session: requests.sessions.Session = requests.session()
    twx_connected: bool = False
    twx_last_conn_test: int = 0
    twx_conn_url: str = 'http://localhost:8000/Thingworx/Things/LocalEms/Properties/isConnected'
    twx_headers: dict = field(default_factory = lambda: {
        'Connection' : 'keep-alive',
        'Accept' : 'application/json',
        'Content-Type' : 'application/json'
    })
    
    async def plc_scan_timer(self,) -> bool:
        """PLC Scan Rate Timer\n
        Scan Rate set in config file

        Returns:
            bool: accumulated time >= timer preset
        """
        timer = SimpleTimer(self.plc_last_scan_time, self.plc_scan_rate)
        if timer.done:
            self.plc_last_scan_time = timer.timestamp
        return timer.done
       
    def twx_request(self, request_type: str, url: str, data: list):
        requst_type = request_type.lower()
        try:
            if requst_type == 'get':
                return self.twx_session.get(url = url, headers = self.twx_headers, timeout = 4)
            elif request_type == 'post':
                pass
        except Exception as e:
            SaniTrendLogging.logger.error(repr(e))

    
    async def get_twx_connection_status(self) -> None:
        timer = SimpleTimer(self.twx_last_conn_test, 10000)
        if timer.done:
            self.twx_last_conn_test = timer.timestamp
            self.twx_connected = await self._get_twx_connection_status()
            if not self.twx_connected:
                self.twx_last_conn_test = self.twx_last_conn_test + 30000

    async def _get_twx_connection_status(self) -> bool:
        result = await asyncio.to_thread(self.twx_request, request_type = 'get', url = self.twx_conn_url, data = [])
        if isinstance(result, requests.models.Response):
            if result.status_code == 200:
                return (result.json())["rows"][0]["isConnected"]
            else:
                return False
        else:
            return False
        


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
    database: str = os.path.join(os.path.dirname(__file__), "stc.db")
    logging_active: bool = False


async def main():
    test = STC()
    while True:
        # conn_status = asyncio.create_task(test.get_twx_connection_status())
        # enable_scan = asyncio.create_task(test.plc_scan_timer())
        print(test.twx_last_conn_test, test.twx_connected)
        await test.get_twx_connection_status()
        await test.plc_scan_timer()
        await asyncio.sleep(1)
        

if __name__ == "__main__":
    asyncio.run(main())