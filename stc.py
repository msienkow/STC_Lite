import asyncio
import stc_lite



async def main():
    sanitrend_cloud_lite = stc_lite.STC()
    run_code = True
    plc_watchdog_buffer = False
    twx_alarm_buffer = True

    while run_code:
        try:
            if sanitrend_cloud_lite.plc_scan_timer():
                asyncio.create_task(sanitrend_cloud_lite.get_twx_connection_status())
                asyncio.create_task(sanitrend_cloud_lite.get_stc_config())
                for tag in sanitrend_cloud_lite.plc_tag_list:
                    asyncio.create_task(sanitrend_cloud_lite.read_tags(tag))
                
                plc_watchdog = stc_lite.get_tag_value(sanitrend_cloud_lite.plc_data, 'PLC_Watchdog')
                twx_alarm = not sanitrend_cloud_lite.twx_connected
                comms_data = []
                if plc_watchdog != plc_watchdog_buffer:
                    comms_data.append(('SaniTrend_Watchdog', plc_watchdog))
                    plc_watchdog_buffer = plc_watchdog

                if twx_alarm != twx_alarm_buffer:
                    comms_data.append(('Twx_Alarm', twx_alarm))
                    twx_alarm_buffer = twx_alarm
                
                if len(comms_data) > 0:
                    asyncio.create_task(sanitrend_cloud_lite.write_tags(comms_data))

                asyncio.create_task(sanitrend_cloud_lite.upload_tag_data_to_twx())

            
            await asyncio.sleep(0.1)

            reboot = stc_lite.get_tag_value(sanitrend_cloud_lite.plc_data, 'Reboot')
            if reboot:
                run_code = False
                reboot_data = []
                reboot_data.append(('Reboot_Response', 2))
                asyncio.sleep(5)
                stc_lite.reboot_pc()

        except KeyboardInterrupt:
            print("\n\nExiting Python and closing PLC connection...\n\n\n")
            sanitrend_cloud_lite.plc.Close()
            runCode = False
            
        except Exception as error:
            print(f'Critical Error: {error} Restarting Code in 30 Seconds...')
            stc_lite.SaniTrendLogging.logger.error(repr(error))
            asyncio.sleep(30)
            

if __name__ == "__main__":
    asyncio.run(main())