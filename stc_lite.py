import asyncio
import aiohttp
from dataclasses import dataclass, field
import json
import logging
from logging import handlers
from math import isinf
import os
import platform
from pylogix import PLC, lgx_response
import sqlite3
import time




class SaniTrendLogging:
    """Class for automatic logging
    """
    logger = logging.getLogger("STC_Logs")
    logger.setLevel(logging.DEBUG)
    logger_formatter = logging.Formatter("%(levelname)s %(asctime)s: %(funcName)s @ line %(lineno)d - %(message)s")
    logger_handler = handlers.TimedRotatingFileHandler("stc.log", when="midnight", interval=1, backupCount=30)
    logger_handler.setFormatter(logger_formatter)
    logger.addHandler(logger_handler)



@dataclass
class SaniTrendDatabase:
    """Class for dealing with Sqlite3 database
    """


    def log_twx_data_to_db(data: list, dbase: str) -> bool:
        """Logs Thingworx data to SQLite3 database.

        Args:
            data (list): List of Thingworx data with proper formatting.
            dbase (str): Name of database

        Returns:
            bool: True if database operation was successful, else False
        """
        if data:
            try:
                with sqlite3.connect(database = dbase) as db:
                    cur = db.cursor()
                    cur.execute(''' CREATE TABLE if not exists sanitrend (TwxData text, SentToTwx integer) ''')   
                    records = []     
                    sql_as_text = ''
                    insert_query = ''' INSERT INTO sanitrend (TwxData, SentToTwx) VALUES (?,?); '''
                    sql_as_text = json.dumps(data)
                    records.append((sql_as_text, False)) 
                    cur.executemany(insert_query, records)
                    db.commit()
                    return True
            
            except Exception as e:
                SaniTrendLogging.logger.error(repr(e))
                return False

        else:
            return False

    async def upload_twx_data_from_db(dbase: str, url: str) -> int:
        """Queries SQLite database for Thingworx data that needs to be uploaded and uploads it.

        Args:
            dbase (str): name of database file
            url (str): url of Thingworx "Thing" UpdatePropertyValues service.

        Returns:
            int: http response from REST call to Thingworx
        """
        select_query = '''select ROWID,TwxData,SentToTwx from sanitrend where SentToTwx = false LIMIT 32'''
        delete_ids = []
        sql_twx_data = []
        try:
            with sqlite3.connect(database = dbase) as db:
                cur = db.cursor()  
                cur.execute(''' CREATE TABLE if not exists sanitrend (TwxData text, SentToTwx integer) ''')
                cur.execute(select_query)  
                records = cur.fetchall()
                for row in records:
                    delete_ids.append(row[0])
                    sql_data = json.loads(row[1])
                    for item in sql_data:
                        sql_twx_data.append(item)
                
                if len(sql_twx_data) > 0:
                    response = await twx_request('update_tag_values', url, 'status', sql_twx_data)
                    if response == 200:
                        delete_query = ''' DELETE FROM sanitrend where ROWID=? '''
                        for id in delete_ids:
                            cur.execute(delete_query, (id,))
                        db.commit()
                
                    return response
            
        except Exception as e:
            SaniTrendLogging.logger.error(repr(e))
            return 404




