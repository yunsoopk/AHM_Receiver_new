import asyncio
from bleak import BleakClient, BleakScanner
from datetime import datetime
import signal
import sys

# Nordic UART Service (NUS) UUIDs
NUS_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
NUS_RX_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
NUS_TX_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"
DEVICE_NAME = "AHM_PANDEY_LAB"

clients = []  # Global list of clients to access during shutdown

def create_handle_rx(address):
    def handle_rx(sender: str, data: bytearray):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] Received data from {address}: {data.decode('utf-8')}")
    return handle_rx

async def handle_device(address):
    client = BleakClient(address)
    clients.append(client)

    try:
        await client.connect()
        print(f"Connected to device {address}")

        # Send initialization command
        init_command = b"{"
        await client.write_gatt_char(NUS_RX_UUID, init_command)
        print(f"Sent initialization command: {{ to {address}")

        # Start receiving notifications
        await client.start_notify(NUS_TX_UUID, create_handle_rx(address))
        print(f"Started receiving notifications from {address}")

        # Keep the connection alive to receive notifications
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        print(f"Connection to {address} cancelled")
    finally:
        if client.is_connected:
            # Send termination command
            term_command = b"}"
            await client.write_gatt_char(NUS_RX_UUID, term_command)
            print(f"Sent termination command: }} to {address}")
            await client.stop_notify(NUS_TX_UUID)
            await client.disconnect()
            print(f"Disconnected from {address}")

def choose_device(devices):
    print("Available Devices:")
    for i, device in enumerate(devices):
        print(f"[{i}] {device.name} - {device.address}")
    
    choice = -1
    while choice < 0 or choice >= len(devices):
        try:
            choice = int(input("Choose a device by index: "))
        except ValueError:
            print("Invalid input. Please enter a number.")
    return devices[choice]

async def main():
    print("Scanning for devices...")
    devices = await BleakScanner.discover()

    # Filter target devices
    target_devices = [device for device in devices if device.name and DEVICE_NAME in device.name]

    if not target_devices:
        print(f"No devices found with the name: {DEVICE_NAME}")
        return

    chosen_device = choose_device(target_devices)
    print(f"Chosen device: {chosen_device.name} ({chosen_device.address})")

    # Handle the chosen device
    await handle_device(chosen_device.address)

def signal_handler(signal, frame):
    print('SIGINT received, shutting down.')
    for client in clients:
        if client.is_connected:
            asyncio.run_coroutine_threadsafe(client.disconnect(), asyncio.get_event_loop())
    sys.exit(0)

if __name__ == "__main__":
    # Set the signal handler for SIGINT
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Run the main function
        asyncio.run(main())
    except Exception as e:
        print(f"Error occurred: {e}")