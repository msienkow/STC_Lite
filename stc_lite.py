
from datetime import datetime
import json
import logging
from logging import handlers
import math
import os
import platform
import sqlite3
import sys
import threading
import time


class SaniTrendLogging:
    logger = logging.getLogger("STC_Logs")
    logger.setLevel(logging.DEBUG)
    logger_formatter = logging.Formatter("%(levelname)s %(asctime)s: %(funcName)s @ line %(lineno)d - %(message)s")
    logger_handler = handlers.TimedRotatingFileHandler("stc.log", when="midnight", interval=1, backupCount=30)
    logger_handler.setFormatter(logger_formatter)
    logger.addHandler(logger_handler)


class SimpleTimer():
    def __init__(self, entered_time: int = 0, preset: int = 0):
        self.entered_time = entered_time
        self.preset = preset
        self.ACC = 0
        self.DN = False
        self.timestamp = 0

        self._simple_timer()
    
    def _simple_timer(self,) -> None:
        """Allen-Bradley PLC Timer replica

        Args:
            entered_time (int, optional): timestamp in milliseconds. Defaults to 0.
            preset (int, optional): preset in milliseconds. Defaults to 0.

        Returns:
            None: 
        """
        current_datetime = int(round(time.time() * 1000))
        time_elapsed = current_datetime - self.entered_time
        self.ACC = time_elapsed
        self.timestamp = current_datetime
        self.DN = True if time_elapsed >= self.preset else False
        

class STC:
    def __init__(self, config_file: str ="SaniTrendConfig.json"):
        self.plc_config = {
            "delta": 0.495,
            "ipaddress": "",
            "path": "",
            "scan_rate": 1000,
            "tags": [],
            "virt_analog_tag" : "",
            "virt_digital_tag": "",
            "virt_string_tag": "",
            "virt_analog_enable": False,
            "virt_digital_enable": False,
            "virt_string_enable": False,
            "virt_tag_config": []
        }

        self._plc_last_scan_time:int = 0
        self.plc_data = []
        self.plc_data_buffer = []
        self.twx_config = {
            "headers": {
                "Connection": "keep-alive",
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            "conn_url": "http://localhost:8000/Thingworx/Things/LocalEms/Properties/isConnected"
        }

        self.twx_connected: bool = False
        self._twx_last_conn_test = 0
    
    def plc_scan_timer(self,) -> bool:
        """PLC Scan Rate Timer\n
        Scan Rate set in config file

        Returns:
            bool: accumulated time >= timer preset
        """
        timer = SimpleTimer(self._plc_last_scan_time, self.plc_config["scan_rate"])
        if timer.DN:
            self._plc_last_scan_time = timer.timestamp
        return timer.DN
        
    
    def get_twx_connection_status(self,) -> None:
        timer = SimpleTimer(self._twx_last_conn_test, 10000)
        if timer.DN:
            self._twx_last_conn_test = timer.timestamp
            asyncio.create_task(self._get_twx_connection_status())

    async def _get_twx_connection_status(self,) -> None:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.twx_config["conn_url"], headers=self.twx_config["headers"], timeout=1) as response:
                    result = await response.json()
                    if  response.status == 200:
                        self.twx_connected = (result)["rows"][0]["isConnected"]
                        SaniTrendLogging.logger.info("Thingworx is connected.")
                        
        except Exception as e:
            SaniTrendLogging.logger.error(repr(e))
            self.twx_connected = False
            self._twx_last_conn_test = self._twx_last_conn_test + 30000


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
    run_code = True
    num = int(1)
    while run_code:
        try:
            test = STC()
            test.get_twx_connection_status()
            print(test._twx_last_conn_test)
            
            await asyncio.sleep(3)



        except Exception as e:
            SaniTrendLogging.logger.error(repr(e))
            run_code = False

if __name__ == "__main__":
    asyncio.run(main())

# while True:
    # log_error("twx_connected", test.twx_connected)
    # time.sleep(10)