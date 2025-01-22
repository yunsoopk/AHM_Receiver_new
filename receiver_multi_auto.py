import asyncio
from bleak import BleakClient, BleakScanner
from datetime import datetime, timedelta
import signal
import sys
import os
import csv

# Nordic UART Service (NUS) UUIDs
NUS_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
NUS_RX_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
NUS_TX_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
DEVICE_NAME_SUBSTRING = "AHM_PANDEY_LAB"

clients = {}  # Dictionary of clients to access during shutdown
buffers = {}  # Buffer dictionary to store incomplete messages for each device
csv_writers = {}  # Dictionary to store CSV writers for each device
csv_files = {}  # Dictionary to store file objects for each device
connected_devices = []  # List to track connected devices

async def disconnect_all():
    for address, client in clients.items():
        if client.is_connected:
            await client.disconnect()
            print(f"Disconnected from {address}")
    clients.clear()
    buffers.clear()
    connected_devices.clear()

def create_csv_writer(device_name, device_address):
    current_time = datetime.now()

    # Create the directory for sensor data
    sanitized_device_name = device_name.replace(" ", "_").replace(":", "_")
    base_path = os.path.join("sensor_data", sanitized_device_name)
    if not os.path.exists(base_path):
        os.makedirs(base_path)

    # Generate the filename and full file path using the current hour
    filename = f"{sanitized_device_name}_{current_time.strftime('%Y%m%d_%H')}.csv"
    filepath = os.path.join(base_path, filename)

    csv_file = open(filepath, mode='w', newline='')
    writer = csv.writer(csv_file)

    # Write header
    writer.writerow(["Date", "Time", "Device Name", "accel.X", "accel.Y", "accel.Z", "gyro.X", "gyro.Y", "gyro.Z", "temp.O", "temp.A", "battery.V"])
    return writer, csv_file


def parse_complete_message(complete_message):
    parsed_data = {
        "accel.X": "",
        "accel.Y": "",
        "accel.Z": "",
        "gyro.X": "",
        "gyro.Y": "",
        "gyro.Z": "",
        "temp.O": "",
        "temp.A": "",
        "battery.V": ""
    }

    try:
        if "A:" in complete_message and ";G:" in complete_message:
            accel_part, gyro_part = complete_message.split(";G:")
            _, accel_values = accel_part.split("A:")
            parsed_data["accel.X"], parsed_data["accel.Y"], parsed_data["accel.Z"] = map(float, accel_values.split(","))
            parsed_data["gyro.X"], parsed_data["gyro.Y"], parsed_data["gyro.Z"] = map(float, gyro_part.split(","))

        if "V:" in complete_message and ";T:" in complete_message:
            voltage_part, temp_part = complete_message.split(";T:")
            _, voltage_value = voltage_part.split("V:")
            temp_values = temp_part.split(",")
            parsed_data["battery.V"] = float(voltage_value)
            parsed_data["temp.O"], parsed_data["temp.A"] = map(float, temp_values)
    except ValueError as e:
        print(f"Error parsing message: {complete_message}. Error: {e}")

    return parsed_data


def create_handle_rx(device_address, device_name):
    async def handle_rx(sender: str, data: bytearray):
        timestamp = datetime.now()
        date_str = timestamp.strftime('%Y-%m-%d')
        time_str = timestamp.strftime('%H:%M:%S.%f')[:-3]  # Include milliseconds in timestamp
        message = data.decode('utf-8')
        buffers[device_address] += message

        if '_' in buffers[device_address]:
            complete_message, remaining = buffers[device_address].split('_', 1)
            buffers[device_address] = remaining

            parsed_data = parse_complete_message(complete_message)
            writer, csv_file = csv_writers[device_address], csv_files[device_address]
            row = [date_str, time_str, device_name] + list(parsed_data.values())
            writer.writerow(row)
            csv_file.flush()

    return handle_rx


async def connect_and_init_device(device, device_name):
    if len(connected_devices) >= 7:
        print("Maximum device limit reached. Skipping new connections.")
        return None

    client = BleakClient(device.address)
    try:
        await client.connect()
        buffers[client.address] = ""
        writer, csv_file = create_csv_writer(device_name, client.address)
        csv_writers[client.address], csv_files[client.address] = writer, csv_file

        await client.write_gatt_char(NUS_RX_UUID, b"I")
        await client.start_notify(NUS_TX_UUID, create_handle_rx(client.address, device_name))

        clients[client.address] = client
        connected_devices.append(client.address)
        print(f"Connected to {device.name} ({device.address})")
        return client
    except Exception as e:
        print(f"Failed to connect to {device.address}: {e}")

    return None


async def scan_and_connect():
    print("Scanning for devices...")
    devices = await BleakScanner.discover()
    for device in devices:
        if DEVICE_NAME_SUBSTRING in (device.name or "") and device.address not in clients:
            await connect_and_init_device(device, device.name)


async def periodic_disconnect_and_scan():
    while True:
        current_time = datetime.now()
        if current_time.minute % 5 == 0:
            print("Performing scheduled disconnect and scan...")
            await disconnect_all()
            await scan_and_connect()
        await asyncio.sleep(60)  # Check every minute


async def main():
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    await periodic_disconnect_and_scan()


if __name__ == "__main__":
    asyncio.run(main())
