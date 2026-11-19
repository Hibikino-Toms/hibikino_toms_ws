"""Joint-space adapter for RMD q1/q2 over an Arduino bridge and DXL q3."""
from __future__ import annotations

import math
import threading
import time


class _RmdSerialBridge:
    """Line protocol client for ``module/arduino_rmd_arm_bridge``."""

    def __init__(self, serial_number: str, baudrate: int, timeout_sec: float):
        try:
            import serial
            from serial.tools import list_ports
        except ImportError as exc:
            raise RuntimeError("can_mixed backend requires pyserial") from exc
        port = next((p.device for p in list_ports.comports()
                     if p.serial_number == serial_number), None)
        if port is None:
            raise RuntimeError(f"Arduino serial {serial_number!r} was not found")
        self._serial = serial.Serial(port, baudrate=baudrate,
                                     timeout=min(0.1, timeout_sec),
                                     write_timeout=timeout_sec, exclusive=True)
        self.timeout_sec = timeout_sec
        self._lock = threading.RLock()
        self._seq = 0
        self._fault = None
        self._closed = False
        self.startup_diagnostics = []
        self.last_diagnostics = []
        try:
            self._await_ready()
        except BaseException:
            self._serial.close()
            raise

    def _await_ready(self):
        # Opening the Uno's CDC port resets it. Wait for the new firmware's
        # explicit stopped-ready banner; never infer readiness from a delay.
        deadline = time.monotonic() + 6.0
        ready = False
        transcript = []
        while time.monotonic() < deadline:
            line = self._serial.readline().decode("ascii", errors="replace").strip()
            if not line:
                continue
            transcript.append(line)
            if line.startswith("DIAG,"):
                self.startup_diagnostics.append(line)
            if line == "READY,RMD_ARM_V1,STOPPED":
                ready = True
                break
            if line.startswith("ERR,"):
                raise RuntimeError(f"Arduino bridge startup error: {line}; received={transcript}")
        if not ready:
            raise RuntimeError(f"Arduino bridge did not report stopped-ready: {transcript}")
        response = self._request("PING", "PONG,RMD_ARM_V1", timeout=1.0)
        if response != "PONG,RMD_ARM_V1":
            raise RuntimeError(f"unexpected Arduino bridge identity: {response}")

    def _request(self, command: str, expected: str, timeout: float | None = None) -> str:
        with self._lock:
            if self._closed:
                raise RuntimeError("Arduino bridge is closed")
            if self._fault:
                raise RuntimeError(f"Arduino bridge fault latched: {self._fault}")
            self._serial.write((command + "\n").encode("ascii"))
            self._serial.flush()
            deadline = time.monotonic() + (self.timeout_sec if timeout is None else timeout)
            seen = []
            while time.monotonic() < deadline:
                line = self._serial.readline().decode("ascii", errors="replace").strip()
                if not line:
                    continue
                seen.append(line)
                if line.startswith("DIAG,"):
                    self.last_diagnostics = (self.last_diagnostics + [line])[-8:]
                if line.startswith("FAULT,"):
                    self._fault = line
                    raise RuntimeError(f"Arduino bridge reported {line}")
                if line.startswith("ERR,"):
                    raise RuntimeError(f"Arduino bridge rejected {command}: {line}; received={seen}")
                if line == expected or line.startswith(expected):
                    return line
            raise TimeoutError(f"Arduino response timeout for {command}; received={seen}")

    def _next_seq(self) -> int:
        self._seq = (self._seq + 1) % 2_000_000_000
        return self._seq

    def read(self):
        seq = self._next_seq()
        line = self._request(f"READ,{seq}", f"S,{seq},")
        fields = line.split(",")
        if len(fields) != 13 or fields[0] != "S" or int(fields[1]) != seq:
            raise RuntimeError(f"malformed Arduino state: {line}")
        data = [int(value) for value in fields[2:]]
        armed = data[0]
        state = {
            "armed": armed,
            "x8_position_cdeg": data[1], "x8_speed_dps": data[2],
            "x8_temp_c": data[3], "x8_voltage_10v": data[4], "x8_errors": data[5],
            "x6_position_cdeg": data[6], "x6_speed_dps": data[7],
            "x6_temp_c": data[8], "x6_voltage_10v": data[9], "x6_errors": data[10],
        }
        for name in ("x8_position_cdeg", "x8_speed_dps", "x8_temp_c", "x8_voltage_10v",
                     "x8_errors", "x6_position_cdeg", "x6_speed_dps", "x6_temp_c",
                     "x6_voltage_10v", "x6_errors"):
            if not -100_000 <= state[name] <= 100_000:
                raise RuntimeError(f"invalid Arduino state field {name}={state[name]}")
        return state

    def configure_and_arm(self, bounds):
        x8_low, x8_high, x6_low, x6_high = bounds
        self._request(f"CONFIG,{x8_low},{x8_high},{x6_low},{x6_high}", "OK,CONFIG")
        self._request("ARM", "OK,ARMED", timeout=1.5)

    def move(self, x8_cdeg: int, x6_cdeg: int, speed_dps: int):
        seq = self._next_seq()
        self._request(f"MOVE,{seq},{x8_cdeg},{x6_cdeg},{speed_dps},{speed_dps}",
                      f"OK,MOVE,{seq}")

    def start_heartbeat(self, period_sec: float = 0.15):
        self._heartbeat_period = period_sec
        self._heartbeat_stop = threading.Event()
        self._heartbeat = threading.Thread(target=self._heartbeat_loop,
                                           name="rmd-bridge-heartbeat", daemon=True)
        self._heartbeat.start()

    def _heartbeat_loop(self):
        while not self._heartbeat_stop.wait(self._heartbeat_period):
            try:
                self._request("HB", "OK,HB", timeout=0.5)
            except Exception as exc:
                self._fault = str(exc)
                try:
                    with self._lock:
                        if not self._closed:
                            self._serial.write(b"STOP\n")
                            self._serial.flush()
                except Exception:
                    pass
                return

    def stop(self):
        if self._closed:
            return
        try:
            # STOP is intentionally permitted even after a communication fault.
            with self._lock:
                self._serial.write(b"STOP\n")
                self._serial.flush()
                self._serial.readline()
        except Exception:
            pass

    def close(self):
        if self._closed:
            return
        if hasattr(self, "_heartbeat_stop"):
            self._heartbeat_stop.set()
            self._heartbeat.join(timeout=0.7)
        self.stop()
        with self._lock:
            self._closed = True
            self._serial.close()


