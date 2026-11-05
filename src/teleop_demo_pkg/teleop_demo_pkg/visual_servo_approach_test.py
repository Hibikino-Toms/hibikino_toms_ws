#!/usr/bin/env python3
"""One-shot tomato approach test without harvesting or base motion."""

import time

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_services_default

from toms_msg.srv import ArmService, VisionService


class VisualServoApproachTest(Node):
    """Approach one detected tomato and stop at a configurable standoff."""

    def __init__(self):
        super().__init__('visual_servo_approach_test')

        self.declare_parameter('initialize_arm', True)
        self.declare_parameter('use_overview_camera_for_home', True)
        self.declare_parameter('direction', 'f')
        self.declare_parameter('max_iterations', 30)
        self.declare_parameter('miss_limit', 2)
        self.declare_parameter('required_confirmations', 3)
        self.declare_parameter('tolerance_x_mm', 10.0)
        self.declare_parameter('tolerance_y_mm', 15.0)
        self.declare_parameter('tolerance_z_mm', 10.0)
        self.declare_parameter('standoff_y_mm', 100.0)
        self.declare_parameter('settle_sec', 0.2)
        self.declare_parameter('association_gate_mm', 100.0)
        self.declare_parameter('return_home_on_finish', False)
        self.declare_parameter('return_home_on_failure', False)

        self.vision_client = self.create_client(
            VisionService,
            'vision_service',
            qos_profile=qos_profile_services_default)
        self.arm_client = self.create_client(
            ArmService,
            'arm_service',
            qos_profile=qos_profile_services_default)

        self._wait_for_service(self.vision_client, 'Vision')
        self._wait_for_service(self.arm_client, 'Arm')

    def _wait_for_service(self, client, name):
        while rclpy.ok() and not client.wait_for_service(timeout_sec=1.0):
            self.get_logger().info(f'{name}サービスを待っています...')
        if not rclpy.ok():
            raise RuntimeError(f'{name}サービス待機中にROSが終了しました')

    def _call(self, client, request):
        future = client.call_async(request)
        rclpy.spin_until_future_complete(self, future)
        if future.exception() is not None:
            raise RuntimeError(str(future.exception()))
        return future.result()

    def initialize_arm(self):
        request = ArmService.Request()
        request.task = 'init_arm'
        response = self._call(self.arm_client, request)
        return response is not None and response.task_comp

    def detect_overview_target(self):
        request = VisionService.Request()
        request.task = 'detect_check'
        request.direction = str(self.get_parameter('direction').value)
        response = self._call(self.vision_client, request)
        if response is None or not response.detect_check:
            return None
        if not response.target_pos.tomato_data:
            return None
        return response.target_pos.tomato_data[0]

    def move_to_observation_pose(self, target):
        request = ArmService.Request()
        request.task = 'home'
        request.target.x = target.x
        request.target.y = target.y
        request.target.z = target.z
        request.target.approach_direction = target.approach_direction
        response = self._call(self.arm_client, request)
        return response is not None and response.task_comp

    def request_tracking_targets(self):
        request = VisionService.Request()
        request.task = 'track_tomato'
        request.direction = str(self.get_parameter('direction').value)
        response = self._call(self.vision_client, request)
        if response is None or not response.detect_check:
            return []
        return response.target_pos.tomato_data

    def move_visual_step(self, dx, dy, dz, approach_direction):
        request = ArmService.Request()
        request.task = 'visual_servo_step'
        request.target.x = int(round(dx))
        request.target.y = int(round(dy))
        request.target.z = int(round(dz))
        request.target.approach_direction = int(approach_direction)
        response = self._call(self.arm_client, request)
        return response is not None and response.task_comp

    def select_target(self, candidates, previous_target):
        if not candidates:
            return None
        if previous_target is None:
            return candidates[0]

        previous_x, previous_y, previous_z = previous_target[:3]

        def cost(candidate):
            dx = float(candidate.x) - previous_x
            dy = float(candidate.y) - previous_y
            dz = float(candidate.z) - previous_z
            return dx * dx + dz * dz + 0.05 * dy * dy

        selected = min(candidates, key=cost)
        gate = max(1.0, abs(float(
            self.get_parameter('association_gate_mm').value)))
        if cost(selected) > gate * gate:
            return None
        return selected

    def approach(self):
        max_iterations = max(
            1, int(self.get_parameter('max_iterations').value))
        miss_limit = max(1, int(self.get_parameter('miss_limit').value))
        required_confirmations = max(
            1, int(self.get_parameter('required_confirmations').value))
        tolerance_x = abs(float(self.get_parameter('tolerance_x_mm').value))
        tolerance_y = abs(float(self.get_parameter('tolerance_y_mm').value))
        tolerance_z = abs(float(self.get_parameter('tolerance_z_mm').value))
        standoff_y = float(self.get_parameter('standoff_y_mm').value)
        settle_sec = max(0.0, float(self.get_parameter('settle_sec').value))

        previous_target = None
        angle_history = []
        misses = 0
        confirmations = 0

        for iteration in range(1, max_iterations + 1):
            candidates = self.request_tracking_targets()
            target = self.select_target(candidates, previous_target)
            if target is None:
                misses += 1
                self.get_logger().warning(
                    f'ターゲット未検出 ({misses}/{miss_limit})')
                if misses >= miss_limit:
                    return False
                time.sleep(settle_sec)
                continue

            misses = 0
            raw_target = [
                float(target.x),
                float(target.y),
                float(target.z),
                int(target.approach_direction),
            ]
            previous_target = raw_target

            angle_history.append(raw_target[3])
            angle_history = angle_history[-3:]
            approach_direction = max(
                reversed(angle_history), key=angle_history.count)

            error_x = raw_target[0]
            error_y = raw_target[1] - standoff_y
            error_z = raw_target[2]
            self.get_logger().info(
                f'反復 {iteration}/{max_iterations}: '
                f'EE相対誤差=({error_x:.1f}, {error_y:.1f}, '
                f'{error_z:.1f}) mm, 進入角度={approach_direction} deg')

            in_tolerance = (
                abs(error_x) <= tolerance_x
                and abs(error_y) <= tolerance_y
                and abs(error_z) <= tolerance_z)
            if in_tolerance:
                if confirmations >= required_confirmations:
                    self.get_logger().info(
                        f'接近テスト完了: トマト中心の約{standoff_y:.1f} mm手前で停止')
                    return True

                # Position is held while the wrist finishes following the latest
                # peduncle-derived approach angle.
                if not self.move_visual_step(
                        0.0, 0.0, 0.0, approach_direction):
                    self.get_logger().error('進入角度の追従に失敗しました')
                    return False
                confirmations += 1
                time.sleep(settle_sec)
                continue

            confirmations = 0
            if not self.move_visual_step(
                    error_x, error_y, error_z, approach_direction):
                self.get_logger().error('アームの短距離移動に失敗しました')
                return False
            time.sleep(settle_sec)

        self.get_logger().error(
            f'{max_iterations}回以内に収束しませんでした')
        return False

    def run_test(self):
        self.get_logger().warning(
            '接近テスト専用です。吸引・顎・噛み切り・走行は実行しません。')

        if bool(self.get_parameter('initialize_arm').value):
            self.get_logger().info('アームを初期化します')
            if not self.initialize_arm():
                self.get_logger().error('アーム初期化に失敗しました')
                return False

        if bool(self.get_parameter('use_overview_camera_for_home').value):
            self.get_logger().info('俯瞰カメラでトマトを探索します')
            overview_target = self.detect_overview_target()
            if overview_target is None:
                self.get_logger().error('俯瞰カメラでトマトを検出できませんでした')
                return False
            if not self.move_to_observation_pose(overview_target):
                self.get_logger().error('手先カメラの認識位置へ移動できませんでした')
                return False

        succeeded = self.approach()
        return_home = bool(self.get_parameter(
            'return_home_on_finish' if succeeded else
            'return_home_on_failure').value)
        if return_home:
            self.get_logger().info('テスト終了後にアームを初期位置へ戻します')
            self.initialize_arm()
        return succeeded


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = VisualServoApproachTest()
        succeeded = node.run_test()
        if succeeded:
            node.get_logger().info('Visual servo approach test: SUCCESS')
        else:
            node.get_logger().error('Visual servo approach test: FAILED')
    except KeyboardInterrupt:
        if node is not None:
            node.get_logger().warning('接近テストを中断しました')
    except Exception as error:
        if node is not None:
            node.get_logger().error(f'接近テスト中の例外: {error}')
        else:
            print(f'接近テストノードの起動に失敗しました: {error}')
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
