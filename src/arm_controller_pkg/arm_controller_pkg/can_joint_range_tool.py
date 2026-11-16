"""Read and cautiously jog one CAN-mixed arm joint at a time.

Read-only mode is the default. Motion requires ``--enable-motion`` and an
interactive ``MOVE`` confirmation. q1/q2 are RMD X8/X6 through the Arduino
bridge; q3 is Dynamixel ID 5.
"""
from __future__ import annotations

import argparse
import math
import sys
import time

from ament_index_python.packages import get_package_share_directory

from .modules.can_mixed_backend import (
    CanMixedMotorBackend,
    _DynamixelQ3,
    _RmdSerialBridge,
)


JOINTS = {"q1": 0, "q2": 1, "q3": 2}


def _usb_inventory():
    from serial.tools import list_ports

    return [(p.device, p.serial_number, p.location) for p in list_ports.comports()]


def _check_usb_devices(config):
    """Check both adapters before opening Uno (which resets its firmware)."""
    ports = _usb_inventory()
    missing = []
    for name, serial_number in (
            ("Arduino", str(config["can_mixed_backend"]["arduino_serial_number"])),
            ("U2D2", str(config["dxl_params"]["U2D2_SERIAL_NUMBER"]))):
        matches = [p for p in ports if p[1] == serial_number]
        if len(matches) != 1:
            missing.append(f"{name} serial={serial_number!r}: found {len(matches)} devices")
        else:
            print(f"USB preflight: {name}={matches[0][0]}, serial={serial_number}, "
                  f"location={matches[0][2]}", flush=True)
    if missing:
        raise RuntimeError(
            "; ".join(missing) + f"; detected ports={ports!r}. "
            "No adapter was opened. Check the USB connection and kernel disconnect logs "
            "(journalctl -k --since '-5 minutes').")