class _DynamixelQ3:
    """Single ID-5 adapter retaining the previous q3 mapping and limits."""

    def __init__(self, params, *, angle_trim_deg=0.0):
        self.angle_trim_deg = float(angle_trim_deg)
        if not math.isfinite(self.angle_trim_deg):
            raise ValueError("q3 angle_trim_deg must be finite")
        try:
            from dynamixel_sdk import PortHandler, PacketHandler, COMM_SUCCESS
            from serial.tools import list_ports
        except ImportError as exc:
            raise RuntimeError("q3 Dynamixel needs dynamixel-sdk and pyserial") from exc
        self.params = dict(params)
        self._comm_success = COMM_SUCCESS
        serial_number = str(params["U2D2_SERIAL_NUMBER"])
        device = next((p.device for p in list_ports.comports()
                       if p.serial_number == serial_number), None)
        if device is None:
            raise RuntimeError(f"U2D2 serial {serial_number!r} was not found")
        self.motor_id = int(params.get("q3_motor_id", 5))
        self.min_tick = int(params["DXL_MIN_POSITION_VALUE"])
        self.max_tick = int(params["DXL_MAX_POSITION_VALUE"])
        self.max_angle = float(params["MAX_ANGLE"])
        self.min_deg = float(params["DXL_5_MIN_DEG"])
        self.max_deg = float(params["DXL_5_MAX_DEG"])
        timeout_ms = int(params.get("communication_timeout_ms", 40))
        if (self.min_tick >= self.max_tick or self.max_angle <= 0 or
                not math.isfinite(self.max_angle) or self.min_deg >= self.max_deg or timeout_ms < 1):
            raise ValueError("invalid q3 Dynamixel range/scale/timeout")
        self.port = PortHandler(device)
        self.packet = PacketHandler(float(params["PROTOCOL_VERSION"]))
        if not self.port.openPort():
            raise RuntimeError("could not open U2D2 port")
        if not self.port.setBaudRate(int(params["BAUDRATE"])):
            self.port.closePort()
            raise RuntimeError("could not set U2D2 baudrate")
        if hasattr(self.port, "setPacketTimeoutMillis"):
            self.port.setPacketTimeoutMillis(timeout_ms)

    def _check(self, result, error, operation):
        if result != self._comm_success or error:
            raise RuntimeError(f"DXL q3 {operation} failed: communication={result}, error={error}")

    def _read(self, address, length):
        if length == 1:
            value, result, error = self.packet.read1ByteTxRx(self.port, self.motor_id, address)
        elif length == 4:
            value, result, error = self.packet.read4ByteTxRx(self.port, self.motor_id, address)
        else:
            raise ValueError("unsupported Dynamixel register width")
        self._check(result, error, f"read address {address}")
        return value

    def _write(self, address, value, length):
        if length == 1:
            result, error = self.packet.write1ByteTxRx(self.port, self.motor_id, address, value)
        elif length == 4:
            result, error = self.packet.write4ByteTxRx(self.port, self.motor_id, address, value)
        else:
            raise ValueError("unsupported Dynamixel register width")
        self._check(result, error, f"write address {address}")

    def activate(self):
        p = self.params
        mode = self._read(int(p["ADDR_OPERATING_MODE"]), 1)
        drive = self._read(int(p["ADDR_DRIVE_MODE"]), 1)
        torque = self._read(int(p["ADDR_TORQUE_ENABLE"]), 1)
        if mode != 3:
            raise RuntimeError(f"DXL q3 requires Position Control Mode 3; got {mode}")
        if drive & 0x08:
            raise RuntimeError("DXL q3 Torque On by Goal Update must be disabled")
        present = self._read(int(p["ADDR_PRESENT_POSITION"]), 4)
        if not self.min_tick <= present <= self.max_tick:
            raise RuntimeError(f"DXL q3 position {present} outside single-turn range")
        angle = (present-self.min_tick)/(self.max_tick-self.min_tick)*self.max_angle
        if not self.min_deg <= angle <= self.max_deg:
            raise RuntimeError(f"DXL q3 present angle {angle:.2f}deg outside configured limits")
        # Preserve the existing tracker profile setup for q3 (the fifth entry
        # in the former five-motor configuration).
        for key, address_key in (("PROFILE_ACCELS", "ADDR_PROFILE_ACCEL"),
                                 ("stream_profile_velocities", "ADDR_PROFILE_VELO")):
            values = p.get(key, [])
            if values:
                if len(values) != 5:
                    raise ValueError(f"{key} must contain the legacy five motor entries")
                self._write(int(p[address_key]), int(values[4]), 4)
        goal_address = int(p["ADDR_GOAL_POSITION"])
        tolerance = int(p.get("startup_hold_tolerance_ticks", 1))
        timeout = float(p.get("startup_readback_timeout_ms", 250)) / 1000.0
        if not math.isfinite(timeout) or not 0 < timeout <= 1.0 or tolerance not in (0, 1):
            raise ValueError("invalid q3 startup hold readback settings")
        self._write(goal_address, present, 4)
        deadline = time.monotonic() + timeout
        readbacks = []
        confirmed = False
        stable_samples = 0
        while True:
            goal = self._read(goal_address, 4)
            readbacks.append(goal)
            if abs(goal-present) <= tolerance:
                live_position = self._read(int(p["ADDR_PRESENT_POSITION"]), 4)
                live_torque = self._read(int(p["ADDR_TORQUE_ENABLE"]), 1)
                confirmed_goal = self._read(goal_address, 4)
                readbacks.append(confirmed_goal)
                angle = (live_position-self.min_tick)/(self.max_tick-self.min_tick)*self.max_angle
                # Bound the readback, live hold error AND drift from the initial
                # sample. Do not chase a hand-moved arm or require tick equality
                # inside a configured +/-1-count tolerance.
                valid = (live_torque == torque and
                         self.min_tick <= live_position <= self.max_tick and
                         self.min_tick <= confirmed_goal <= self.max_tick and
                         self.min_deg <= angle <= self.max_deg and
                         abs(live_position-present) <= tolerance and
                         abs(confirmed_goal-present) <= tolerance and
                         abs(confirmed_goal-live_position) <= tolerance)
                stable_samples = stable_samples+1 if valid else 0
                if stable_samples >= 2:
                    confirmed = True
                    break
            else:
                stable_samples = 0
            remaining = deadline-time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(0.005, remaining))
        if not confirmed:
            torque_now = self._read(int(p["ADDR_TORQUE_ENABLE"]), 1)
            now = self._read(int(p["ADDR_PRESENT_POSITION"]), 4)
            raise RuntimeError(
                f"DXL q3 startup hold readback mismatch: initial={present}, goals={readbacks}, "
                f"present_now={now}, torque={torque_now}; torque-enable was not requested")
        if torque == 0:
            self._write(int(p["ADDR_TORQUE_ENABLE"]), 1, 1)
        if self._read(int(p["ADDR_TORQUE_ENABLE"]), 1) != 1:
            raise RuntimeError("DXL q3 torque enable did not verify")
        return self.motor_id

    def read_joint(self):
        tick = self._read(int(self.params["ADDR_PRESENT_POSITION"]), 4)
        joint = self.joint_from_tick(tick)
        angle = (tick-self.min_tick)/(self.max_tick-self.min_tick)*self.max_angle
        if not self.min_deg-0.5 <= angle <= self.max_deg+0.5:
            raise RuntimeError(f"DXL q3 angle {angle:.2f}deg outside configured range")
        return joint

    def joint_from_tick(self, tick):
        """Convert the raw single-turn encoder value to calibrated joint radians."""
        if not self.min_tick <= tick <= self.max_tick:
            raise RuntimeError(f"DXL q3 present position {tick} outside encoder range")
        angle = (tick-self.min_tick)/(self.max_tick-self.min_tick)*self.max_angle
        joint = angle - 180.0 + self.angle_trim_deg
        return math.radians(joint)

    def send_joint(self, joint_rad):
        q3 = math.degrees(float(joint_rad))
        motor_angle = q3 + 180.0 - self.angle_trim_deg
        if not math.isfinite(motor_angle) or not self.min_deg <= motor_angle <= self.max_deg:
            raise ValueError(f"q3 target {motor_angle:.2f}deg outside {self.min_deg}..{self.max_deg}")
        tick = round(self.min_tick + motor_angle/self.max_angle*(self.max_tick-self.min_tick))
        self._write(int(self.params["ADDR_GOAL_POSITION"]), tick, 4)

    def close(self):
        if self.port.is_open:
            self.port.closePort()


