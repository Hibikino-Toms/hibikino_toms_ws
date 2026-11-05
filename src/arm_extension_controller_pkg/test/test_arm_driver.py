"""python -m unittest discover -s test -v (ROS/USB不要)"""
import sys
import threading
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from arm_driver import PicoArm, SimulatedArm, target_position


class ArmTests(unittest.TestCase):
    def setUp(self):
        self.arm = SimulatedArm(100, 20)
        self.cancel = threading.Event()

    def test_requires_origin(self):
        with self.assertRaises(ValueError):
            self.arm.execute("move", 10, self.cancel)

    def test_relative_distance(self):
        self.arm.execute("zero", 0, self.cancel)
        self.assertEqual(self.arm.execute("move", 10, self.cancel).position_mm, 10)
        self.assertEqual(self.arm.execute("move", 10, self.cancel).position_mm, 20)
        result = self.arm.execute("move", -5, self.cancel)
        self.assertEqual(result.actual_distance_mm, -5)
        self.assertEqual(result.position_mm, 15)

    def test_invalid_ranges(self):
        for position, distance, maximum, step in (
            (0, -1, 100, 20), (95, 10, 100, 20), (0, 21, 100, 20),
            (0, 0, 100, 20), (0, float("nan"), 100, 20), (0, 10, 0, 20),
            (0, float("inf"), 100, 20)):
            with self.assertRaises(ValueError):
                target_position(position, distance, maximum, step)

    def test_cancel(self):
        self.arm.execute("zero", 0, self.cancel)
        self.cancel.set()
        result = self.arm.execute("move", 10, self.cancel)
        self.assertFalse(result.success)
        self.assertEqual(result.position_mm, 0)


class FakeSerial:
    """Pico相当の応答を分割して返す。実ポートには一切接続しない。"""
    def __init__(self, *args, **kwargs):
        self.is_open, self.rx, self.sent, self.position = True, b"", [], 0.0

    @property
    def in_waiting(self):
        return len(self.rx)

    def write(self, data):
        text = data.decode().strip()
        self.sent.append(text)
        fields = text.split(",")
        if text == "Q":
            self.rx += b"HELLO,ARM_EXTENSION_V1\n"
        elif fields[0] == "C":
            self.rx += b"CONFIG_OK\n"
        elif fields[0] == "Z":
            self.position = 0
            self.rx += f"D,{fields[1]},1,0,0,1,0,ZERO_OK\n".encode()
        elif fields[0] == "M":
            distance = float(fields[2])
            self.position += distance
            self.rx += f"D,{fields[1]},1,{distance},{self.position},1,64,TARGET_STOP_COMMAND\n".encode()
        return len(data)

    def read(self, count):
        count = min(count, 7)
        result, self.rx = self.rx[:count], self.rx[count:]
        return result

    def close(self):
        self.is_open = False


class SerialTests(unittest.TestCase):
    def setUp(self):
        # serial.Serial自体を置換して、USBを開くことを防ぐ。
        self.serial_patch = patch("serial.Serial", FakeSerial)
        self.serial_patch.start()
        self.sleep_patch = patch("arm_driver.time.sleep")
        self.sleep_patch.start()

    def tearDown(self):
        self.sleep_patch.stop()
        self.serial_patch.stop()

    def test_handshake_zero_and_move_with_fragmented_input(self):
        arm = PicoArm("FAKE", "", 100, 20, 45)
        self.assertFalse(any(s.startswith("M,") for s in arm.serial.sent))
        with self.assertRaises(ValueError):
            arm.execute("move", 10, threading.Event())
        arm.execute("zero", 0, threading.Event())
        result = arm.execute("move", 10, threading.Event())
        self.assertTrue(result.success)
        self.assertEqual(result.position_mm, 10)
        result = arm.execute("move", -5, threading.Event())
        self.assertEqual(result.position_mm, 5)
        arm.close()
        self.assertEqual(arm.serial.sent[-1], "S")
        self.assertFalse(arm.serial.is_open)

    def test_rejected_distance_is_not_sent(self):
        arm = PicoArm("FAKE", "", 100, 20, 45)
        arm.execute("zero", 0, threading.Event())
        before = list(arm.serial.sent)
        with self.assertRaises(ValueError):
            arm.execute("move", 99, threading.Event())
        self.assertEqual(before, arm.serial.sent)
        arm.close()


if __name__ == "__main__":
    unittest.main()
