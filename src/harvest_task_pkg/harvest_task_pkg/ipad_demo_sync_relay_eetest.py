"""iPad harvest relay bridged to the existing automatic EE coordinator."""
import json
import math
import threading
import time

import rclpy
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from std_msgs.msg import Bool, String
from std_srvs.srv import Trigger

from harvest_task_pkg.ipad_demo_sync_relay import (
    GatewayError,
    HarvestGatewayNode,
)


class HarvestGatewayEETestNode(HarvestGatewayNode):
    """Bridge the hand-target relay to the unchanged auto_harvest node."""

    def __init__(self):
        super().__init__()
        self.declare_parameter('ee_cycle_timeout_sec', 180.0)
        self._ee_cycle_timeout = float(
            self.get_parameter('ee_cycle_timeout_sec').value)
        if not math.isfinite(self._ee_cycle_timeout) or self._ee_cycle_timeout <= 0:
            raise ValueError('ee_cycle_timeout_sec must be finite and positive')

        self._ee_condition = threading.Condition()
        self._ee_state = None
        self._ee_reason = ''
        self._ee_ready = False
        self._arm_state = 'STARTUP'
        self._arm_reason = 'relay_startup'
        self._arm_hold_ready = False
        self._arm_sequence = 0
        self._pull_requested = threading.Event()

        self._bridge_group = ReentrantCallbackGroup()
        self._ee_state_sub = self.create_subscription(
            String, '/end_effector/auto/state', self._ee_state_callback, 10,
            callback_group=self._bridge_group)
        self._ee_ready_sub = self.create_subscription(
            Bool, '/end_effector/ready', self._ee_ready_callback, QoSProfile(
                depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                reliability=ReliabilityPolicy.RELIABLE),
            callback_group=self._bridge_group)
        self._arm_state_pub = self.create_publisher(
            String, '/arm_xy/harvest/state', QoSProfile(
                depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                reliability=ReliabilityPolicy.RELIABLE))
        self._ee_key_pub = self.create_publisher(
            String, '/end_effector/auto/key', 10)
        self._hold_srv = self.create_service(
            Trigger, '/arm_xy/harvest/hold', self._hold_callback,
            callback_group=self._bridge_group)
        self._pull_srv = self.create_service(
            Trigger, '/arm_xy/harvest/pull', self._pull_callback,
            callback_group=self._bridge_group)
        self._resume_srv = self.create_service(
            Trigger, '/arm_xy/harvest/resume', self._resume_callback,
            callback_group=self._bridge_group)
        self._arm_state_timer = self.create_timer(.1, self._publish_arm_state)
        self.get_logger().info(
            'EE test relay bridge ready; waiting for auto_harvest initialization.')

    def _ee_state_callback(self, msg):
        try:
            data = json.loads(msg.data)
            state = str(data['state'])
            reason = str(data.get('reason', ''))
        except (ValueError, KeyError, TypeError):
            return
        with self._ee_condition:
            self._ee_state = state
            self._ee_reason = reason
            self._ee_condition.notify_all()

    def _ee_ready_callback(self, msg):
        self._ee_ready = bool(msg.data)
        with self._ee_condition:
            self._ee_condition.notify_all()

    def _set_arm_state(self, state, reason, hold_ready=False):
        with self._ee_condition:
            self._arm_state = state
            self._arm_reason = reason
            self._arm_hold_ready = bool(hold_ready)
            self._arm_sequence += 1
            self._ee_condition.notify_all()
        self._publish_arm_state()

    def _publish_arm_state(self):
        # The unchanged auto_harvest node expects a fresh tracker heartbeat.
        now = self.get_clock().now().nanoseconds / 1e9
        msg = String(data=json.dumps({
            'state': self._arm_state,
            'sequence': self._arm_sequence,
            'reason': self._arm_reason,
            'hold_ready': self._arm_hold_ready,
            'stamp': now,
        }, allow_nan=False))
        self._arm_state_pub.publish(msg)

        if (self._ee_ready and self._ee_state == 'WAIT_ARM_STARTUP'
                and self._arm_state == 'STARTUP'):
            self._set_arm_state('APPROACH', 'startup_complete')

    def _wait_for_ee_state(self, expected, timeout=None):
        deadline = time.monotonic() + (
            self._ee_cycle_timeout if timeout is None else timeout)
        terminal = {'FAULT', 'ABORTED'}
        with self._ee_condition:
            while True:
                if self._ee_state in expected:
                    return self._ee_state
                if self._ee_state in terminal:
                    raise GatewayError(
                        f'auto_harvestが{self._ee_state}へ移行しました: '
                        f'{self._ee_reason}')
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise GatewayError(
                        f'auto_harvestの状態待ちがタイムアウトしました '
                        f'(current={self._ee_state}, expected={sorted(expected)})')
                self._ee_condition.wait(min(remaining, .2))

    def _hold_callback(self, _request, response):
        # arm_service has no stop/hold operation. Rejecting this explicitly
        # prevents the EE controller from assuming that an arm stop occurred.
        response.success = False
        response.message = (
            'このアーム構成には独立したhold/停止サービスがありません。'
            '現在位置と非常停止を確認してください')
        return response

    def _pull_callback(self, _request, response):
        if self._arm_state != 'HARVEST_HOLD':
            response.success = False
            response.message = f'引き戻し要求を受け付けられません: {self._arm_state}'
            return response
        self._pull_requested.set()
        response.success = True
        response.message = 'relayがアーム初期位置への復帰を実行します'
        return response

    def _resume_callback(self, _request, response):
        if self._arm_state != 'RETURNED':
            response.success = False
            response.message = f'復帰完了前の再開要求です: {self._arm_state}'
            return response
        self._set_arm_state('APPROACH', 'operator_resume')
        response.success = True
        response.message = '次のiPad収穫要求を受け付け可能です'
        return response

    def run_harvest_phase(self):
        if not self.last_targets or self.last_pre_arm_height is None:
            raise GatewayError(
                '手先視点で十字を合わせ、先に「トマト検出」を押してください')
        if not self._ee_ready or self._ee_state != 'APPROACH':
            raise GatewayError(
                'エンドエフェクタが収穫待機状態ではありません '
                f'(ready={self._ee_ready}, state={self._ee_state})')

        target = self.last_targets[0]
        pre_h = self.last_pre_arm_height
        self._clear_targets()
        self._pull_requested.clear()
        self.get_logger().info(
            f'[EE TEST] arm target x={target.x} y={target.y} z={target.z} '
            f'direction={target.approach_direction}')

        # The arm service returns only after its target motion reports complete.
        self.arm_send_request_target(target, pre_h)
        self._set_arm_state('HARVEST_HOLD', 'approach_complete', True)
        self._wait_for_ee_state({'WAIT_ARM_RETURN'})

        if not self._pull_requested.wait(self._ee_cycle_timeout):
            raise GatewayError('auto_harvestからアーム復帰要求が届きませんでした')

        # Match the existing auto_harvest sequence: close hook, return arm,
        # then restore the EE initial pose before accepting the next target.
        self._set_arm_state('RETURNING', 'relay_arm_return')
        self.arm_send_request_init()
        self._set_arm_state('RETURNED', 'return_complete_wait_for_n')
        self._wait_for_ee_state({'WAIT_NEXT_CYCLE'})
        self._ee_key_pub.publish(String(data='n'))
        self._wait_for_ee_state({'APPROACH'})
        self._reset_manual_flow()
        return True, 'アーム到達後にEE収穫・初期位置復帰まで完了しました'


def main(args=None):
    rclpy.init(args=args)
    node = HarvestGatewayEETestNode()
    executor = MultiThreadedExecutor(num_threads=4)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        node.get_logger().info('Shutting down')
    finally:
        executor.shutdown()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
