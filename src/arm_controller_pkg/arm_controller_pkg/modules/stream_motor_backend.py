"""Non-blocking joint command interface for the five-motor planar arm."""
import math
import time


class SimulatedMotorBackend:
    """Five-motor software model; no serial discovery or hardware access."""
    def __init__(self, params, initial_joints_rad):
        if len(initial_joints_rad) != 3 or not all(math.isfinite(float(v)) for v in initial_joints_rad):
            raise ValueError("simulator initial state must contain three finite joints")
        self.joints = [math.degrees(float(v)) for v in initial_joints_rad]
        self.goal = list(self.joints)
        self.max_speed = float(params.get("sim_max_joint_speed_rad_s", 0.8))
        self._last = time.monotonic()
        if self.max_speed <= 0:
            raise ValueError("sim_max_joint_speed_rad_s must be positive")

    def activate(self):
        """Simulation requires no torque register writes."""
        return []

    def read_joints(self):
        now = time.monotonic()
        dt = min(now - self._last, 0.1)
        self._last = now
        max_step = math.degrees(self.max_speed * dt)
        self.joints = [q + max(-max_step, min(max_step, g - q)) for q, g in zip(self.joints, self.goal)]
        return [math.radians(v) for v in self.joints]

    def send_joints(self, joints_rad):
        if len(joints_rad) != 3 or not all(math.isfinite(float(v)) for v in joints_rad):
            raise ValueError("expected three finite joint angles")
        self.goal = [math.degrees(v) for v in joints_rad]

    def close(self):
        pass