@dataclass
class SimpleTimer:
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
    """SaniTrend™ Cloud Lite Class

    Returns:
        None: None
    """
    config_file: str = 'SaniTrendConfig.json'
    smi_number: str = ''
    plc = PLC()
    plc_data: list = field(default_factory = list)
    plc_data_buffer: list = field(default_factory = list)
    plc_tag_list: list = field(default_factory = list)
    plc_tag_delta: float = 0.25
    plc_ip_address: str = ''
    plc_scan_rate: int = 1000
    plc_last_scan_time: int = 0
    remote_plc_config: list = field(default_factory = list)
    remote_plc_last_config_time: int = 0
    twx_tag_table: list = field(default_factory = list)
    twx_connected: bool = False
    twx_last_conn_test: int = 0
    twx_conn_fail_count: int = 0
    twx_upload_data: list = field(default_factory = list)
    db_busy: bool = False
    database: str = os.path.join(os.path.dirname(__file__), "stc.db")
    

    def __post_init__(self) -> None:
        with open(self.config_file) as file:
            config_data = json.load(file)
            self.plc_ip_address = config_data['Config']['PLCIPAddress']
            self.plc_scan_rate = int(config_data['Config']['PLCScanRate'])
            self.smi_number = config_data['Config']['SMINumber']
            self.twx_tag_table = config_data['Tags']
            for tag in self.twx_tag_table:
                self.plc_tag_list.append(tag['tag'])

            self.plc.IPAddress = self.plc_ip_address
            self.plc.Micro800 = True
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


    async def read_tags(self, tag: str = '') -> None:
        """Asyncio wrapper for reading tags using Pylogix

        Args:
            tag (str, optional): Tag name in PLC (must be global scoped). Defaults to ''.
        """
        try: 
            new_data = await self.read_tag_data(tag)
        
        except Exception as e:
            SaniTrendLogging.logger.error(repr(e))
            
        if new_data:
            if isinstance(new_data.Value, float):
                new_data.Value = round(new_data.Value, 2)    

            add_data = True
            for old_data in self.plc_data:
                if old_data.TagName == new_data.TagName:
                    add_data = False
                    if new_data.Value is not None:
                        if old_data.Value is None:
                            old_data.Value = 0
                        if isinstance(new_data.Value, float):
                            if abs(old_data.Value - new_data.Value) >= self.plc_tag_delta:
                                old_data.Value = new_data.Value

                        else:
                            if old_data.Value != new_data.Value:
                                old_data.Value = new_data.Value

            if add_data:
                self.plc_data.append(new_data)
        

    async def read_tag_data(self, tags: list = []) -> lgx_response:
        """Asyncio wrapper for reading plc tags using Pylogix

        Args:
            tags (list, optional): list of tags. Defaults to [].

        Returns:
            lgx_response: returns TagName, Value, and Status of tag.
        """
        return self.plc.Read(tags)


    async def write_tags(self, tag_list: list = []) -> None:
        """Asyncio wrapper for writing tag values to PLC

        Args:
            tag_list (list, optional): list of tuples containing tagnames and values. Defaults to [].
        """
        try:
            for tag in tag_list:
                x = await self.write_tag_data(tag)

        except Exception as e:
            SaniTrendLogging.logger.error(repr(e))


    async def write_tag_data(self, tag) -> None:
        """Asyncio wrapper for writing tag data using Pylogix

        Args:
            tag (tuple): tuple of TagName and Value

        Returns:
            None: None
        """
        tag_name, tag_value = tag
        self.plc.Write(tag_name, tag_value)


    async def upload_tag_data_to_twx(self) -> None:
        """Uploads plc tag data to Thingworx
        """
        new_data = []
        for tag_data in self.plc_data:
            add_tag = True
            for old_data in self.plc_data_buffer:
                tag_name = old_data['TagName']
                if tag_data.TagName == tag_name:
                    add_tag = False
                    if tag_data.Value != old_data['Value']:
                        old_data['Value'] = tag_data.Value
                        new_data.append(tag_data)

            if add_tag:
                data_to_add = {
                    'TagName': tag_data.TagName,
                    'Value': tag_data.Value,
                    'Status': tag_data.Status
                }

                self.plc_data_buffer.append(data_to_add)
                new_data.append(tag_data)

        if new_data:
            ignore_type = 'ignore'
            timestamp = int(round(time.time() * 1000))
            for item in new_data:
                twx_value = {}
                twx_tag = ''
                twx_basetype = ''
                for twx_config in self.twx_tag_table:
                    if item.TagName == twx_config['tag']:
                        twx_tag = twx_config['tag']
                        twx_basetype = twx_config['twxtype']
                        break
                
                if twx_tag and twx_basetype.lower() != ignore_type:
                    tag_value = item.Value
                    if tag_value is None:
                        continue

                    else:
                        if twx_basetype == 'NUMBER':
                            if isinf(tag_value):
                                continue

                            else:
                                twx_tag_value = round(tag_value,2)

                        else:
                            twx_tag_value = tag_value

                    twx_value['time'] = timestamp
                    twx_value['quality'] = 'GOOD'
                    twx_value['name'] = twx_tag

                    twx_value['value'] = {
                        'value': twx_tag_value,
                        'baseType': twx_basetype
                    }
                    
                    self.twx_upload_data.append(twx_value)
            
            if self.twx_connected:
                url = f'/Thingworx/Things/{self.smi_number}/Services/UpdatePropertyValues'
                response = await twx_request('update_tag_values', url, 'status', self.twx_upload_data)
                if response != 200 and not self.db_busy:
                    self.db_busy = True
                    success = SaniTrendDatabase.log_twx_data_to_db(self.twx_upload_data, self.database)
                    if success:
                        self.twx_upload_data = []
                    
                    self.db_busy = False

                elif response == 200:
                    self.twx_upload_data = []
                    self.db_busy = True
                    upload_response = await SaniTrendDatabase.upload_twx_data_from_db(self.database, url)
                    self.db_busy = False

            else:
                if not self.db_busy and self.twx_upload_data:
                    self.db_busy = True
                    success = SaniTrendDatabase.log_twx_data_to_db(self.twx_upload_data, self.database)
                    if success:
                        self.twx_upload_data = []

                    self.db_busy = False
                                  

    async def get_twx_connection_status(self) -> None:
        """Gets connection status of PC to Thingworx
        """
        timer = SimpleTimer(self.twx_last_conn_test, 10000)
        url = '/Thingworx/Things/LocalEms/Properties/isConnected'
        if timer.done:
            self.twx_last_conn_test = timer.timestamp
            response = await twx_request('get', url)
            if isinstance(response, dict):
                self.twx_connected = response['rows'][0]['isConnected']
                self.twx_conn_fail_count = 0

            else:
                self.twx_conn_fail_count += 1
                self.twx_connected = False
                self.twx_conn_fail_count += 1
                if self.twx_conn_fail_count > 12:
                    self.twx_last_conn_test += 60000


    async def get_stc_config(self):
        """Gets configuration data from Thingworx
        """
        url = f'/Thingworx/Things/{self.smi_number}/Services/GetPropertyValues'
        timer = SimpleTimer(self.remote_plc_last_config_time, 10000)
        if timer.done and self.twx_connected:
            self.remote_plc_last_config_time = timer.timestamp
            response = await twx_request('post', url)
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
                    if property_type.upper() in analog:
                        plc_array_number = int(property_name_parts[len(property_name_parts) - 1]) - 1
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
                        plc_array_number = int(property_name_parts[len(property_name_parts) - 1]) - 1
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

        asyncio.create_task(self.write_tags(self.remote_plc_config))



