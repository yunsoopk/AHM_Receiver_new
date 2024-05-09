import asyncio
import timeit
import unittest
from unittest.mock import patch, MagicMock
from bleak import BleakScanner, BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

class TestReceiver(unittest.TestCase):

    def setUp(self):
        self.device_name = "AHM_PANDEY_LAB"
        self.service_uuid = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
        self.tx_char_uuid = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
        self.rx_char_uuid = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"

    @patch('bleak.BleakScanner.discover')
    async def test_scan_and_connect(self, mock_discover):
        mock_discover.return_value = {
            BLEDevice(
                address="AA:BB:CC:DD:EE:FF",
                name=self.device_name,
                rssi=-50,
                connectable=True,
                advertisement=AdvertisementData()
            )
        }

        async def mock_start_notify(self, char_uuid, callback):
            callback(BleakGATTCharacteristic(
                uuid=char_uuid,
                handle=1,
                properties=['notify'],
                service_uuid=self.service_uuid,
                descriptors=[]
            ), b'Hello, world!')

        async def mock_write_gatt_char(self, char_uuid, data, response):
            return True

        async def mock_disconnect(self):
            pass

        with patch.object(BleakClient, 'start_notify', mock_start_notify):
            with patch.object(BleakClient, 'write_gatt_char', mock_write_gatt_char):
                with patch.object(BleakClient, 'disconnect', mock_disconnect):
                    await scan_and_connect(self.device_name)

    def test_response_handler(self):
        response_handler = response_handler(None, b'Hello, world!')
        self.assertEqual(response_handler, 'Hello, world!')

if __name__ == '__main__':
    unittest.main()
