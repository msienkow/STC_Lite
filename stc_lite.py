import asyncio
from multiprocessing.sharedctypes import Value
import aiohttp
from dataclasses import dataclass, field
import json
import logging
from logging import handlers
from math import isinf
import os
import platform
from pylogix import PLC, lgx_response
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

def RoundTagData(tag_data) -> any:
    """Round float value to 2 decimal places \n
    from list of tag data or single tag response \n
    from a pylogix PLC read.

    Args:
        tag_data (lgx_response.Response or list[lxg_response.Response]): either single tag read, of list of tag data from read

    Returns:
        list: returns either a lgx_response.Response class or list of lgx_response.Response class
    """
    if isinstance(tag_data, list):
        rounded_tag_data = []
        # Response(tag_name, value, status)
        for tag in tag_data:
            value = round(tag.Value,2) if isinstance(tag.Value, float) else tag.Value
            rounded_tag_data.append(lgx_response.Response(tag.TagName, value, tag.Status))
        return rounded_tag_data
    elif isinstance(tag_data, lgx_response.Response):
        value = tag_data.Value
        value = round(tag_data.Value,2) if isinstance(tag_data.Value, float) else tag_data.Value
        return lgx_response.Response(tag_data.TagName, value, tag_data.Status)

            
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


def get_tag_value(tag_data: list = [], tag_name: str = '') -> any:
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
                async with request_types[request_type](url = url, headers = headers) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        return None
            except Exception as e:
                SaniTrendLogging.logger.error(repr(e))
        else:
            SaniTrendLogging.logger.exception('Request method not defined.')

