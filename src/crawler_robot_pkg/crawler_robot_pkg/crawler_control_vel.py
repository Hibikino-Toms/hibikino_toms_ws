#!/usr/bin/env python
# -*- coding: utf-8 -*-

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool

class MobilityControllerNode(Node):
    def __init__(self):
        super().__init__('mobility_controller')
        
        self.is_harvesting = False

        # 収穫シナリオ管理ノードからの「収穫モード(True/False)」を受信
        self.sub_harvest_mode = self.create_subscription(
            Bool, 
            'harvest_mode', 
            self.harvest_mode_callback, 
            10
        )
        
        # Nav2や手動操作からの速度指令を受信
        self.sub_cmd_vel = self.create_subscription(
            Twist, 
            'cmd_vel', 
            self.cmd_vel_callback, 
            10
        )
        
        # 実際のクローラー(足回り)への速度指令を出力
        self.pub_cmd_vel_cr = self.create_publisher(
            Twist, 
            'cmd_vel_cr', 
            10
        )

    def harvest_mode_callback(self, msg):
        self.is_harvesting = msg.data
        if self.is_harvesting:
            self.get_logger().info("収穫モードON: 足回りを強制停止します")
            self.pub_cmd_vel_cr.publish(Twist()) # 即座に速度0を送信
        else:
            self.get_logger().info("探索モードON: 連続走行を許可します")

    def cmd_vel_callback(self, msg):
        # 収穫中であれば安全のため速度0を送り続け、それ以外はパススルーする
        if self.is_harvesting:
            self.pub_cmd_vel_cr.publish(Twist())
        else:
            self.pub_cmd_vel_cr.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = MobilityControllerNode()
    
    try:
        # このノードは非常に軽い処理しかしないため、シングルスレッドで超高速に回り続けます
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.get_logger().info("Ctrl+Cが押されました。")
    finally:
        node.pub_cmd_vel_cr.publish(Twist())
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()