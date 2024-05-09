import argparse
import asyncio

from bleak import BleakScanner
from bleak import BleakClient

import pandas as pd
from datetime import datetime
import keyboard

search_string = 'AHM_PANDEY_LAB'
df = pd.DataFrame(columns=['Date', 'Time', 'Address', 'Local_Name', 'RSS_in_dBm', 'tx_power', 'service_data', 'service_uuids', 'manufacturer_data', 'platform_data'])

async def scan(args: argparse.Namespace):
    print("scanning for 1 second. if you want to stop scanning, press 's'")

    devices = await BleakScanner.discover(
        timeout = 1.0, return_adv=True, cb=dict(use_bdaddr=args.macos_use_bdaddr)
    )

    for d, a in devices.values():
        if a.local_name == search_string:
            now = datetime.now()
            date = now.strftime('%Y/%m/%d')
            time = now.strftime('%H:%M:%S.%f')
            scan = [date, time, d.address, a.local_name, a.rssi, a.tx_power, a.service_data, a.service_uuids, a.manufacturer_data, a.platform_data]
            df.loc[len(df)] = scan
    print(df)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--macos-use-bdaddr",
        action="store_true",
        help="when true use Bluetooth address instead of UUID on macOS",
    )

    args = parser.parse_args()

    running = True

    while running:
        asyncio.run(scan(args))

        if keyboard.is_pressed('s'):
            print("Stopping scanning and saving DataFrame to Excel...")
            now = datetime.now()
            date = now.strftime('%Y-%m-%d')
            time = now.strftime('%H%M')
            filename = "BLE_Scanned_"+date+"_"+time+".xlsx"
            df.to_excel(filename)
            running = False