@dataclass
class STC:
    smi_number: str = ''

    plc_data: list = field(default_factory = list)
    plc_data_buffer: list = field(default_factory = list)
    plc_tag_list: list = field(default_factory = list)
    plc_tag_delta: float = 0.495,
    plc_ip_address: str = ''
    plc_scan_rate: int = 1000
    plc_last_scan_time: int = 0
    
    remote_plc_config: list = field(default_factory = list)
    remote_plc_last_config_time: int = 0
 
    twx_tag_table: list = field(default_factory = list)
    twx_connected: bool = False
    twx_last_conn_test: int = 0
    twx_conn_fail_count: int = 0
    twx_conn_url: str = 'http://localhost:8000/Thingworx/Things/LocalEms/Properties/isConnected'
    twx_server_url: str = ''
    twx_headers: dict = field(default_factory = lambda: {
        'Connection' : 'keep-alive',
        'Accept' : 'application/json',
        'Content-Type' : 'application/json'
    })
    twx_data_shape: dict = field(default_factory = lambda: {
        'fieldDefinitions': {
            'name': {
                'name': 'name',
                'aspects': {
                    'isPrimaryKey': True
                },
            'description': 'Property name',
            'baseType': 'STRING',
            'ordinal': 0
            },
            'time': {
                'name': 'time',
                'aspects': {},
                'description': 'time',
                'baseType': 'DATETIME',
                'ordinal': 0
            },
            'value': {
                'name': 'value',
                'aspects': {},
                'description': 'value',
                'baseType': 'VARIANT',
                'ordinal': 0
            },
            'quality': {
                'name': 'quality',
                'aspects': {},
                'description': 'quality',
                'baseType': 'STRING',
                'ordinal': 0
            }
        }
    })

    def __post_init__(self) -> None:
        with open('SaniTrendConfig.json') as file:
            config_data = json.load(file)
            self.plc_ip_address = config_data['Config']['PLCIPAddress']
            self.plc_scan_rate = int(config_data['Config']['PLCScanRate'])
            self.smi_number = config_data['Config']['SMINumber']
            self.twx_server_url = f'http://localhost:8000/Thingworx/Things/{self.smi_number}/'
            self.twx_tag_table = config_data['Tags']
            for tag in self.twx_tag_table:
                self.plc_tag_list.append(tag['tag'])
            return None
    
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

    async def get_remote_plc_config(self):
        url = f'{self.twx_server_url}Services/GetPropertyValues'
        timer = SimpleTimer(self.remote_plc_last_config_time, 10000)
        if timer.done and self.twx_connected:
            self.remote_plc_last_config_time = timer.timestamp
            response = await twx_request('post', url, self.twx_headers)
            if isinstance(response, dict):
                self.remote_plc_config = []
                result = response['rows'][0]
                rows = result['PropertyConfig']['rows']
                analog = 'ANALOG'
                digital = 'DIGITAL'
                for property in rows:
                    property_name = ''
                    tag_name = ''
                    units_min = 0
                    units_max = 1
                    units = ''
                    for key,value in property.items():
                        if key == 'PropertyName':
                            property_name = value
                        if key == 'TagName':
                            tag_name = value
                        if key == 'EUMin':
                            units_min = value
                            if units_min == '':
                                units_min = 0
                        if key == 'EUMax':
                            units_max = value
                            if units_max == '':
                                units_max = 1
                        if key == 'Units':
                            units = value
                    property_name_parts = property_name.split('_')
                    property_type = property_name_parts[0]
                    plc_array_number = int(property_name_parts[len(property_name_parts) - 1]) - 1
                    if property_type.upper() in analog:
                        tag_name_tag = f'Analog_In_Tags[{plc_array_number}]'
                        tag_name_data = (tag_name_tag, tag_name)
                        units_min_tag = f'Analog_In_Min[{plc_array_number}]'
                        units_min_data = (units_min_tag, units_min)
                        units_max_tag = f'Analog_In_Max[{plc_array_number}]'
                        units_max_data = (units_max_tag, units_max)
                        units_tag = f'Analog_In_Units[{plc_array_number}]'
                        units_data = (units_tag, units)
                        self.remote_plc_config.extend((tag_name_data, units_min_data, units_max_data, units_data))
                    if property_type.upper() in digital:
                        tag_name_tag = f'Digital_In_Tags[{plc_array_number}]'
                        tag_name_data = (tag_name_tag, tag_name)
                        self.remote_plc_config.append(tag_name_data)
                self.remote_plc_config.append(('PLC_IPAddress', result['PLC_IPAddress']))
                self.remote_plc_config.append(('PLC_Path', result['PLC_Path']))
                self.remote_plc_config.append(('Virtual_AIn_Tag', result['Virtual_AIn_Tag']))
                self.remote_plc_config.append(('Virtual_DIn_Tag', result['Virtual_DIn_Tag']))
                self.remote_plc_config.append(('Virtual_String_Tag', result['Virtual_String_Tag']))
                self.remote_plc_config.append(('Virtualize_AIn', result['Virtualize_AIn']))
                self.remote_plc_config.append(('Virtualize_DIn', result['Virtualize_DIn']))
                self.remote_plc_config.append(('Virtualize_String', result['Virtualize_String']))

            


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
    plc = PLC()
    plc.IPAddress = test.plc_ip_address
    plc.Micro800 = True
    while True:
        if test.plc_scan_timer():
            start = time.perf_counter()
            plc.Write('Analog_In_Tags[0]', 'Analog_In_1')
            plc.Write('Analog_In_Min[0]', 0)
            plc.Write('Analog_In_Max[0]', 100)
            plc.Write('Analog_In_Units[0]', '%')
            plc.Write('Analog_In_Tags[1]', 'Analog_In_2')
            plc.Write('Analog_In_Min[1]', 0)
            plc.Write('Analog_In_Max[1]', 100)
            plc.Write('Analog_In_Units[1]', '%')
            plc.Write('Analog_In_Tags[2]', 'Analog_In_3')
            plc.Write('Analog_In_Min[2]', 0)
            plc.Write('Analog_In_Max[2]', 100)
            plc.Write('Analog_In_Units[2]', '%')
            plc.Write('Analog_In_Tags[3]', 'Analog_In_4')
            plc.Write('Analog_In_Min[3]', 0)
            plc.Write('Analog_In_Max[3]', 100)
            plc.Write('Analog_In_Units[3]', '%')
            plc.Write('Analog_In_Tags[4]', 'Analog_In_5')
            plc.Write('Analog_In_Min[4]', 0)
            plc.Write('Analog_In_Max[4]', 100)
            plc.Write('Analog_In_Units[4]', '%')
            plc.Write('Analog_In_Tags[5]', 'Analog_In_6')
            plc.Write('Analog_In_Min[5]', 0)
            plc.Write('Analog_In_Max[5]', 100)
            plc.Write('Analog_In_Units[5]', '%')
            plc.Write('Analog_In_Tags[6]', 'Analog_In_7')
            plc.Write('Analog_In_Min[6]', 0)
            plc.Write('Analog_In_Max[6]', 100)
            plc.Write('Analog_In_Units[6]', '%')
            plc.Write('Analog_In_Tags[7]', 'Analog_In_8')
            plc.Write('Analog_In_Min[7]', 0)
            plc.Write('Analog_In_Max[7]', 100)
            plc.Write('Analog_In_Units[7]', '%')
            plc.Write('Digital_In_Tags[0]', 'Digital_In_1')
            plc.Write('Digital_In_Tags[1]', 'Digital_In_2')
            plc.Write('Digital_In_Tags[2]', 'Digital_In_3')
            plc.Write('Digital_In_Tags[3]', 'Digital_In_4')
            plc.Write('Digital_In_Tags[4]', 'Digital_In_5')
            plc.Write('Digital_In_Tags[5]', 'Digital_In_6')
            plc.Write('Digital_In_Tags[6]', 'Digital_In_7')
            plc.Write('Digital_In_Tags[7]', 'Digital_In_8')
            plc.Write('Digital_In_Tags[8]', 'Digital_In_9')
            plc.Write('Digital_In_Tags[9]', 'Digital_In_10')
            plc.Write('Digital_In_Tags[10]', 'Digital_In_11')
            plc.Write('Digital_In_Tags[11]', 'Digital_In_12')
            plc.Write('PLC_IPAddress', '192.168.1.132')
            plc.Write('PLC_Path', '1,0')
            plc.Write('Virtual_AIn_Tag', '')
            plc.Write('Virtual_DIn_Tag', '')
            plc.Write('Virtual_String_Tag', '')
            plc.Write('Virtualize_AIn', 2)
            plc.Write('Virtualize_DIn', 0)
            plc.Write('Virtualize_String', 0)

            

            # for tag_data in test.remote_plc_config:
            #     (tag_name, tag_value) = tag_data
            #     print(tag_data)
            #     plc.Write(tag_name, tag_value)
            end = time.perf_counter()
            total = int((end - start) * 1000)
            print(f'Total write time: {total}ms')
        
        asyncio.create_task(test.get_twx_connection_status())
        asyncio.create_task(test.get_remote_plc_config())
        
        await asyncio.sleep(1)
        # test.get_twx_connection_status()
        # enable_plc_scan = test.plc_scan_timer()
        # if enable_plc_scan:
        #     print(test.twx_last_conn_test, test.twx_connected)
        # time.sleep(0.250)
        
if __name__ == "__main__":
    asyncio.run(main())