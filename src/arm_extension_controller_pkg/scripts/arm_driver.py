"""ROS-independent USB communication and simulation. No movement on import."""
import math
import threading
import time
from dataclasses import dataclass


@dataclass
class Result:
    success: bool
    position_valid: bool
    actual_distance_mm: float
    position_mm: float
    message: str


def target_position(position, distance, max_position, max_move):
    if not all(math.isfinite(v) for v in (position, distance, max_position, max_move)):
        raise ValueError("数値は有限値にしてください")
    if max_position <= 0 or max_move <= 0:
        raise ValueError("max_position_mm と max_move_mm を正の値で設定してください")
    if distance == 0 or abs(distance) > max_move:
        raise ValueError(f"移動量は0以外、1回±{max_move:g}mm以内にしてください")
    target = position + distance
    if not 0 <= target <= max_position:
        raise ValueError(f"目標が範囲外です: {target:.2f}mm（0～{max_position:g}mm）")
    return target


class SimulatedArm:
    def __init__(self, max_position, max_move):
        self.max_position, self.max_move = max_position, max_move
        self.position, self.referenced = 0.0, False

    def execute(self, command, distance, cancel):
        if command == "zero":
            self.position, self.referenced = 0.0, True
            return Result(True, True, 0.0, 0.0, "SIMULATION: 原点を0に設定")
        if command == "home":
            self.position, self.referenced = 0.0, True
            return Result(True, True, 0.0, 0.0, "SIMULATION: 原点復帰完了")
        if not self.referenced:
            raise ValueError("先に zero で原点を設定してください")
        target = target_position(self.position, distance, self.max_position, self.max_move)
        start = self.position
        # Ten small steps make cancellation testable without real hardware.
        for index in range(1, 11):
            if cancel.wait(0.02):
                return Result(False, True, self.position - start, self.position, "SIMULATION: 中止")
            self.position = start + (target - start) * index / 10
        return Result(True, True, self.position - start, self.position, "SIMULATION: 完了")

    def close(self):
        pass


class PicoArm:
    def __init__(self, port, serial_number, max_position, max_move, timeout):
        import serial
        from serial.tools import list_ports
        if not port:
            matches = [p.device for p in list_ports.comports()
                       if serial_number and p.serial_number == serial_number]
            if len(matches) != 1:
                raise ValueError("port または一意な serial_number を指定してください")
            port = matches[0]
        if max_position <= 0 or max_move <= 0:
            raise ValueError("実機では max_position_mm と max_move_mm の設定が必要です")
        self.max_position, self.max_move = max_position, max_move
        self.timeout = timeout
        self.position, self.referenced, self.sequence = 0.0, False, 0
        self.buffer = b""
        self.tx_lock = threading.Lock()
        self.serial = serial.Serial(port, 115200, timeout=0.05, write_timeout=0.2)
        try:
            time.sleep(2)  # USB接続直後の準備待ち。ここでは動かさない。
            self.send("S")
            self.send("Q")
            self.wait_for("HELLO,ARM_EXTENSION_V1")
            self.send(f"C,{max_position:.3f},{max_move:.3f}")
            self.wait_for("CONFIG_OK")
        except BaseException:
            self.close()
            raise

    def send(self, text):
        with self.tx_lock:
            self.serial.write((text + "\n").encode("ascii"))

    def lines(self):
        self.buffer += self.serial.read(max(1, self.serial.in_waiting))
        if len(self.buffer) > 4096:
            raise RuntimeError("受信データが長すぎます")
        result = []
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            result.append(line.decode("ascii", errors="strict").strip())
        return result

    def wait_for(self, expected):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if expected in self.lines():
                return
        raise RuntimeError(f"Pico応答なし: {expected}。専用Arduinoプログラムを確認してください")

    def execute(self, command, distance, cancel):
        if command == "move":
            if not self.referenced:
                raise ValueError("先に zero で原点を設定してください")
            target_position(self.position, distance, self.max_position, self.max_move)
        self.sequence += 1
        request_id = self.sequence
        if command == "zero":
            self.send(f"Z,{request_id}")
        elif command == "home":
            self.send(f"H,{request_id}")
        else:
            self.send(f"M,{request_id},{distance:.3f}")
        deadline, heartbeat, stopping = time.monotonic() + self.timeout, 0.0, False
        try:
            while time.monotonic() < deadline:
                now = time.monotonic()
                if cancel.is_set() and not stopping:
                    self.send("S")
                    stopping = True
                if now - heartbeat >= 0.1:
                    self.send("K")
                    heartbeat = now
                for line in self.lines():
                    fields = line.split(",", 7)
                    if len(fields) == 8 and fields[:2] == ["D", str(request_id)]:
                        success, actual, position, valid, _, reason = fields[2:]
                        actual, position = float(actual), float(position)
                        if valid not in ("0", "1") or not all(map(math.isfinite, (actual, position))):
                            raise RuntimeError("不正なPico応答")
                        self.position, self.referenced = position, valid == "1"
                        return Result(success == "1" and not stopping, self.referenced,
                                      actual, position, reason)
            raise TimeoutError("Picoの完了応答がありません。再送せず停止・配線を確認してください")
        except BaseException:
            self.referenced = False  # タイムアウト後の位置は信用しない。
            try:
                self.send("S")
            except Exception:
                pass
            raise

    def close(self):
        if self.serial.is_open:
            try:
                self.send("S")
            finally:
                self.serial.close()