def reboot_pc() -> None:
    operating_system = platform.system().lower()
    if operating_system == 'windows':
        os.system('shutdown /r /t 1')

    elif operating_system == 'linux':
        os.system('sudo reboot')
        

def get_tag_value(tag_data: list = [], tag_name: str = '') -> any:
    """Gets tag value given list of tag data from pylogix

    Args:
        tag_data (list, optional): list of tag data from Pylogix. Defaults to [].
        tag_name (str, optional): name of tag from which to get the value. Defaults to ''.

    Returns:
        any: value of tag
    """
    if tag_data and tag_name:
        values = (tag.Value for tag in tag_data if tag.TagName.lower() == tag_name.lower())
        for value in values:
            return value


async def twx_request(request_type: str, url: str, response_type: str = 'json', data: list = [], timeout: int = 5) -> any:
    """Process Thingworx REST requests

    Args:
        request_type (str): type of request being made
        url (str): url of REST request
        response_type (str, optional): 'json' data from REST request, or http 'status' of REST request. Defaults to 'json'.
        data (list, optional): data for POST requests. Defaults to [].
        timeout (int, optional): http timeout. Defaults to 5.

    Returns:
        any: json or status depending on 'response_type'
    """
    new_data =  []
    if data:
        new_data = data.copy()

    post_data = {}
    headers = {
        'Connection' : 'keep-alive',
        'Accept' : 'application/json',
        'Content-Type' : 'application/json'
    }

    datashape = {
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
    }

    async with aiohttp.ClientSession('http://localhost:8000') as session:
        request_types = {
            'get': session.get,
            'post': session.post,
            'update_tag_values': session.post
        }

        request_type = request_type.lower()
        if request_type in request_types:
            if request_type == 'update_tag_values':
                values = {}
                values['rows'] = new_data
                values['dataShape'] = datashape
                post_data = {
                    'values': values
                }

            try:
                async with request_types[request_type](url, headers = headers, json = post_data, timeout = 5) as response:
                    response_json = await response.json(content_type=None)
                    if response_type == 'json':
                        if response.status == 200:
                            return response_json
                            
                        else:
                            return None

                    elif response_type == 'status':
                        return response.status

            except Exception as e:
                SaniTrendLogging.logger.error(repr(e))

        else:
            SaniTrendLogging.logger.exception('Request method not defined.')