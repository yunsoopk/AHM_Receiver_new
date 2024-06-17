import asyncio
from bleak import BleakClient, BleakScanner
from bleak.backends.scanner import AdvertisementData
from datetime import datetime, timedelta
import signal
import sys
import os
import csv

# Nordic UART Service (NUS) UUIDs
NUS_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
NUS_RX_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
NUS_TX_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
DEVICE_NAME = "AHM_PANDEY_LAB"

clients = []  # Global list of clients to access during shutdown
buffers = {}  # Buffer dictionary to store incomplete messages for each device
csv_writers = {}  # Dictionary to store CSV writers for each device
csv_files = {}  # Dictionary to store file objects for each device
file_timestamps = {}  # Dictionary to store the timestamp for each device's current file

def create_csv_writer(device_name, device_address):
    current_time = datetime.now()
    file_timestamps[device_address] = current_time

    # Create the directory if it doesn't exist
    if not os.path.exists(device_name):
        os.mkdir(device_name)
    
    filename = f"{device_address}_{current_time.strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join(device_name, filename)

    csv_file = open(filepath, mode='w', newline='')
    writer = csv.writer(csv_file)
    writer.writerow(["Timestamp", "Message"])  # Write header
    return writer, csv_file

def get_current_csv_writer(device_address):
    writer, csv_file = csv_writers[device_address], csv_files[device_address]
    return writer, csv_file

def rotate_csv_writer(device_name, device_address):
    csv_file = csv_files[device_address]
    csv_file.close()
    writer, csv_file = create_csv_writer(device_name, device_address)
    csv_writers[device_address], csv_files[device_address] = writer, csv_file

def create_handle_rx(device_address, device_name):
    async def handle_rx(sender: str, data: bytearray):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]  # Include milliseconds in timestamp
        message = data.decode('utf-8')
        buffers[device_address] += message

        # Check if the buffer contains an underscore
        if '_' in buffers[device_address]:
            complete_message, remaining = buffers[device_address].split('_', 1)
            print(f"[{timestamp}] Received complete message from {device_address}: {complete_message}")
            buffers[device_address] = remaining

            # Write to CSV
            writer, csv_file = get_current_csv_writer(device_address)
            writer.writerow([timestamp, complete_message])
            csv_file.flush()

            # Check if an hour has passed to rotate the file
            if datetime.now() - file_timestamps[device_address] >= timedelta(hours=1):
                rotate_csv_writer(device_name, device_address)

    return handle_rx

async def handle_device_lock(client, device_name):
    async with client.lock:
        await client.connect()
        print(f"Connected to device {client.address}")

        # Initialize buffer for this device
        buffers[client.address] = ""
        writer, csv_file = create_csv_writer(device_name, client.address)
        csv_writers[client.address], csv_files[client.address] = writer, csv_file

        # Send initialization command
        init_command = b"{"
        await client.write_gatt_char(NUS_RX_UUID, init_command)
        print(f"Sent initialization command: {{ to {client.address}")

        # Start receiving notifications
        await client.start_notify(NUS_TX_UUID, create_handle_rx(client.address, device_name))
        print(f"Started receiving notifications from {client.address}")

async def handle_device_task(client, device_name):
    try:
        await handle_device_lock(client, device_name)
        
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        print(f"Connection to {client.address} cancelled")
    finally:
        if client.is_connected:
            # Send termination command
            term_command = b"}"
            await client.write_gatt_char(NUS_RX_UUID, term_command)
            print(f"Sent termination command: }} to {client.address}")
            await client.stop_notify(NUS_TX_UUID)
            await client.disconnect()
            print(f"Disconnected from {client.address}")
            if client.address in csv_files:
                csv_files[client.address].close()

def signal_handler(signal, frame):
    print('SIGINT received, shutting down.')
    loop = asyncio.get_event_loop()
    for client in clients:
        if client.is_connected:
            loop.run_until_complete(client.disconnect())
    sys.exit(0)

async def main():
    print("Scanning for devices...")

    unique_devices = {}

    def scan_callback(device, advertisement_data):
        if device.name and DEVICE_NAME in device.name:
            unique_devices[device.address] = (device, advertisement_data)

    scanner = BleakScanner(detection_callback=scan_callback)
    await scanner.start()
    await asyncio.sleep(5)  # Adjust the sleep duration to your needs
    await scanner.stop()

    target_devices = list(unique_devices.values())

    if not target_devices:
        print(f"No devices found with the name: {DEVICE_NAME}")
        return

    print("Found devices:")
    for idx, (device, advertisement_data) in enumerate(target_devices):
        print(f"{idx}: {device.name} ({device.address}), RSSI: {advertisement_data.rssi} dBm")

    selected_indices = input("Enter the indices of the devices you want to connect to, separated by commas: ")
    selected_indices = [int(index.strip()) for index in selected_indices.split(',')]

    selected_devices = [target_devices[idx][0] for idx in selected_indices]

    # Create and store clients with additional lock for synchronized access
    device_clients = [(BleakClient(device.address), device.name) for device in selected_devices]
    for client, device_name in device_clients:
        client.lock = asyncio.Lock()
        clients.append(client)

    # Create tasks for handling each selected device
    tasks = [handle_device_task(client, device_name) for client, device_name in device_clients]

    # Run tasks concurrently
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    # Set the signal handler for SIGINT
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Run the main function
        asyncio.run(main())
    except Exception as e:
        print(f"Error occurred: {e}")