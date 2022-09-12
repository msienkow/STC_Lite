# STC_Lite 
SaniTrend™ Cloud Lite

This project contains python scripts to communicate with an Allen-Bradley Micro800 series controller, and a Thingworx instance (not included)
using the Thingworx Edge Microserver (not included). This will also store and forward the data when communication to the Thingworx server 
is not working, by storing the Thingworx Rest API messages in a local SQLite database.

Included is python embedded (3.10.6) for use on Windows PCs without having to install python. I do this for companies that have IT departments that 
refuse to have a Linux system installed on their network.

### Dependencies
*Only needed if installed on Linux, as the Microsoft Windows® embedded python package will have the dependencies included.

- [pylogix](https://github.com/dmroeder/pylogix) - for Allen-Bradley PLC Communications
- [aiohttp](https://github.com/aio-libs/aiohttp) - For REST API calls to the Thingworx Edge Micro Server.

Windows (if using installed python)
```console
python -m pip install pylogix
python -m pip install aiohttp
```

Linux
```console
pip3 install pylogix
pip3 install aiohttp
```