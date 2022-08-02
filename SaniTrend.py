import time
from pylogix import PLC
import stc_lite


def main():
    stc_lite.SaniTrendLogging.add_log_entry('warn', 'call from class')
    # while True:
        # test = stc_lite.SaniTrendLogging()
        # test2 = stc_lite.Thingworx()
        # for i in range(10):
        #     test.add_log_entry('debug', f'Test #{i}')
        # print(time.perf_counter())
        # print(int(round(time.time() * 1000)))
        # test2.get_twx_connection_status
        # time.sleep(5)

if __name__ == '__main__':
    # asyncio.run(main())
    main()
