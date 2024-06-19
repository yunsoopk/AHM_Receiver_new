import asyncio
import tkinter as tk
from tkinter import scrolledtext
import pandas as pd
from datetime import datetime
import argparse
from bleak import BleakScanner
from bleak import BleakClient

Device_list = []

async def start_window():
    my_window = MyWindow(asyncio.get_event_loop())
    await my_window.show()


class MyWindow(tk.Tk):
    
    def __init__(self, loop):
        self.loop = loop
        super().__init__()
        self.title("BLE Scanner")
        # self.attributes('-zoomed', True)
        self.state("zoomed")

        self.is_scanning = False

        self.start_stop_button = tk.Button(self, text="Start Scan", command=self.start_stop_scan, width=20, height=3)
        self.start_stop_button.grid(row=0, column=0, padx=5, pady=5)

        self.text_output = scrolledtext.ScrolledText(self, width=60, height=20)
        self.text_output.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        self.df = pd.DataFrame(columns=['Date', 'Time', 'Address', 'Local_Name', 'RSS_in_dBm', 'tx_power', 'service_data', 'service_uuids', 'manufacturer_data', 'platform_data'])

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    async def scan(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("--macos-use-bdaddr",action="store_true",help="when true use Bluetooth address instead of UUID on macOS",)
        args = parser.parse_args()
        search_string = 'AHM_PANDEY_LAB'
        Device_list = []

        while self.is_scanning:
            devices = await BleakScanner.discover(timeout = 1.0, return_adv=True, cb=dict(use_bdaddr=args.macos_use_bdaddr))
            
            for d, a in devices.values():
                if a.local_name == search_string:
                    now = datetime.now()
                    date = now.strftime('%Y/%m/%d')
                    time = now.strftime('%H:%M:%S.%f')
                    scan = [date, time, d.address, a.local_name, a.rssi, a.tx_power, a.service_data, a.service_uuids, a.manufacturer_data, a.platform_data]
                    self.df.loc[len(self.df)] = scan
                    Device_list.append(d.address)

                    self.text_output.insert(tk.END, f"{date} {time} - {a.local_name} ({d.address}) RSSI: {a.rssi}\n")
                    self.text_output.see(tk.END)

            # await asyncio.sleep(0.1)

    def start_stop_scan(self):
        if not self.is_scanning:
            self.is_scanning = True
            self.start_stop_button.config(text="Stop Scan & Save to CSV")
            asyncio.create_task(self.scan())
        else:
            self.is_scanning = False
            self.start_stop_button.config(text="Start Scan")
            asyncio.create_task(self.save_to_csv())

    async def save_to_csv(self):
        self.text_output.insert(tk.END, "Stopping scanning and saving DataFrame to CSV...")
        self.text_output.see(tk.END)
        now = datetime.now()
        date = now.strftime('%Y-%m-%d')
        time = now.strftime('%H%M')
        filename = "BLE_Scanned_"+date+"_"+time+".csv"
        self.df.to_csv(filename)
        self.text_output.insert(tk.END, f"DataFrame saved to {filename}\n")
        self.text_output.see(tk.END)

    def on_close(self):
        self.loop.stop()
        self.destroy()

    async def show(self):
        while True:
            self.update()
            await asyncio.sleep(0.1)


async def main():
    await start_window()

if __name__ == "__main__":
    asyncio.run(main())
