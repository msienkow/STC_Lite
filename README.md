# STC_Lite
SaniTrend™ Cloud Lite

This project contains python scripts to communicate with an Allen-Bradley Micro800 series controller, and a Thingworx instance (not included)
using the Thingworx Edge Microserver (not included). This will also store and forward the data when communication to the Thingworx server 
is not working, by storing the Thingworx Rest API messages in a local SQLite database.

Included is python embedded (3.10.5) for use on Windows PCs without having to install python. I do this for companies that have IT departments that 
refuse to have a Linux system installed on their network.

### Dependencies
*Only needed if install on Linux, as the embedded python package will have the dependencies included.

- [pylogix](https://github.com/dmroeder/pylogix) - for Allen-Bradley PLC Communications

```console
python -m pip install pylogix
```

- [Reqeusts](https://github.com/psf/requests) - For REST API calls to Thingworx.

```console
python -m pip install requests
```