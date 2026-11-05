#!/usr/bin/env python3
"""例: 10 -> 10mm伸ばす、-10 -> 10mm戻す。"""
import math
import rclpy
from rclpy.node import Node
from arm_extension_controller_pkg.srv import MoveArm


class ArmClientNode(Node):
    def __init__(self):
        super().__init__("arm_client_node")
        self.client = self.create_client(MoveArm, "arm_extension/control")

    def run(self):
        while rclpy.ok() and not self.client.wait_for_service(timeout_sec=1):
            self.get_logger().info("アームのサービス待ち...")
        while rclpy.ok():
            text = input("移動量[mm]（+伸ばす/-戻す）、home、zero、stop、q: ").strip().lower()
            if text == "q":
                return
            request = MoveArm.Request()
            if text in ("zero", "home", "stop"):
                if text == "zero" and input("停止した原点でスイッチが押され、断線なし？ yes: ").strip() != "yes":
                    continue
                if text == "home" and input("原点スイッチが今は未押下で、F方向へ戻してよい？ yes: ").strip() != "yes":
                    continue
                request.command = text
            else:
                try:
                    request.distance_mm = float(text)
                    if not math.isfinite(request.distance_mm):
                        raise ValueError()
                except ValueError:
                    print("数値、home、zero、stop、qのどれかを入力してください")
                    continue
                request.command = "move"
            future = self.client.call_async(request)
            rclpy.spin_until_future_complete(self, future, timeout_sec=60)
            if not future.done():
                # クライアントを中断してもサービス要求は取り消されない。
                self.client.call_async(MoveArm.Request(command="stop"))
                print("応答タイムアウト。停止を要求しました。再送せず実機を確認してください。")
                continue
            if future.exception():
                print(f"サービス通信エラー: {future.exception()}。実機を確認してください。")
                continue
            result = future.result()
            print(f"success={result.success}, 今回={result.actual_distance_mm:.2f}mm, "
                  f"原点から={result.position_mm:.2f}mm, 原点有効={result.position_valid}")
            print(result.message)


def main(args=None):
    rclpy.init(args=args)
    node = ArmClientNode()
    try:
        node.run()
    except (KeyboardInterrupt, EOFError):
        # 退出はモーターの停止保証ではない。サービス側Ctrl+C/物理停止も使用する。
        if rclpy.ok():
            future = node.client.call_async(MoveArm.Request(command="stop"))
            rclpy.spin_until_future_complete(node, future, timeout_sec=1)
    finally:
        if rclpy.ok():
            future = node.client.call_async(MoveArm.Request(command="stop"))
            rclpy.spin_until_future_complete(node, future, timeout_sec=1)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
