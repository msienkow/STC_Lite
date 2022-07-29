from pylogix import PLC
import stc_lite

import time
stc_plc = stc_lite.SaniTrendPLC()
while True:
    if stc_plc.plc_timer():
        print("gotcha")
    time.sleep(.5)