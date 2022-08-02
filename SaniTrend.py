import time
from pylogix import PLC
import stc_lite


def main():
    tags = []
    stc = stc_lite.SaniTrendPLC()
    for i in range(8):
        tags.append(f'a{i+1}')
    for i in range(12):
        tags.append(f'd{i+1}')
    tags.append('Recipe')
    with PLC() as comm:
        comm.IPAddress = '192.168.1.132'
        comm.Micro800 = True
        comm.Close()
        stc.tag_data = comm.Read(tags)
        start = int(round(time.time() * 1000))
        for item in stc.tag_data:
            message = f'{item.TagName}: {item.Value}'
            stc_lite.SaniTrendLogging.add_log_entry('info', message)
        end = int(round(time.time() * 1000))
        total = end - start
        print(f'log time: {total} ms')
        stc.set_tag_data_buffer()
        time.sleep(15)
        stc.tag_data = comm.Read(tags)
        stc.set_tag_data_buffer()

    # stc_lite.SaniTrendLogging.add_log_entry('warn', 'call from class')
    # # while True:
    #     # test = stc_lite.SaniTrendLogging()
    #     # test2 = stc_lite.Thingworx()
    #     # for i in range(10):
    #     #     test.add_log_entry('debug', f'Test #{i}')
    #     # print(time.perf_counter())
    #     # print(int(round(time.time() * 1000)))
    #     # test2.get_twx_connection_status
    #     # time.sleep(5)

if __name__ == '__main__':
    # asyncio.run(main())
    main()
    
