import asyncio
import aiohttp
from time import sleep

from stc_lite import SaniTrendLogging

class Test:
    test = False
    async def request(self,):
        async def _request(self,):
            twx_config = {
                "headers": {
                    "Connection": "keep-alive",
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                },
                "url": "http://localhost:8000/Thingworx/Things/LocalEms/Properties/isConnected"
            }
            self.test = True
            async with aiohttp.ClientSession() as session:
                async with session.get(twx_config['url'], headers=twx_config['headers'], timeout=2) as response:
                        result_status = response.status
                        result = await response.json()
                        if result_status == 200:
                            print(result_status)
                        else: 
                            print("Failed")
                        print(result)
        try:                    
            await (_request(self))
        except Exception as e:
            asyncio.create_task(SaniTrendLogging.add_log_entry("error", e))

async def main():
    test = Test()
    asyncio.create_task(test.request())
    
    
    await asyncio.sleep(4)
    
    
    




if __name__ == "__main__":
    asyncio.run(main())