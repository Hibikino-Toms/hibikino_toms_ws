import serial.tools.list_ports

# 接続されているUSBデバイスのリストを取得
ports = serial.tools.list_ports.comports()

# デバイス情報を表示
for port in ports:
    print(f"デバイス名: {port.device}, VID: {port.vid}, PID: {port.pid}, シリアル番号: {port.serial_number}")

# 特定のシリアル番号を持つデバイスを選択
# desired_serial_number = "FT94VZIA"
# for port in ports:
#     if port.serial_number == desired_serial_number:
#         DEVICENAME = port.device
#         print(f"選択されたデバイス: {DEVICENAME}")
