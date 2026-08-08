import math

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray

# Order must match the `joints:` lists in
# rover_description/config/rover_controllers.yaml.
MODULES = ("front_left", "front_right", "rear_left", "rear_right")

# Module positions relative to base_link (x: forward, y: left), matching the
# x_reflect/y_reflect layout in rover_description/urdf/rover.urdf.xacro.
WHEEL_BASE = 0.4
WHEEL_SEPARATION = 0.5
WHEEL_RADIUS = 0.15
MODULE_POSITIONS = {
    "front_left": (WHEEL_BASE / 2, WHEEL_SEPARATION / 2),
    "front_right": (WHEEL_BASE / 2, -WHEEL_SEPARATION / 2),
    "rear_left": (-WHEEL_BASE / 2, WHEEL_SEPARATION / 2),
    "rear_right": (-WHEEL_BASE / 2, -WHEEL_SEPARATION / 2),
}

# Below this module speed, hold the last commanded steer angle instead of
# snapping to atan2(0, 0) == 0 -- avoids the wheels jittering back to
# "forward" every time the rover comes to a stop.
MIN_SPEED_FOR_STEERING = 1e-3


class SwerveKinematicsNode(Node):
    """Converts /cmd_vel into per-module steer-angle and wheel-speed commands.

    NOTE: this does the direct inverse-kinematics computation only. It does
    not do wheel-angle-flip optimization (i.e. choosing to reverse a wheel's
    direction and rotate the module by <90 deg instead of turning it up to
    180 deg) -- a real implementation should add that to avoid unnecessary
    steering motion.
    """

    def __init__(self):
        super().__init__("swerve_kinematics_node")

        self._last_steer_angles = {name: 0.0 for name in MODULES}

        self.create_subscription(Twist, "cmd_vel", self._cmd_vel_callback, 10)
        self._steer_pub = self.create_publisher(
            Float64MultiArray, "/steer_controller/commands", 10
        )
        self._wheel_pub = self.create_publisher(
            Float64MultiArray, "/wheel_controller/commands", 10
        )

    def _cmd_vel_callback(self, msg: Twist) -> None:
        vx = msg.linear.x
        vy = msg.linear.y
        omega = msg.angular.z

        steer_angles = []
        wheel_speeds = []

        for name in MODULES:
            x, y = MODULE_POSITIONS[name]
            module_vx = vx - omega * y
            module_vy = vy + omega * x
            speed = math.hypot(module_vx, module_vy)

            if speed > MIN_SPEED_FOR_STEERING:
                angle = math.atan2(module_vy, module_vx)
                self._last_steer_angles[name] = angle
            else:
                angle = self._last_steer_angles[name]

            steer_angles.append(angle)
            wheel_speeds.append(speed / WHEEL_RADIUS)

        self._steer_pub.publish(Float64MultiArray(data=steer_angles))
        self._wheel_pub.publish(Float64MultiArray(data=wheel_speeds))


def main(args=None):
    rclpy.init(args=args)
    node = SwerveKinematicsNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
