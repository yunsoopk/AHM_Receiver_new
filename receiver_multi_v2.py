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

clients = []  # Global list of clients to access during shutdown
buffers = {}  # Buffer dictionary to store incomplete messages for each device
csv_writers = {}  # Dictionary to store CSV writers for each device
csv_files = {}  # Dictionary to store file objects for each device
file_timestamps = {}  # Dictionary to store the timestamp for each device's current file


def create_csv_writer(device_name, device_address):
    current_time = datetime.now()
    file_timestamps[device_address] = current_time

    # Create the directory for sensor data
    sanitized_device_name = device_name.replace(" ", "_").replace(":", "_")
    base_path = os.path.join("sensor_data", sanitized_device_name)
    if not os.path.exists(base_path):
        os.makedirs(base_path)

    # Generate the filename and full file path using device name
    filename = f"{sanitized_device_name}_{current_time.strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join(base_path, filename)

    csv_file = open(filepath, mode='w', newline='')
    writer = csv.writer(csv_file)

    # Write header
    writer.writerow(["Date", "Time", "Device Name", "accel.X", "accel.Y", "accel.Z", "gyro.X", "gyro.Y", "gyro.Z", "temp.O", "temp.A", "battery.V"])
    return writer, csv_file


def get_current_csv_writer(device_address):
    return csv_writers[device_address], csv_files[device_address]


def rotate_csv_writer(device_name, device_address):
    csv_file = csv_files[device_address]
    csv_file.close()
    writer, csv_file = create_csv_writer(device_name, device_address)
    csv_writers[device_address], csv_files[device_address] = writer, csv_file


def parse_complete_message(complete_message, device_address):
    """
    Parses the complete message and returns a dictionary with the parsed values.
    """
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
            # Parse accelerometer and gyroscope data
            accel_part, gyro_part = complete_message.split(";G:")
            _, accel_values = accel_part.split("A:")
            parsed_data["accel.X"], parsed_data["accel.Y"], parsed_data["accel.Z"] = map(float, accel_values.split(","))
            parsed_data["gyro.X"], parsed_data["gyro.Y"], parsed_data["gyro.Z"] = map(float, gyro_part.split(","))

        if "V:" in complete_message and ";T:" in complete_message:
            # Parse voltage and temperature data
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

        # Check if the buffer contains an underscore
        if '_' in buffers[device_address]:
            complete_message, remaining = buffers[device_address].split('_', 1)
            print(f"[{time_str}] Received complete message from {device_name}: {complete_message}")
            buffers[device_address] = remaining

            # Parse the complete message
            parsed_data = parse_complete_message(complete_message, device_address)

            # Write to CSV
            writer, csv_file = get_current_csv_writer(device_address)
            row = [date_str, time_str, device_name] + list(parsed_data.values())
            writer.writerow(row)
            csv_file.flush()

            # Check if an hour has passed to rotate the file
            if datetime.now() - file_timestamps[device_address] >= timedelta(hours=1):
                rotate_csv_writer(device_name, device_address)

    return handle_rx


async def connect_and_init_device(device, device_name):
    client = BleakClient(device.address)
    try:
        await client.connect()
        print(f"Connected to device {device.address}")

        # Initialize buffer for this device
        buffers[client.address] = ""
        writer, csv_file = create_csv_writer(device_name, client.address)
        csv_writers[client.address], csv_files[client.address] = writer, csv_file

        # Send initialization command
        init_command = b"I"
        await client.write_gatt_char(NUS_RX_UUID, init_command)
        print(f"Sent initialization command: 'I' to {client.address}")

        # Start receiving notifications
        await client.start_notify(NUS_TX_UUID, create_handle_rx(client.address, device_name))
        print(f"Started receiving notifications from {client.address}")

        clients.append(client)

        return client

    except Exception as e:
        print(f"Failed to connect to {device.address}: {e}")

    return None


async def handle_device_connection(device, device_name):
    while True:
        try:
            client = await connect_and_init_device(device, device_name)
            if client is None:
                await asyncio.sleep(5)
                continue

            try:
                while client.is_connected:
                    await asyncio.sleep(1)
            except Exception as e:
                print(f"Error with device {client.address}: {e}")
            finally:
                if client.is_connected:
                    # Send termination command
                    term_command = b"T"
                    await client.write_gatt_char(NUS_RX_UUID, term_command)
                    print(f"Sent termination command: 'T' to {client.address}")
                    await client.stop_notify(NUS_TX_UUID)
                    await client.disconnect()
                    print(f"Disconnected from {client.address}")
                    if client.address in csv_files:
                        csv_files[client.address].close()
                clients.remove(client)
        except Exception as e:
            print(f"Exception in handle_device_connection: {e}")

        # Retry connection after a delay
        print(f"Retrying connection to {device.address} after 5 seconds...")
        await asyncio.sleep(5)


def signal_handler(signal, frame):
    print('SIGINT received, shutting down.')
    for client in clients:
        if client.is_connected:
            asyncio.get_event_loop().run_until_complete(client.disconnect())
    sys.exit(0)


async def main():
    print("Scanning for devices...")

    unique_devices = {}

    def scan_callback(device, advertisement_data):
        if device.name and DEVICE_NAME_SUBSTRING in device.name:
            unique_devices[device.address] = (device, advertisement_data)

    scanner = BleakScanner(detection_callback=scan_callback)
    await scanner.start()
    await asyncio.sleep(5)  # Adjust the sleep duration to your needs
    await scanner.stop()

    target_devices = list(unique_devices.values())

    if not target_devices:
        print(f"No devices found with the name containing: {DEVICE_NAME_SUBSTRING}")
        return

    print("Found devices:")
    for idx, (device, advertisement_data) in enumerate(target_devices):
        print(f"{idx}: {device.name} ({device.address}), RSSI: {advertisement_data.rssi} dBm")

    selected_indices = input("Enter the indices of the devices you want to connect to, separated by commas: ")
    selected_indices = [int(index.strip()) for index in selected_indices.split(',')]

    selected_devices = [target_devices[idx][0] for idx in selected_indices]

    tasks = [handle_device_connection(device, device.name) for device in selected_devices]

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
