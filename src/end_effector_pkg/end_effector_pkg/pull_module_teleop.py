import os
import json
import math
import time
import select
import sys
import termios
import tty

import rclpy
import serial
import serial.tools.list_ports
import yaml
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from std_msgs.msg import Bool, String
from std_srvs.srv import Trigger


PARAMS_PATH = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'


class PullModuleTeleop(Node):
    """Keyboard teleoperation and sensor display for the pull EE Pico."""

    def __init__(self):
        super().__init__('pull_module_teleop')
        with open(PARAMS_PATH, 'r', encoding='utf-8') as params_file:
            params = yaml.safe_load(params_file)
        ee_params = params['EE_params']

        self.declare_parameter('serial_number', ee_params['EE_PICO_SERIAL_NUMBER'])
        self.declare_parameter('baudrate', ee_params.get('BAUDRATE', 115200))
        self.declare_parameter('motor_pwm', 180)
        self.declare_parameter('servo_pwm', 180)
        self.declare_parameter('harvest_link_enabled', False)
        self.declare_parameter('simulate_hardware', False)
        self.declare_parameter('keyboard_enabled', True)
        self.harvest_link = bool(self.get_parameter('harvest_link_enabled').value)
        self.simulate_hardware = bool(self.get_parameter('simulate_hardware').value)
        self.keyboard_enabled = bool(self.get_parameter('keyboard_enabled').value)
        self.harvest_status = None
        self.request_future = None
        self.request_started = 0.
        self.last_alive = 0.
        self.last_motor_heartbeat = 0.
        self.ee_running = False
        self.sent_commands = []
        self.alive_pub = self.create_publisher(Bool, '/arm_xy/harvest/ee_alive', 1)
        self.harvest_clients = {action: self.create_client(Trigger, '/arm_xy/harvest/'+action)
                                for action in ('hold', 'pull', 'resume')}
        self.harvest_sub = self.create_subscription(String, '/arm_xy/harvest/state',
            self._harvest_state, QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                                           reliability=ReliabilityPolicy.RELIABLE))
        serial_number = str(self.get_parameter('serial_number').value)
        baudrate = int(self.get_parameter('baudrate').value)
        self.motor_pwm = max(1, min(255, int(self.get_parameter('motor_pwm').value)))
        self.servo_pwm = max(1, min(255, int(self.get_parameter('servo_pwm').value)))

        self.serial_port = None
        device = 'SIMULATED EE (no USB)'
        if not self.simulate_hardware:
            device = self._find_device(serial_number)
            if device is None:
                raise RuntimeError(f'EE Pico (serial={serial_number}) が見つかりません。')
            self.serial_port = serial.Serial(device, baudrate, timeout=0.02, write_timeout=0.5)
            self.serial_port.reset_input_buffer()
        self.receive_buffer = bytearray()
        self.selected_motor = 1
        self.exit_requested = False
        self.keyboard_stream = sys.stdin
        self.owns_keyboard_stream = False
        self.terminal_settings = None

        if self.keyboard_enabled and not self.keyboard_stream.isatty():
            try:
                self.keyboard_stream = open('/dev/tty', 'rb', buffering=0)
                self.owns_keyboard_stream = True
            except OSError as error:
                if self.serial_port is not None:
                    self.serial_port.close()
                raise RuntimeError(
                    'キー操作には対話型ターミナルが必要です。'
                ) from error

        if self.keyboard_enabled and not self.keyboard_stream.isatty():
            if self.serial_port is not None:
                self.serial_port.close()
            raise RuntimeError('キー操作には対話型ターミナルが必要です。')

        self.terminal_settings = None
        if self.keyboard_enabled:
            self.terminal_settings = termios.tcgetattr(self.keyboard_stream.fileno())
            tty.setcbreak(self.keyboard_stream.fileno())
        self._print_controls(device)
        self.timer = self.create_timer(0.02, self._poll_io)

    @staticmethod
    def _find_device(serial_number):
        for port in serial.tools.list_ports.comports():
            if port.serial_number == serial_number:
                return port.device
        return None

    def _print_controls(self, device):
        print(f'EE Pico接続: {device}', flush=True)
        print('操作: 1〜4=モーター選択, w=正転, s=逆転, Space=全停止, q=終了', flush=True)
        if self.harvest_link:
            print('収穫: h=アーム保持, r=引き戻し→初期姿勢, n=次の接近。Space/qはEE停止＋アーム保持', flush=True)
            print('w/s: アーム状態に関係なくEEを操作します。', flush=True)
        print(f'PWM: DCモーター={self.motor_pwm}, サーボ(M3)={self.servo_pwm} / 255', flush=True)
        print('センサー値を200ms間隔で表示します。', flush=True)

    def _selected_pwm(self):
        # With the current Pico firmware, physical M3 is the hook servo.
        return self.servo_pwm if self.selected_motor == 3 else self.motor_pwm

    def _send(self, command):
        if self.serial_port is not None:
            self.serial_port.write((command + '\n').encode('ascii'))
            self.serial_port.flush()
        if command != 'KEEPALIVE':
            self.ee_running = command != 'STOP'
        self.sent_commands.append(command)
        self.sent_commands = self.sent_commands[-100:]

    def _mode(self):
        if self.harvest_status is None:
            return 'UNAVAILABLE'
        mode, seen, stamp = self.harvest_status
        if time.monotonic()-seen > .7 or abs(self.get_clock().now().nanoseconds/1e9-stamp) > .7:
            return 'UNAVAILABLE'
        return mode

    def _harvest_state(self, msg):
        try:
            data = json.loads(msg.data)
            mode, stamp = str(data['state']), float(data['stamp'])
            if mode not in ('STARTUP', 'APPROACH', 'HARVEST_HOLD', 'RETURNING', 'RETURNED', 'FAULT', 'DISABLED'):
                return
            if self.harvest_status is not None and stamp <= self.harvest_status[2]:
                return
            if not math.isfinite(stamp) or abs(self.get_clock().now().nanoseconds/1e9-stamp) > .7:
                return
            previous = self._mode()
            self.harvest_status = (mode, time.monotonic(), stamp)
            if self.harvest_link and previous != mode:
                self.get_logger().info(f'収穫モード: {mode} ({data.get("reason", "")})')
        except (ValueError, KeyError, TypeError):
            return

    def _request_action(self, action):
        if not self.harvest_link:
            self.get_logger().warning('harvest_link_enabled is false')
            return False
        if self._mode() in ('UNAVAILABLE', 'DISABLED', 'STARTUP', 'FAULT'):
            self.get_logger().warning('アームの収穫制御が利用できません')
            return False
        if self.request_future is not None and not self.request_future.done():
            if action != 'hold':
                self.get_logger().warning('前の要求の応答待ちです')
                return False
            self.request_future.cancel()
        client = self.harvest_clients[action]
        if not client.service_is_ready():
            self.get_logger().warning(f'収穫サービス待ち: {action}')
            return False
        self.request_started = time.monotonic()
        self.request_future = client.call_async(Trigger.Request())
        self.request_future.add_done_callback(self._action_result)
        return True

    def _action_result(self, future):
        if future is not self.request_future or future.cancelled():
            return
        try:
            result = future.result()
            if not result.success:
                self.get_logger().warning(result.message)
        except Exception as exc:
            self.get_logger().error(f'収穫要求失敗: {exc}')

    def _move_ee(self, command):
        # EE motors remain independently operable throughout arm startup,
        # approach, hold, return, and fault states. Arm coordination keys
        # (h/r/n) are separate explicit actions.
        self._send(command)

    def _handle_key(self, key):
        if key in '1234':
            self.selected_motor = int(key)
            print(f'選択: モーター{self.selected_motor}', flush=True)
        elif key == 'w':
            pwm = self._selected_pwm()
            self._move_ee(f'M{self.selected_motor},{pwm}')
            print(f'モーター{self.selected_motor}: 正転 PWM={pwm}', flush=True)
        elif key == 's':
            pwm = self._selected_pwm()
            self._move_ee(f'M{self.selected_motor},{-pwm}')
            print(f'モーター{self.selected_motor}: 逆転 PWM={pwm}', flush=True)
        elif key.lower() in ('h', 'r', 'n'):
            self._send('STOP')
            self._request_action({'h': 'hold', 'r': 'pull', 'n': 'resume'}[key.lower()])
        elif key == ' ':
            self._send('STOP')
            if self.harvest_link:
                self._request_action('hold')
            print('全モーター停止', flush=True)
        elif key.lower() == 'q':
            self._send('STOP')
            if self.harvest_link:
                self.alive_pub.publish(Bool(data=False))
                self._request_action('hold')
            self.exit_requested = True

    def _poll_io(self):
        try:
            if self.harvest_link and time.monotonic()-self.last_alive >= .2:
                self.alive_pub.publish(Bool(data=not self.exit_requested))
                self.last_alive = time.monotonic()
            if self.ee_running and time.monotonic()-self.last_motor_heartbeat >= .2:
                self._send('KEEPALIVE')
                self.last_motor_heartbeat = time.monotonic()
            if self.request_future is not None and not self.request_future.done() and time.monotonic()-self.request_started > 2.:
                self.request_future.cancel()
                self.get_logger().error('収穫要求がタイムアウトしました。モードを確認してください')
            ready = []
            if self.keyboard_enabled:
                ready, _, _ = select.select([self.keyboard_stream], [], [], 0)
            if ready:
                key = os.read(
                    self.keyboard_stream.fileno(), 1).decode('ascii', errors='ignore')
                if key:
                    self._handle_key(key)

            if self.exit_requested:
                return

            if self.serial_port is None:
                return
            available = self.serial_port.in_waiting
            if available:
                self.receive_buffer.extend(self.serial_port.read(min(available, 4096)))
            while b'\n' in self.receive_buffer:
                raw_line, _, remaining = self.receive_buffer.partition(b'\n')
                self.receive_buffer = bytearray(remaining)
                line = raw_line.decode('utf-8', errors='replace').strip()
                # Opening USB serial can start in the middle of a status line.
                if line.startswith('[STATUS] '):
                    print(line, flush=True)
            if len(self.receive_buffer) > 8192:
                self.receive_buffer.clear()
        except (serial.SerialException, OSError) as error:
            self.get_logger().error(f'シリアル通信エラー: {error}')
            self._send_stop_safely()
            self.exit_requested = True

    def _send_stop_safely(self):
        if self.serial_port is not None and self.serial_port.is_open:
            try:
                self._send('STOP')
            except serial.SerialException:
                pass

    def destroy_node(self):
        if self.harvest_link and rclpy.ok():
            self.alive_pub.publish(Bool(data=False))
        self._send_stop_safely()
        if self.terminal_settings is not None:
            try:
                termios.tcsetattr(
                    self.keyboard_stream.fileno(), termios.TCSADRAIN,
                    self.terminal_settings)
            except (termios.error, OSError) as error:
                self.get_logger().warning(f'端末設定を復元できませんでした: {error}')
        if self.owns_keyboard_stream:
            self.keyboard_stream.close()
        if self.serial_port is not None and self.serial_port.is_open:
            self.serial_port.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = PullModuleTeleop()
        # Shut down outside the timer callback so q cannot block the executor.
        while rclpy.ok() and not node.exit_requested:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
