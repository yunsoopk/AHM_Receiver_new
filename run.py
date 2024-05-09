import asyncio
from bleak import BleakScanner

'''
 callback function when devices are scanned
 device: device information(bleak.backends.device.BLEDevice)
 advertisement_data: data transmitted from the sensorboard
'''
# def detection_callback(device, advertisement_data):
    # print device address, signal strength(RSSI) in dB, and advertisement data
    # print(device.address, "RSSI:", advertisement_data.rssi, advertisement_data)

async def run():
    # make scanner class
    scanner = BleakScanner()
    # register callback function
    # scanner.register_detection_callback(detection_callback)
    # start scanning
    await scanner.start()
    # wait 5 seconds. if there is a devices that are scanned, registered callback function is recall
    await asyncio.sleep(5.0)
    # stop scanning
    await scanner.stop()
    # get the devices list
    scanned_devices = await scanner.get_discovered_devices()
    # print device list
    for d, a in scanned_devices():
        print(d.address, "RSSI:", a.rssi, a)
        # print(d)

loop = asyncio.get_event_loop()
loop.run_until_complete(run())