class DynamixelFiveMotorBackend:
    """Dynamixel SDK adapter: joint-space API, paired motor mapping below it."""
    def __init__(self, params):
        try:
            from dynamixel_sdk import (PortHandler, PacketHandler, GroupSyncRead,
                                       GroupSyncWrite, COMM_SUCCESS)
            import serial.tools.list_ports
        except ImportError as exc:
            raise RuntimeError("Dynamixel backend needs dynamixel-sdk and pyserial") from exc
        self._comm_success = COMM_SUCCESS
        self._sdk = __import__("dynamixel_sdk")
        self.params = dict(params)
        self.ids = [int(v) for v in params["DXL_IDs"]]
        if self.ids != [1, 2, 3, 4, 5]:
            raise ValueError("DXL_IDs must be [1,2,3,4,5] for the existing paired-joint mapping")
        serial_number = str(params["U2D2_SERIAL_NUMBER"])
        device = next((p.device for p in serial.tools.list_ports.comports()
                       if p.serial_number == serial_number), None)
        if device is None:
            raise RuntimeError(f"U2D2 serial {serial_number!r} was not found")
        self.min_tick = int(params["DXL_MIN_POSITION_VALUE"])
        self.max_tick = int(params["DXL_MAX_POSITION_VALUE"])
        self.max_angle = float(params["MAX_ANGLE"])
        timeout_ms = int(params.get("communication_timeout_ms", 40))
        if self.min_tick >= self.max_tick or not math.isfinite(self.max_angle) or self.max_angle <= 0:
            raise ValueError("invalid Dynamixel encoder range or angle scale")
        if timeout_ms < 1:
            raise ValueError("communication_timeout_ms must be positive")
        self.port = PortHandler(device)
        self.packet = PacketHandler(float(params["PROTOCOL_VERSION"]))
        if not self.port.openPort():
            raise RuntimeError("Could not open/configure Dynamixel port")
        if not self.port.setBaudRate(int(params["BAUDRATE"])):
            self.port.closePort()
            raise RuntimeError("Could not open/configure Dynamixel port")
        if hasattr(self.port, "setPacketTimeoutMillis"):
            self.port.setPacketTimeoutMillis(timeout_ms)
        self.read_group = GroupSyncRead(self.port, self.packet,
                                       int(params["ADDR_PRESENT_POSITION"]),
                                       int(params["LEN_PRESENT_POSITION"]))
        self.write_group = GroupSyncWrite(self.port, self.packet,
                                          int(params["ADDR_GOAL_POSITION"]),
                                          int(params["LEN_GOAL_POSITION"]))
        for motor_id in self.ids:
            if not self.read_group.addParam(motor_id):
                raise RuntimeError(f"Could not register DXL ID {motor_id} for reading")
        self.present_address = int(params["ADDR_PRESENT_POSITION"])
        self.present_length = int(params["LEN_PRESENT_POSITION"])
        # Configure profile parameters once at startup. A new goal position may
        # still make actuator firmware re-plan its position profile each packet.
        velocities = params.get("stream_profile_velocities", [])
        accelerations = params.get("PROFILE_ACCELS", [])
        for address_key, values in (("ADDR_PROFILE_ACCEL", accelerations),
                                     ("ADDR_PROFILE_VELO", velocities)):
            if values:
                if len(values) != 5:
                    raise ValueError(f"{address_key} profile must contain five values")
                for motor_id, value in zip(self.ids, values):
                    result, error = self.packet.write4ByteTxRx(
                        self.port, motor_id, int(params[address_key]), int(value))
                    if result != self._comm_success or error:
                        raise RuntimeError(f"Failed to set one-time profile on ID {motor_id}")

    def _check_reply(self, result, error, motor_id, operation):
        if result != self._comm_success or error:
            raise RuntimeError(
                f"DXL {motor_id} {operation} failed: "
                f"communication={result}, device_error={error}")

    def _startup_tolerance(self):
        value = self.params.get("startup_hold_tolerance_ticks", 1)
        if isinstance(value, bool) or value not in (0, 1):
            raise ValueError("startup_hold_tolerance_ticks must be 0 or 1")
        return int(value)

    def _validate_startup_tick(self, motor_id, tick):
        if not self.min_tick <= tick <= self.max_tick:
            raise RuntimeError(f"DXL {motor_id}: startup position {tick} outside single-turn range")
        angle = (tick - self.min_tick) / (self.max_tick - self.min_tick) * self.max_angle
        low = float(self.params[f"DXL_{motor_id}_MIN_DEG"])
        high = float(self.params[f"DXL_{motor_id}_MAX_DEG"])
        if not low <= angle <= high:
            raise RuntimeError(f"DXL {motor_id}: startup position {angle:.2f}deg outside {low}..{high}")

    def _verify_hold_goal(self, motor_id, expected):
        """Poll the goal register only; never wait for physical arrival.

        A successful write acknowledgement alone is not a verified goal value.
        A one-count difference is accepted ONLY with torque off and a second
        goal read matching fresh measured position. Larger discrepancies fail.
        """
        started = time.monotonic()
        timeout = float(self.params.get("startup_readback_timeout_ms", 100)) / 1000.
        if not math.isfinite(timeout) or not 0 < timeout <= 1.0:
            raise ValueError("startup_readback_timeout_ms must be in (0, 1000]")
        deadline = started + timeout
        tolerance = self._startup_tolerance()
        samples = []
        while True:
            value, result, error = self.packet.read4ByteTxRx(
                self.port, motor_id, int(self.params["ADDR_GOAL_POSITION"]))
            self._check_reply(result, error, motor_id, "verify hold goal")
            samples.append(value)
            if value == expected:
                return {"id": motor_id, "expected": expected, "samples": samples,
                        "reason": "exact",
                        "elapsed_ms": (time.monotonic() - started) * 1000.}
            if abs(value - expected) <= tolerance:
                present, result, error = self.packet.read4ByteTxRx(
                    self.port, motor_id, int(self.params["ADDR_PRESENT_POSITION"]))
                self._check_reply(result, error, motor_id, "verify current hold position")
                torque, result, error = self.packet.read1ByteTxRx(
                    self.port, motor_id, int(self.params["ADDR_TORQUE_ENABLE"]))
                self._check_reply(result, error, motor_id, "verify current hold torque")
                confirmed, result, error = self.packet.read4ByteTxRx(
                    self.port, motor_id, int(self.params["ADDR_GOAL_POSITION"]))
                self._check_reply(result, error, motor_id, "confirm current hold goal")
                samples.append(confirmed)
                if torque == 0 and value == present == confirmed:
                    self._validate_startup_tick(motor_id, present)
                    return {"id": motor_id, "expected": expected, "samples": samples,
                            "reason": "current_hold", "present": present,
                            "elapsed_ms": (time.monotonic() - started) * 1000.}
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(0.005, remaining))

        # Best-effort diagnostics must preserve the original mismatch reason.
        diagnostics = []
        for name, reader, address in (
                ("present_now", self.packet.read4ByteTxRx, self.params["ADDR_PRESENT_POSITION"]),
                ("torque", self.packet.read1ByteTxRx, self.params["ADDR_TORQUE_ENABLE"])):
            try:
                value, result, error = reader(self.port, motor_id, int(address))
                self._check_reply(result, error, motor_id, f"diagnostic {name}")
                diagnostics.append(f"{name}={value}")
            except Exception as exc:
                diagnostics.append(f"{name}=unavailable({exc})")
        raise RuntimeError(
            f"DXL {motor_id}: hold goal readback mismatch: "
            f"address={self.params['ADDR_GOAL_POSITION']}, expected={expected}, "
            f"readbacks={samples}, elapsed_ms={(time.monotonic() - started)*1000.:.1f}, "
            f"{', '.join(diagnostics)}; no torque-enable writes issued")

    def activate(self):
        """Stage each motor's measured position before enabling any torque.

        Called by the sole I/O owner after checking for competing services.
        Any failure aborts startup; the caller must not automatically retry or
        disable already-enabled motors (the mechanism may require holding).
        """
        torque_address = int(self.params["ADDR_TORQUE_ENABLE"])
        mode_address = int(self.params["ADDR_OPERATING_MODE"])
        drive_address = int(self.params["ADDR_DRIVE_MODE"])
        goal_address = int(self.params["ADDR_GOAL_POSITION"])
        hold_check = self.params.get("startup_hold_check", "strict")
        if hold_check not in ("strict", "acknowledged"):
            raise ValueError("startup_hold_check must be strict or acknowledged")
        timeout = float(self.params.get("startup_readback_timeout_ms", 100))
        if not math.isfinite(timeout) or not 0 < timeout <= 1000:
            raise ValueError("startup_readback_timeout_ms must be in (0, 1000]")
        self.startup_readback_report = []
        tolerance = self._startup_tolerance()
        torque_states = []
        # Inspect all motors before writing a hold goal or enabling a motor.
        for motor_id in self.ids:
            mode, result, error = self.packet.read1ByteTxRx(self.port, motor_id, mode_address)
            self._check_reply(result, error, motor_id, "read operating mode")
            if mode != 3:
                raise RuntimeError(f"DXL {motor_id}: Position Control Mode(3) required; got {mode}")
            drive, result, error = self.packet.read1ByteTxRx(self.port, motor_id, drive_address)
            self._check_reply(result, error, motor_id, "read drive mode")
            if drive & 0x08:
                raise RuntimeError(f"DXL {motor_id}: Torque On by Goal Update must be disabled before staged startup")
            torque, result, error = self.packet.read1ByteTxRx(self.port, motor_id, torque_address)
            self._check_reply(result, error, motor_id, "read torque")
            if torque not in (0, 1):
                raise RuntimeError(f"DXL {motor_id}: invalid torque state {torque}")
            torque_states.append(torque)

        ticks = self._read_ticks()
        for motor_id, tick in zip(self.ids, ticks):
            # Torque-on in position mode can reset multi-turn present position.
            # Do not normalize an unknown mechanical position into a new goal.
            self._validate_startup_tick(motor_id, tick)

        # Individual acknowledged writes preserve the actual positions of both
        # paired motors, without rounding/mirroring a representative joint.
        for motor_id, tick in zip(self.ids, ticks):
            if hold_check == "acknowledged":
                # Hand support may move while inspecting the other motors.
                # Use a fresh position just before this motor's hold write.
                tick, result, error = self.packet.read4ByteTxRx(
                    self.port, motor_id, int(self.params["ADDR_PRESENT_POSITION"]))
                self._check_reply(result, error, motor_id, "read fresh startup position")
                self._validate_startup_tick(motor_id, tick)
            result, error = self.packet.write4ByteTxRx(self.port, motor_id, goal_address, tick)
            self._check_reply(result, error, motor_id, "stage hold goal")
            if hold_check == "strict":
                self.startup_readback_report.append(self._verify_hold_goal(motor_id, tick))

        # Recheck ALL motors after staging, before the first torque-on write.
        # A servo may have moved while the other motors were being inspected.
        for motor_id, initial in (zip(self.ids, ticks) if hold_check == "strict" else []):
            goal, result, error = self.packet.read4ByteTxRx(self.port, motor_id, goal_address)
            self._check_reply(result, error, motor_id, "final hold goal")
            present, result, error = self.packet.read4ByteTxRx(
                self.port, motor_id, int(self.params["ADDR_PRESENT_POSITION"]))
            self._check_reply(result, error, motor_id, "final hold position")
            self._validate_startup_tick(motor_id, goal)
            self._validate_startup_tick(motor_id, present)
            if max(abs(goal - initial), abs(present - initial), abs(goal - present)) > tolerance:
                raise RuntimeError(
                    f"DXL {motor_id}: startup hold changed before torque ON: "
                    f"initial={initial}, goal={goal}, present={present}, tolerance={tolerance} tick; "
                    "no torque-enable writes issued")

        for motor_id, torque in zip(self.ids, torque_states):
            if torque == 0:
                result, error = self.packet.write1ByteTxRx(self.port, motor_id, torque_address, 1)
                self._check_reply(result, error, motor_id, "enable torque")
        for motor_id in self.ids:
            value, result, error = self.packet.read1ByteTxRx(self.port, motor_id, torque_address)
            self._check_reply(result, error, motor_id, "verify torque")
            if value != 1:
                raise RuntimeError(f"DXL {motor_id}: torque remains OFF; tracking will not start")
        return list(self.ids)

    def _read_ticks(self):
        result = self.read_group.txRxPacket()
        if result != self._comm_success:
            raise RuntimeError(f"Dynamixel read timed out/failed: {self.packet.getTxRxResult(result)}")
        ticks = []
        for motor_id in self.ids:
            if not self.read_group.isAvailable(motor_id, self.present_address, self.present_length):
                raise RuntimeError(f"No present position for Dynamixel ID {motor_id}")
            ticks.append(self.read_group.getData(motor_id, self.present_address, self.present_length))
        return ticks

    def read_joints(self):
        ticks = self._read_ticks()
        deg = [(v - self.min_tick) / (self.max_tick - self.min_tick) * self.max_angle for v in ticks]
        # IDs 1/3/5 represent q1/q2/q3; IDs 2/4 are mirrored mechanically.
        return [math.radians(deg[0] - 90.), math.radians(deg[2] - 90.), math.radians(deg[4] - 180.)]

    def send_joints(self, joints_rad):
        if len(joints_rad) != 3 or not all(math.isfinite(float(v)) for v in joints_rad):
            raise ValueError("expected three finite joint angles")
        q1, q2, q3 = [math.degrees(float(v)) for v in joints_rad]
        motor_angles = [q1 + 90., 360. - (q1 + 90.), q2 + 90.,
                        360. - (q2 + 90.), q3 + 180.]
        motor_limits = [(float(params_min), float(params_max)) for params_min, params_max in (
            (self.params["DXL_1_MIN_DEG"], self.params["DXL_1_MAX_DEG"]),
            (self.params["DXL_2_MIN_DEG"], self.params["DXL_2_MAX_DEG"]),
            (self.params["DXL_3_MIN_DEG"], self.params["DXL_3_MAX_DEG"]),
            (self.params["DXL_4_MIN_DEG"], self.params["DXL_4_MAX_DEG"]),
            (self.params["DXL_5_MIN_DEG"], self.params["DXL_5_MAX_DEG"]))]
        for motor_id, angle, bounds in zip(self.ids, motor_angles, motor_limits):
            if not bounds[0] <= angle <= bounds[1]:
                raise ValueError(f"joint command maps outside calibrated limit of DXL {motor_id}: {angle:.2f}deg not in {bounds}")
        ticks = [round(self.min_tick + a / self.max_angle * (self.max_tick - self.min_tick))
                 for a in motor_angles]
        self.write_group.clearParam()
        for motor_id, tick in zip(self.ids, ticks):
            tick = max(self.min_tick, min(self.max_tick, tick))
            raw = [self._sdk.DXL_LOBYTE(self._sdk.DXL_LOWORD(tick)),
                   self._sdk.DXL_HIBYTE(self._sdk.DXL_LOWORD(tick)),
                   self._sdk.DXL_LOBYTE(self._sdk.DXL_HIWORD(tick)),
                   self._sdk.DXL_HIBYTE(self._sdk.DXL_HIWORD(tick))]
            if not self.write_group.addParam(motor_id, raw):
                raise RuntimeError(f"Could not register goal for Dynamixel ID {motor_id}")
        result = self.write_group.txPacket()
        self.write_group.clearParam()
        if result != self._comm_success:
            raise RuntimeError(f"Dynamixel goal write failed: {self.packet.getTxRxResult(result)}")

    def close(self):
        if self.port.is_open:
            self.port.closePort()