class CanMixedMotorBackend:
    """Keep q1/q2/q3 in radians; translate all bus details below this layer."""

    def __init__(self, params, dxl_params, joint_limits_rad):
        self.params = dict(params)
        self.dxl_params = dict(dxl_params)
        self.joint_limits_rad = joint_limits_rad
        self.bridge = None
        self.q3 = None
        self.active = False
        self.calibration = None
        self.motor_bounds = None
        self.max_speed_dps = int(self.params.get("max_command_speed_dps", 15))
        self.bridge_timeout = float(self.params.get("communication_timeout_sec", 0.8))
        self.q3_trim_deg = float(self.params.get("q3", {}).get("angle_trim_deg", 0.0))
        if not math.isfinite(self.q3_trim_deg):
            raise ValueError("q3 angle_trim_deg must be finite")
        if not 1 <= self.max_speed_dps <= 60 or not math.isfinite(self.bridge_timeout) or self.bridge_timeout <= 0:
            raise ValueError("invalid CAN bridge speed or timeout")

    @staticmethod
    def _calibration_axis(config, name):
        axis = config.get(name, {})
        direction = axis.get("direction")
        q_ref = axis.get("reference_joint_deg")
        motor_ref = axis.get("reference_motor_cdeg")
        if direction not in (-1, 1) or q_ref is None or motor_ref is None:
            return None
        trim = float(axis.get("angle_trim_deg", 0.0))
        values = [float(q_ref), float(motor_ref), trim]
        if not all(math.isfinite(v) for v in values):
            raise ValueError(f"{name} calibration reference and angle_trim_deg must be finite")
        # q = q_ref + direction*(raw-raw_ref)/100 + trim.
        # Put trim into the effective zero so reads, inverse commands and
        # bridge bounds all use exactly the same calibration.
        return {"direction": int(direction), "reference_joint_deg": values[0],
                "angle_trim_deg": trim,
                "zero_cdeg": values[1] - direction * (values[0] + trim) * 100.0}

    def _read_rmd(self):
        state = self.bridge.read()
        self.last_state = dict(state, read_time_unix=time.time())
        for name in ("x8_errors", "x6_errors"):
            if state[name] != 0:
                raise RuntimeError(f"RMD motor error {name}={state[name]:#06x}")
        for name in ("x8_voltage_10v", "x6_voltage_10v"):
            if not 200 <= state[name] <= 550:
                raise RuntimeError(f"RMD motor voltage outside 20..55 V: {name}={state[name]/10:.1f}V")
        return state

    def _joint_from_position(self, position_cdeg, axis):
        zero = self.calibration[axis]["zero_cdeg"]
        direction = self.calibration[axis]["direction"]
        return math.radians((position_cdeg-zero)/(100.0*direction))

    def _motor_target(self, joint_rad, axis):
        zero = self.calibration[axis]["zero_cdeg"]
        direction = self.calibration[axis]["direction"]
        return round(zero + direction*math.degrees(joint_rad)*100.0)

    def _derive_bounds(self):
        result = []
        for axis, limit in zip(("q1", "q2"), self.joint_limits_rad[:2]):
            values = [self._motor_target(float(q), axis) for q in limit]
            result.extend([min(values), max(values)])
        return result

    def activate(self):
        self.bridge = _RmdSerialBridge(
            str(self.params["arduino_serial_number"]),
            int(self.params.get("baudrate", 115200)), self.bridge_timeout)
        # READ is read-only and works while disarmed. Capture raw encoder values
        # before requiring calibration so the operator can use them in YAML.
        state = self._read_rmd()
        q1cal = self._calibration_axis(self.params, "q1")
        q2cal = self._calibration_axis(self.params, "q2")
        if not bool(self.params.get("calibration_valid", False)) or q1cal is None or q2cal is None:
            raise RuntimeError(
                "CAN joint calibration is incomplete; no RMD ARM, DXL torque-enable, or motion was sent. "
                f"Read-only output angles: X8 ID0={state['x8_position_cdeg']/100:.2f}deg, "
                f"X6 ID1={state['x6_position_cdeg']/100:.2f}deg. Set each q axis direction and "
                "a physically verified reference_joint_deg/reference_motor_cdeg in YAML, then set calibration_valid=true.")
        self.calibration = {"q1": q1cal, "q2": q2cal}
        for name, position, calibration, limit in (
                ("q1", state["x8_position_cdeg"], q1cal, self.joint_limits_rad[0]),
                ("q2", state["x6_position_cdeg"], q2cal, self.joint_limits_rad[1])):
            q = self._joint_from_position(position, name)
            margin = math.radians(0.5)
            if not limit[0]-margin <= q <= limit[1]+margin:
                raise RuntimeError(f"{name} motor reading implies joint {math.degrees(q):.2f}deg outside configured limits")
        self.motor_bounds = self._derive_bounds()
        if any(abs(value) > 72000 for value in self.motor_bounds):
            raise ValueError("derived RMD raw position limits exceed bridge's +/-720deg safety window")
        if abs(state["x8_speed_dps"]) > 10 or abs(state["x6_speed_dps"]) > 10:
            raise RuntimeError("RMD motors are not stationary (speed must be within +/-10 dps at activation)")

        # The bridge ARM command is preflight only; the first position command
        # is issued later by the tracker's single control-timer owner.
        self.bridge.configure_and_arm(self.motor_bounds)
        try:
            self.q3 = _DynamixelQ3(self.dxl_params, angle_trim_deg=self.q3_trim_deg)
            q3_id = self.q3.activate()
        except Exception:
            self.bridge.stop()
            raise
        self.bridge.start_heartbeat()
        self.active = True
        self.activation_report = f"RMD X8 ID0 + X6 ID1; Dynamixel q3 ID {q3_id}"
        return self.activation_report

    def read_joints(self):
        if not self.active:
            raise RuntimeError("CAN mixed backend is not activated")
        try:
            state = self._read_rmd()
            if state["armed"] != 1:
                raise RuntimeError("Arduino bridge is disarmed")
            q1 = self._joint_from_position(state["x8_position_cdeg"], "q1")
            q2 = self._joint_from_position(state["x6_position_cdeg"], "q2")
            q3 = self.q3.read_joint()
            for index, q in enumerate((q1, q2, q3)):
                low, high = self.joint_limits_rad[index]
                if q < low-math.radians(0.5) or q > high+math.radians(0.5):
                    raise RuntimeError(f"q{index+1} measured angle {math.degrees(q):.2f}deg outside joint limits")
            return [q1, q2, q3]
        except Exception:
            self._safe_stop()
            raise

    def send_joints(self, joints_rad):
        if not self.active:
            raise RuntimeError("CAN mixed backend is not activated")
        if len(joints_rad) != 3 or not all(math.isfinite(float(v)) for v in joints_rad):
            raise ValueError("expected three finite joint angles")
        for i, q in enumerate(joints_rad):
            low, high = self.joint_limits_rad[i]
            if not low <= float(q) <= high:
                raise ValueError(f"q{i+1}={math.degrees(float(q)):.2f}deg outside configured limits")
        x8_target = self._motor_target(joints_rad[0], "q1")
        x6_target = self._motor_target(joints_rad[1], "q2")
        if not self.motor_bounds[0] <= x8_target <= self.motor_bounds[1] or not self.motor_bounds[2] <= x6_target <= self.motor_bounds[3]:
            raise ValueError("derived CAN motor target is outside configured raw range")
        # q3 and q1/q2 use separate physical buses. Both receive their new goals
        # in the same control tick; q1 and q2 are sent together by one CAN cycle.
        try:
            self.q3.send_joint(joints_rad[2])
            self.bridge.move(x8_target, x6_target, self.max_speed_dps)
        except Exception:
            self._safe_stop()
            raise

    def _safe_stop(self):
        if self.bridge is not None:
            self.bridge.stop()
        if self.q3 is not None:
            try:
                measured_q3 = self.q3.read_joint()
                self.q3.send_joint(measured_q3)
            except Exception:
                # Keep its existing position-mode hold; never disable torque.
                pass

    def close(self):
        if self.bridge is not None:
            self.bridge.close()
        if self.q3 is not None:
            self.q3.close()
        self.active = False
