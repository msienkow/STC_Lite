from dataclasses import dataclass, field
from datetime import datetime
import json
import math
import os
import platform
import requests
from sqlite3 import connect
import threading
import time


@dataclass
class SaniTrendDatabase:
    """Class for database data logging
    """
    database: str = os.path.join(os.path.dirname(__file__), 'stc.db')
    logging_active: bool = False

@dataclass
class SaniTrendPLC:
    plc_ipaddress: str = ''
    plc_path: str = ''

@dataclass
class ThingworxConnectivity:
    twx_connected: bool = False
    _twx_last_connection_test: int = 0
    _twx_conn_test_in_progress: bool = False

    def twx_connection_status(self, preset: int = 5):
        if not self._twx_conn_test_in_progress:
            current_ms_time = get_ms_time()
            time_accumulated = current_ms_time - self._twx_last_connection_test
            
            if time_accumulated > preset:
                self._twx_conn_test_in_progress = True
                self._twx_last_connection_test = current_ms_time
                threading.Thread(target=self._twx_connection_status).start()

    def _twx_connection_status(self,):
        headers = {
            'Connection': 'keep-alive',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        url = 'http://localhost:8000/Thingworx/Things/LocalEms/Properties/isConnected'
        

@dataclass
class SaniTrendCloud(SaniTrendDatabase, SaniTrendPLC, ThingworxConnectivity):
    """Set up initial SaniTrend™ Cloud class that will hold all the data in memory that is needed.
    """
    connection_status_time: int = 0


    # def __post_init__(self):
    #     self.plc_path = 'test'
    #     self.connection_headers = 
    # twxData: list = field(default_factory=list)
    


def get_ms_time():
    """Simple function to get current time in milliseconds. Useful for time comparisons\n
        ex.  start_time = get_ms_time()
        end_time = get_ms_time()
        total_millisecond_difference = (end_time - start_time)"""
    return round(time.time() * 1000)


test = SaniTrendCloud()
test.twx_connection_status(1)