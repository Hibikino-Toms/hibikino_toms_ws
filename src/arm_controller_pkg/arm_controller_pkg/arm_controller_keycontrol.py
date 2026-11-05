import os
import select
import sys
import termios
import time
import tty

import rclpy
import serial
import yaml
from rclpy.node import Node
from std_msgs.msg import String

from .modules.angle_converter import AngleConverter
from .modules.ik_solver_arm2 import InverseKinematicsSolver
from .modules.motor_controller_module_5motor import MotorController
from .modules.z_axis_controller_module import ZAxis

PARAMS_PATH = '/home/ylab/hibikino_toms_ws/module/set_params.yaml'
Z_TAP_MM = 20


class ArmControllerKeycontrol(Node):
    """Cartesian hold-to-move arm keyboard node and shared key event source."""

    def __init__(self):
        super().__init__('arm_controller_keycontrol')
        self.keyboard_stream = sys.stdin
        self.owns_keyboard_stream = False
        self.terminal_settings = None
        if not self.keyboard_stream.isatty():
            try:
                self.keyboard_stream = open('/dev/tty', 'rb', buffering=0)
                self.owns_keyboard_stream = True
            except OSError as error:
                raise RuntimeError(
                    'キー操作には対話型ターミナルが必要です。端末から起動してください。'
                ) from error
        with open(PARAMS_PATH, 'r', encoding='utf-8') as stream:
            params = yaml.safe_load(stream)

        self.declare_parameter('keyboard_topic', '/teleop/keyboard_key')
        self.declare_parameter('speed_mm_s', 30.0)
        self.keyboard_topic = str(self.get_parameter('keyboard_topic').value)
        self.speed_mm_s = float(self.get_parameter('speed_mm_s').value)
        if self.speed_mm_s <= 0:
            raise ValueError('speed_mm_s は正の値にしてください。')

        self.motor = MotorController(params['dxl_params'])
        self.solver = InverseKinematicsSolver(params['ik_solver_params'])
        self.angle_converter = AngleConverter(params['dxl_params'])
        # Bypass ZAxis.__init__: its legacy power-off/on cycle can drop the axis.
        z_params = params['ZAxis_params']
        self.z_axis = ZAxis.__new__(ZAxis)
        z_device = self.z_axis.select_device(z_params['Z_PICO_SERIAL_NUMBER'])
        if z_device is None:
            raise RuntimeError('Z軸Picoが接続されていません。')
        self.z_axis.BACK_CAM_HEIGHT = z_params['BACK_CAM_HEIGHT']
        self.z_axis.serial_timeout = float(z_params.get('SERIAL_TIMEOUT_SEC', 5.0))
        self.z_axis.move_timeout = float(z_params.get('MOVE_TIMEOUT_SEC', 45.0))
        if self.z_axis.serial_timeout <= 0 or self.z_axis.move_timeout <= 0:
            raise ValueError('Z軸のタイムアウトは正の値にしてください。')
        self.z_axis.ser = serial.Serial(
            z_device, z_params['BAUDRATE'], timeout=self.z_axis.serial_timeout,
            write_timeout=self.z_axis.serial_timeout)
        # Discard the firmware's setup-time `0 0` response to keep replies aligned.
        time.sleep(0.1)
        self.z_axis.ser.reset_input_buffer()
        # Pico firmware starts with pre_pos=-1; mode 3 ignores moves until
        # mode 2 homes the limit switch and initializes pre_pos.
        print('Z軸をリミットスイッチへ移動して原点復帰します...', flush=True)
        z_state = self.z_axis.init_pos()
        if z_state[0] != 2 or not 0 <= z_state[1] <= 450:
            raise RuntimeError(f'Z軸の原点復帰応答が不正です: {z_state!r}')
        self.position = [0.0, 0.0, float(z_state[1])]
        if not 0.0 <= self.position[2] <= 450.0:
            raise RuntimeError(f'Z軸の現在位置が範囲外です: {self.position[2]} mm')

        self.current_key = None
        self.last_update_time = time.monotonic()
        self.exit_requested = False
        self.keyboard_pub = self.create_publisher(String, self.keyboard_topic, 10)
        self._capture_starting_pose()

        self.terminal_settings = termios.tcgetattr(self.keyboard_stream.fileno())
        tty.setcbreak(self.keyboard_stream.fileno())
        self.timer = self.create_timer(0.02, self._poll_keyboard_and_move)
        print('アーム: i/k=X±, j/l=Y±で動作開始、u/o=Z±20mm/タップ、Spaceで停止 (XY指令速度 約30 mm/s)', flush=True)
        print('エンドエフェクタ: 1〜4=選択, w/s=正転/逆転, Space=停止, q=終了', flush=True)

    def _capture_starting_pose(self):
        positions = self.motor.read_positions()
        if len(positions) < 5:
            raise RuntimeError(f'アーム現在位置を取得できません: {positions!r}')
        degrees = [self.motor.position_to_angle(value) for value in positions]
        self.ik_angles = self.angle_converter.dxl_ang2ik_ang(
            [degrees[0], degrees[2], degrees[4]])
        x, y, self.approach_angle = self.solver.forward_kinematics(*self.ik_angles)
        self.position[0:2] = [x, y]
        self.get_logger().info(
            f'起動時姿勢を保持: x={x:.1f}, y={y:.1f}, z={self.position[2]:.1f} mm')

    def _poll_keyboard_and_move(self):
        try:
            ready, _, _ = select.select([self.keyboard_stream], [], [], 0)
            if ready:
                key = os.read(self.keyboard_stream.fileno(), 1).decode('ascii', errors='ignore')
                if key:
                    self._handle_key(key)
            if self.exit_requested:
                return

            now = time.monotonic()
            dt = min(max(now - self.last_update_time, 0.0), 0.1)
            self.last_update_time = now
            self._move_for_key(dt)
        except Exception as error:
            self.get_logger().error(f'キー操作エラー: {error}')
            self.exit_requested = True

    def _handle_key(self, key):
        key = key.lower()
        self.keyboard_pub.publish(String(data=key))
        if key == 'q':
            self.exit_requested = True
        elif key in ('u', 'o'):
            self.current_key = None
            self._move_z_once(1 if key == 'u' else -1)
        elif key in ('i', 'k', 'j', 'l'):
            self.current_key = key
            self.last_update_time = time.monotonic()
        elif key in (' ', '\x1b'):
            self.current_key = None

    def _move_for_key(self, dt):
        if self.current_key is None or dt <= 0:
            return
        next_position = list(self.position)
        delta = self.speed_mm_s * dt
        axis, sign = {
            'i': (0, 1), 'k': (0, -1), 'j': (1, 1),
            'l': (1, -1),
        }[self.current_key]
        next_position[axis] += sign * delta
        next_position[0] = max(-40.0, min(250.0, next_position[0]))
        next_position[1] = max(0.0, min(500.0, next_position[1]))
        next_position[2] = max(0.0, min(450.0, next_position[2]))

        if next_position[:2] != self.position[:2]:
            target = [next_position[0], next_position[1], self.approach_angle]
            current = [self.position[0], self.position[1], self.approach_angle]
            motor_positions = self.motor.read_positions()
            degrees = [self.motor.position_to_angle(value) for value in motor_positions]
            current_ik = self.angle_converter.dxl_ang2ik_ang(
                [degrees[0], degrees[2], degrees[4]])
            _, target_ik, solved = self.solver.solve_ik(current, target, current_ik)
            if not solved:
                self.get_logger().warning('目標位置の逆運動学解がありません。')
                self.current_key = None
                return
            target_motor, in_limits = self.angle_converter.ik_ang2dxl_ang(target_ik)
            if not in_limits:
                self.get_logger().warning('モーター可動範囲に達しました。')
                self.current_key = None
                return
            if not self.motor.move_motors(target_motor, task='target'):
                self.get_logger().warning('アーム移動が完了しませんでした。')
                self.current_key = None
                return

        self.position = next_position

    def _move_z_once(self, direction):
        current_z = int(round(self.position[2]))
        target_z = max(0, min(450, current_z + direction * Z_TAP_MM))
        if target_z == current_z:
            self.get_logger().info(f'Z軸は可動範囲の端です: {current_z} mm')
            return

        # The Pico enables its driver when mode 3 arrives.
        response = self.z_axis.data2pico(
            f'3,{target_z}\n', self.z_axis.move_timeout)
        if response != [3, target_z]:
            raise RuntimeError(f'Z軸移動応答が不正です: {response!r}')
        self.position[2] = float(response[1])
        self.get_logger().info(f'Z軸: {current_z} → {response[1]} mm')

    def destroy_node(self):
        try:
            if self.terminal_settings is not None:
                termios.tcsetattr(
                    self.keyboard_stream.fileno(), termios.TCSADRAIN, self.terminal_settings)
        except (termios.error, OSError) as error:
            self.get_logger().warning(f'端末設定を復元できませんでした: {error}')
        finally:
            if self.owns_keyboard_stream:
                self.keyboard_stream.close()
        if hasattr(self, 'z_axis') and self.z_axis.ser.is_open:
            self.z_axis.ser.close()
        if hasattr(self, 'motor'):
            self.motor.close(dis_torque=False)
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = ArmControllerKeycontrol()
        while rclpy.ok() and not node.exit_requested:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    except Exception as error:
        print(f'arm_controller_keycontrol 起動失敗: {error}', file=sys.stderr, flush=True)
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
