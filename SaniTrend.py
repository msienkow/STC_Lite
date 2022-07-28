from pylogix import PLC
import stc_lite

thingworx_connectivity = stc_lite.ThingworxConnectivity()
thingworx_connectivity.get_twx_connection_status()
print(thingworx_connectivity.twx_connected)
