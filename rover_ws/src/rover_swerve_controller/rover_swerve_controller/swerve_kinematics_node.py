import math

import rclpy
from geometry_msgs.msg import Twist
from rclpy.node import Node
from std_msgs.msg import Float64MultiArray

# Order must match the `joints:` lists in
# rover_description/config/rover_controllers.yaml.
MODULES = ("front_left", "front_right", "rear_left", "rear_right")

# Derived from the CAD-based rover_description/urdf/rover.urdf.xacro, not
# from a symmetric WHEEL_BASE/WHEEL_SEPARATION pair -- the real chassis is
# NOT symmetric front-to-back (front modules sit 0.3175m from center, rear
# modules sit 0.2921m from center). Values below are each *_steer_joint's
# <origin> in rover.urdf.xacro, converted from that URDF/base_link frame
# (where +x = left, -y = front -- swapped and sign-flipped from this file's
# own "x: forward, y: left" convention) into (forward_offset, left_offset).
# Re-derive these from the URDF again if the chassis geometry changes.
MODULE_POSITIONS = {
    "front_left": (0.3175, 0.3556),
    "front_right": (0.3175, -0.3556),
    "rear_left": (-0.2921, 0.3556),
    "rear_right": (-0.2921, -0.3556),
}

# Measured directly off rover_description/meshes/wheel1_1.stl's bounding box
# (diameter ~203.2mm across the two axes perpendicular to the rolling axis)
# -- i.e. an 8in-diameter wheel, not the 0.15m (300mm-diameter) placeholder.
WHEEL_RADIUS = 0.1016

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
