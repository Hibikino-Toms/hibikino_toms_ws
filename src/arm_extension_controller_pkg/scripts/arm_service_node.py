#!/usr/bin/env python3
"""距離を受け取りPicoへ送り、完了後に実測ベースの推定値を返す。"""
import math
import threading

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from arm_extension_controller_pkg.srv import MoveArm
from arm_driver import PicoArm, SimulatedArm


class ArmServiceNode(Node):
    def __init__(self):
        super().__init__("arm_service_node")
        self.declare_parameter("simulate", True)
        self.declare_parameter("port", "")
        self.declare_parameter("serial_number", "")
        self.declare_parameter("max_position_mm", 0.0)
        self.declare_parameter("max_move_mm", 20.0)
        self.declare_parameter("timeout_sec", 45.0)
        value = lambda name: self.get_parameter(name).value
        maximum, step = float(value("max_position_mm")), float(value("max_move_mm"))
        timeout = float(value("timeout_sec"))
        if not all(map(math.isfinite, (maximum, step, timeout))) or step <= 0 or timeout < 25:
            raise ValueError("範囲を有限値、max_move_mm>0、timeout_sec>=25に設定してください")
        self.simulate = value("simulate")
        self.driver = (SimulatedArm(maximum, step) if self.simulate else
                       PicoArm(value("port"), value("serial_number"), maximum, step, timeout))
        self.cancel = threading.Event()
        self.operation = threading.Lock()
        self.srv = self.create_service(MoveArm, "arm_extension/control", self.control,
                                      callback_group=ReentrantCallbackGroup())
        self.get_logger().info("SIMULATION（実機は動きません）" if self.simulate else "実機モード")
        self.get_logger().info("arm_extension/control 準備完了。homeで原点復帰、zeroで手動原点設定。")

    def control(self, request, response):
        command = request.command.strip().lower()
        response.position_mm = float("nan")
        if command == "stop":
            self.cancel.set()
            response.success = True
            response.message = "停止を要求しました（停止完了ではありません）"
            return response
        if command not in ("move", "zero", "home"):
            response.message = "command は move / home / zero / stop"
            return response
        if not self.operation.acquire(blocking=False):
            response.message = "動作中です。別の移動要求は受け付けません"
            return response
        try:
            self.cancel.clear()
            result = self.driver.execute(command, request.distance_mm, self.cancel)
            response.success = result.success
            response.position_valid = result.position_valid
            response.actual_distance_mm = result.actual_distance_mm
            response.position_mm = result.position_mm
            response.message = result.message
            self.get_logger().info(f"{command}: {result.message}, position={result.position_mm:.2f} mm")
        except Exception as error:
            response.message = str(error)
            self.get_logger().error(str(error))
        finally:
            self.operation.release()
        return response


def main(args=None):
    rclpy.init(args=args)
    node, executor = None, MultiThreadedExecutor(num_threads=2)
    try:
        node = ArmServiceNode()
        executor.add_node(node)
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        if node:
            node.cancel.set()
        executor.shutdown(timeout_sec=2)
        if node:
            node.driver.close()
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
