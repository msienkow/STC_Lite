import asyncio
import aiohttp
from dataclasses import dataclass, field
import json
import logging
from logging import handlers
from math import isinf
import os
import platform
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

# def RoundTagData(tag_data: list = []) -> list:
#         for tag in tag_data:
#             if isinstance(tag.Value, float):
#                 tag.Value = round(tag.Value,2)
#             for tag_buffer in self.data_buffer:
#                 if tag.TagName == tag_buffer.TagName:
#                     add_tag = False
#                     if isinstance(tag_buffer.Value, float):
#                         difference = abs(tag.Value - tag_buffer.Value)
#                         if difference > self.delta:
#                             tag_buffer.Value = tag.Value
#                     else:
#                         if tag.Value != tag_buffer.Value:
#                             tag_buffer.Value = tag.Value

#                     continue
                    
#             if add_tag:
#                 self.tag_data_buffer.append(tag)

# def UpdateTagData(tag_data: list = []) -> list:
#         for tag in tag_data:
#             add_tag = True
#             if isinstance(tag.Value, float):
#                 tag.Value = round(tag.Value,2)
#             for tag_buffer in self.data_buffer:
#                 if tag.TagName == tag_buffer.TagName:
#                     add_tag = False
#                     if isinstance(tag_buffer.Value, float):
#                         difference = abs(tag.Value - tag_buffer.Value)
#                         if difference > self.delta:
#                             tag_buffer.Value = tag.Value
#                     else:
#                         if tag.Value != tag_buffer.Value:
#                             tag_buffer.Value = tag.Value

#                     continue
                    
#             if add_tag:
#                 self.tag_data_buffer.append(tag)


async def GetTagValue(tag_data: list = [], tag_name: str = '') -> any:
    if tag_data and tag_name:
        values = (tag.Value for tag in tag_data if tag.TagName == tag_name)
        for value in values:
            if isinstance(value, float):
                return round(value, 2)
            else:
                return value

async def twx_request(request_type: str, url: str, headers = {}, data: dict = {}, timeout: int = 5):
    async with aiohttp.ClientSession() as session:
        request_types = {
            'get': session.get,
            'post': session.post
        }
        request_type = request_type.lower()
        if request_type in request_types:
            try:
                async with request_types[request_type](url = url, headers = headers, json = data, timeout = timeout) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        SaniTrendLogging.logger.error(repr(e))
                        return None
            except Exception as e:
                SaniTrendLogging.logger.error(repr(e))
        else:
            SaniTrendLogging.logger.exception('Request method not defined.')




        
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
    # twx_session: aiohttp.client.ClientSession = aiohttp.ClientSession()
    twx_connected: bool = False
    twx_last_conn_test: int = 0
    twx_conn_fail_count: int = 0
    twx_conn_url: str = 'http://localhost:8000/Thingworx/Things/LocalEms/Properties/isConnected'
    twx_headers: dict = field(default_factory = lambda: {
        'Connection' : 'keep-alive',
        'Accept' : 'application/json',
        'Content-Type' : 'application/json'
    })

    def __post_init__(self) -> None:
        pass
    
    def plc_scan_timer(self) -> bool:
        """PLC Scan Rate Timer\n
        Scan Rate set in config file

        Returns:
            bool: accumulated time >= timer preset
        """
        timer = SimpleTimer(self.plc_last_scan_time, self.plc_scan_rate)
        if timer.done:
            self.plc_last_scan_time = timer.timestamp
        return timer.done

    async def get_twx_connection_status(self) -> None:
        timer = SimpleTimer(self.twx_last_conn_test, 10000)
        if timer.done:
            self.twx_last_conn_test = timer.timestamp
            print(timer.timestamp)
            response = await twx_request('get', self.twx_conn_url, self.twx_headers)
            if isinstance(response, dict):
                self.twx_connected = response['rows'][0]['isConnected']
                self.twx_conn_fail_count = 0
            else:
                self.twx_conn_fail_count += 1
                self.twx_connected = False
                self.twx_conn_fail_count += 1
                if self.twx_conn_fail_count > 12:
                    self.twx_last_conn_test += 60000

    # def get_tag_data(self, tag_data: list = []) -> None:
    #     for tag in tag_data:
    #         add_tag = True
    #         if isinstance(tag.Value, float):
    #             tag.Value = round(tag.Value,2)
    #         for tag_buffer in self.data_buffer:
    #             if tag.TagName == tag_buffer.TagName:
    #                 add_tag = False
    #                 if isinstance(tag_buffer.Value, float):
    #                     difference = abs(tag.Value - tag_buffer.Value)
    #                     if difference > self.delta:
    #                         tag_buffer.Value = tag.Value
    #                 else:
    #                     if tag.Value != tag_buffer.Value:
    #                         tag_buffer.Value = tag.Value

    #                 continue
                    
    #         if add_tag:
    #             self.tag_data_buffer.append(tag)


class SaniTrendDatabase:
    """Class for database data logging
    """
    database: str = os.path.join(os.path.dirname(__file__), "stc.db")
    logging_active: bool = False

async def main():
    test = STC()
    
    while True:
        asyncio.create_task(test.get_twx_connection_status())
        print(test.twx_connected)
        await asyncio.sleep(0.250)
        # test.get_twx_connection_status()
        # enable_plc_scan = test.plc_scan_timer()
        # if enable_plc_scan:
        #     print(test.twx_last_conn_test, test.twx_connected)
        # time.sleep(0.250)
        
if __name__ == "__main__":
    asyncio.run(main())