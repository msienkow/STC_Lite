import asyncio
import stc_lite



async def main():
    sanitrend_cloud_lite = stc_lite.STC()
    run_code = True
    plc_watchdog_buffer = False

    while run_code:
        try:
            if sanitrend_cloud_lite.plc_scan_timer():
                asyncio.create_task(sanitrend_cloud_lite.get_twx_connection_status())
                asyncio.create_task(sanitrend_cloud_lite.get_stc_config())
                for tag in sanitrend_cloud_lite.plc_tag_list:
                    asyncio.create_task(sanitrend_cloud_lite.read_tags(tag))
                
                plc_watchdog = stc_lite.get_tag_value(sanitrend_cloud_lite.plc_data, 'PLC_Watchdog')
                sanitrend_watchdog = stc_lite.get_tag_value(sanitrend_cloud_lite.plc_data, 'SaniTrend_Watchdog')
                thingworx_alarm = stc_lite.get_tag_value(sanitrend_cloud_lite.plc_data, 'Twx_Alarm')
                thingworx_alarm_status = not sanitrend_cloud_lite.twx_connected
                comms_data = []
                if sanitrend_watchdog != plc_watchdog:
                    comms_data.append(('SaniTrend_Watchdog', plc_watchdog))

                if thingworx_alarm != thingworx_alarm_status:
                    comms_data.append(('Twx_Alarm', thingworx_alarm_status))
                
                if len(comms_data) > 0:
                    asyncio.create_task(sanitrend_cloud_lite.write_tags(comms_data))

                asyncio.create_task(sanitrend_cloud_lite.upload_tag_data_to_twx())
            
            await asyncio.sleep(0.25)

            reboot = stc_lite.get_tag_value(sanitrend_cloud_lite.plc_data, 'Reboot')
            if reboot:
                reboot_data = []
                reboot_data.append(('Reboot_Response', 2))
                await sanitrend_cloud_lite.write_tags(reboot_data)
                await asyncio.sleep(10)
                run_code = False
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