def _load_config(path):
    import yaml

    with open(path, encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    if not isinstance(config, dict):
        raise ValueError("config_file must contain a YAML mapping")
    return config


def _limits(config):
    values = config.get("joint_limits_deg")
    if not isinstance(values, list) or len(values) != 3:
        raise ValueError("joint_limits_deg must contain limits for q1, q2, and q3")
    result = []
    for name, row in zip(JOINTS, values):
        if (not isinstance(row, (list, tuple)) or len(row) != 2 or
                not all(math.isfinite(float(v)) for v in row) or float(row[0]) >= float(row[1])):
            raise ValueError(f"invalid joint_limits_deg entry for {name}: {row!r}")
        result.append((math.radians(float(row[0])), math.radians(float(row[1]))))
    return result


def _format_state(config, state, q3_adapter):
    can_cfg = config["can_mixed_backend"]
    lines = [
        f"RMD X8 ID0: raw={state['x8_position_cdeg'] / 100.0:.2f}deg, "
        f"speed={state['x8_speed_dps']}dps, voltage={state['x8_voltage_10v'] / 10.0:.1f}V, "
        f"errors=0x{state['x8_errors']:04x}",
        f"RMD X6 ID1: raw={state['x6_position_cdeg'] / 100.0:.2f}deg, "
        f"speed={state['x6_speed_dps']}dps, voltage={state['x6_voltage_10v'] / 10.0:.1f}V, "
        f"errors=0x{state['x6_errors']:04x}, bridge_armed={state['armed']}",
    ]
    calibration_valid = bool(can_cfg.get("calibration_valid", False))
    calibration = {
        name: CanMixedMotorBackend._calibration_axis(can_cfg, name)
        for name in ("q1", "q2")
    }
    for name, raw_key in (("q1", "x8_position_cdeg"), ("q2", "x6_position_cdeg")):
        axis = calibration[name]
        if axis is None:
            lines.append(f"{name}: joint angle unavailable (calibration reference missing)")
            continue
        angle = math.radians((state[raw_key] - axis["zero_cdeg"]) /
                             (100.0 * axis["direction"]))
        tag = "configured" if calibration_valid else "UNCALIBRATED estimate"
        lines.append(f"{name}: {math.degrees(angle):+.2f}deg ({tag}, "
                     f"trim={axis['angle_trim_deg']:+.2f}deg)")

    p = q3_adapter.params
    tick = q3_adapter._read(int(p["ADDR_PRESENT_POSITION"]), 4)
    q3 = math.degrees(q3_adapter.joint_from_tick(tick))
    lines.append(f"q3 (Dynamixel ID {q3_adapter.motor_id}): {q3:+.2f}deg, "
                 f"raw_tick={tick}, trim={q3_adapter.angle_trim_deg:+.2f}deg")
    lines.append(f"Dynamixel torque={q3_adapter._read(int(p['ADDR_TORQUE_ENABLE']), 1)} (reported state)")
    return "\n".join(lines)


def _read_only(config):
    bridge = None
    q3 = None
    try:
        can = config["can_mixed_backend"]
        dxl_params = config["dxl_params"]
        bridge = _RmdSerialBridge(
            str(can["arduino_serial_number"]),
            int(can.get("baudrate", 115200)),
            float(can.get("communication_timeout_sec", 0.8)),
        )
        q3 = _DynamixelQ3(dxl_params, angle_trim_deg=can.get("q3", {}).get("angle_trim_deg", 0.0))
        while True:
            state = bridge.read()
            print("\n" + _format_state(config, state, q3), flush=True)
            command = input("[read-only] Enter=refresh, q=quit: ").strip().lower()
            if command == "q":
                break
            if command:
                print("Read-only mode accepts only Enter or q.")
    finally:
        if bridge is not None:
            bridge.close()
        if q3 is not None:
            q3.close()


def _show_active(config, backend, joints):
    state = backend.last_state
    print("\n" + _format_state(config, state, backend.q3), flush=True)
    print("Measured joint angles: " + ", ".join(
        f"{name}={math.degrees(joints[index]):+.2f}deg" for name, index in JOINTS.items()),
        flush=True)


def _jog(backend, limits, joint, sign, step_deg, tolerance_deg, timeout_sec):
    index = JOINTS[joint]
    measured = backend.read_joints()
    target = list(measured)
    target[index] += math.radians(step_deg * sign)
    low, high = limits[index]
    if target[index] < low or target[index] > high:
        raise ValueError(
            f"{joint} jog would cross configured software limit "
            f"[{math.degrees(low):.2f}, {math.degrees(high):.2f}]deg; no command sent")

    backend.send_joints(target)
    print(f"Sent {joint} target={math.degrees(target[index]):+.2f}deg; "
          "other joints are commanded to their measured angles.", flush=True)
    deadline = time.monotonic() + timeout_sec
    stable = 0
    last_report = 0.0
    while time.monotonic() < deadline:
        time.sleep(0.1)
        measured = backend.read_joints()
        error_deg = abs(math.degrees(target[index] - measured[index]))
        stable = stable + 1 if error_deg <= tolerance_deg else 0
        now = time.monotonic()
        if now - last_report >= 1.0:
            print(f"  {joint} measured={math.degrees(measured[index]):+.2f}deg, "
                  f"error={error_deg:.2f}deg", flush=True)
            last_report = now
        if stable >= 3:
            print(f"Reached within {tolerance_deg:.2f}deg: "
                  f"{joint}={math.degrees(measured[index]):+.2f}deg", flush=True)
            return measured
    backend._safe_stop()
    raise TimeoutError(
        f"{joint} did not reach the small jog target within {timeout_sec:.1f}s; "
        "all motion commands stopped. Inspect the mechanism and communication before restarting.")


def _motion_mode(config, args, limits):
    if not bool(config.get("can_mixed_backend", {}).get("calibration_valid", False)):
        raise RuntimeError("CAN calibration_valid is false; motion is disabled until q1/q2 are calibrated")
    answer = input(
        "This will arm RMD q1/q2 and enable Dynamixel q3 torque. "
        "Confirm q1/q2 zero and direction are verified on the assembled arm, "
        "the arm is supported, the area is clear, and other arm nodes are stopped. "
        "Type MOVE to continue: ").strip()
    if answer != "MOVE":
        print("Cancelled; no motion backend was activated.")
        return

    backend = CanMixedMotorBackend(
        config["can_mixed_backend"], config["dxl_params"], limits)
    backend.max_speed_dps = int(args.speed_dps)
    try:
        report = backend.activate()
        print(f"Motion enabled: {report}; RMD command speed={backend.max_speed_dps}dps", flush=True)
        print("q3 uses the existing Dynamixel profile from xy_robot_config.yaml; "
              "--speed-dps changes only the CAN q1/q2 speed.", flush=True)
        current = backend.read_joints()
        _show_active(config, backend, current)
        step_deg = args.step_deg
        print("Commands: j <q1|q2|q3> <+|->, step <degrees>, r, limits, q")
        while True:
            text = input("range> ").strip().lower().split()
            if not text:
                continue
            if text[0] in ("q", "quit", "exit"):
                break
            if text[0] == "r" and len(text) == 1:
                current = backend.read_joints()
                _show_active(config, backend, current)
                continue
            if text[0] == "limits" and len(text) == 1:
                print("Configured software limits: " + ", ".join(
                    f"{name}=[{math.degrees(limits[index][0]):.1f},"
                    f"{math.degrees(limits[index][1]):.1f}]deg"
                    for name, index in JOINTS.items()), flush=True)
                continue
            if text[0] == "step" and len(text) == 2:
                value = float(text[1])
                if not math.isfinite(value) or not 0.1 <= value <= 5.0:
                    print("Step must be between 0.1 and 5 degrees.")
                else:
                    step_deg = value
                    print(f"Jog step set to {step_deg:g}deg")
                continue
            if text[0] == "j" and len(text) == 3:
                joint, direction = text[1], text[2]
                if joint not in JOINTS or direction not in ("+", "-"):
                    print("Usage: j <q1|q2|q3> <+|->")
                    continue
                current = _jog(backend, limits, joint, 1 if direction == "+" else -1,
                               step_deg, args.arrival_tolerance_deg, args.move_timeout_sec)
                _show_active(config, backend, current)
                continue
            print("Unknown command. Use j <q1|q2|q3> <+|->, step <degrees>, r, limits, q.")
    finally:
        try:
            backend._safe_stop()
        finally:
            backend.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-file", default=None,
                        help="robot YAML (defaults to the installed arm_controller_pkg config)")
    parser.add_argument("--enable-motion", action="store_true",
                        help="enable one-axis jog commands; read-only is the default")
    parser.add_argument("--step-deg", type=float, default=0.5,
                        help="initial manual jog size in degrees (0.1..5.0)")
    parser.add_argument("--speed-dps", type=int, default=2,
                        help="RMD speed for q1/q2 jogs (1..10 deg/s)")
    parser.add_argument("--arrival-tolerance-deg", type=float, default=0.3)
    parser.add_argument("--move-timeout-sec", type=float, default=12.0)
    args = parser.parse_args(argv)
    if not 0.1 <= args.step_deg <= 5.0:
        parser.error("--step-deg must be between 0.1 and 5.0")
    if not 1 <= args.speed_dps <= 10:
        parser.error("--speed-dps must be between 1 and 10")
    if (not math.isfinite(args.arrival_tolerance_deg) or args.arrival_tolerance_deg <= 0 or
            not math.isfinite(args.move_timeout_sec) or args.move_timeout_sec <= 0):
        parser.error("arrival tolerance and move timeout must be positive and finite")

    config_path = args.config_file or (
        get_package_share_directory("arm_controller_pkg") + "/config/xy_robot_config.yaml")
    config = _load_config(config_path)
    if not all(name in config for name in ("can_mixed_backend", "dxl_params")):
        parser.error("config_file must define can_mixed_backend and dxl_params")
    limits = _limits(config)
    print(f"Config: {config_path}")
    print("Configured software limits: " + ", ".join(
        f"{name}=[{math.degrees(limits[index][0]):.1f},"
        f"{math.degrees(limits[index][1]):.1f}]deg"
        for name, index in JOINTS.items()))
    print("No mechanical limits are inferred. Read-only mode does not arm the RMD bridge "
          "or enable Dynamixel torque.")
    try:
        _check_usb_devices(config)
        if args.enable_motion:
            _motion_mode(config, args, limits)
        else:
            _read_only(config)
    except (KeyboardInterrupt, EOFError):
        print("\nInterrupted; closing communication and requesting the configured stop/hold behavior.")
    except Exception as exc:  # Keep diagnostic tools friendly for serial/runtime errors.
        print(f"ERROR: {exc}", file=sys.stderr)
        print(f"USB ports after failure: {_usb_inventory()!r}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
