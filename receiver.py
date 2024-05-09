import asyncio
import timeit
import sys
from datetime import datetime
from bleak import BleakScanner, BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

# Servide UUID for UART over BLE
SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
TX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
RX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

dataflag = False

async def scan_and_connect(device_name):
    while True:
        devices = await BleakScanner.discover(timeout=1.0, return_adv=True)
        for d, a in devices.values():
            if a.local_name == device_name:
                # print(f"Found device with name '{device_name}': {d.address}")
                try:
                    async with BleakClient(d, timeout=3.0) as client:
                        async def response_handler(sender, data: bytearray):
                          # Record the time after receiving the response
                            end_time = timeit.default_timer()
                            # Decode the response from the UART characteristic
                            response = data.decode()
                            # Read the response from the UART characteristic
                            now = datetime.now()
                            date = now.strftime('%Y/%m/%d')
                            time = now.strftime('%H:%M:%S.%f')
                            # Calculate the time difference
                            time_diff = end_time - start_time
                            print(f"{date}, {time}, {d.address}, {a.rssi}, {time_diff}, {response}")
                            client.disconnect()

                        print(f"Connected to {d.address}")
                        await client.start_notify(RX_CHAR_UUID, response_handler)

                        # Define signal to send
                        signal = b"{"
                        # Record the time before receiving the response
                        start_time = timeit.default_timer()
                        # Write the signal to the UART characteristic
                        await client.write_gatt_char(TX_CHAR_UUID, bytearray(signal), response=True)
                        # print(f"Sent signal: {signal.decode()}")
                    
                        # Wait for the response
                        await asyncio.sleep(0.5)

                except Exception as e:
                    print(f"Failed to connect to {d.address}: {e}")

        #await asyncio.sleep(1)  # Wait for 1 second before scanning again

async def main():
    # Define the device name
    device_name = "AHM_PANDEY_LAB"
    #device_name = "Nordic_UART"
    await scan_and_connect(device_name)

if __name__ == "__main__":
    asyncio.run(main())