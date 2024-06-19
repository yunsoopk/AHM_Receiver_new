# Multi OS AHM_Receiver
This is the code for the receiver for Animal Health Monitoring sensors.

The code is tested on Windows 10, Windows 11, macOS Sonoma 14.4, and Raspberry Pi OS Legacy.

This application requires Bleak Python library. (RSSI_Scanner and RSSI_Scanner_GUI needs Pandas library additionally)

## System requirements
Python 3.7 and above (tested with Python 3.10, 3.11, and 3.12)
Bleak Python library (https://bleak.readthedocs.io/en/latest/)
Pandas Python library (https://pandas.pydata.org/)

## How to setup
1. Prepare the system requirements (Install python and required library)
2. Download Python script
3. Run Python script (ex: python receiver_multi.py)

## How to use
1. Run Python script
2. Select the devices you want to connect and collect the data (only for receiver_multi)
3. See the CSV files.