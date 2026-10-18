import rclpy
from rclpy.node import Node
from tf2_ros.buffer import Buffer
from tf2_ros.transform_listener import TransformListener
from tf2_ros import TransformException
import sys
from nav_msgs.msg import Odometry

import numpy as np

#Fix this, uncompleted
def compose_transform(T_ab, R_ab, T_bc, R_bc):
    """
    Compose transformations A -> B and B -> C to obtain A -> C.

    Parameters:
        T_ab: Translation xyz from A to B, shape (3,)
        R_ab: Quaternion xyzw from A to B, shape (4,)
        T_bc: Translation xyz from B to C, shape (3,)
        R_bc: Quaternion xyzw from B to C, shape (4,)

    Returns:
        T_ac: Translation xyz from A to C
        R_ac: Quaternion xyzw from A to C
    """
    from scipy.spatial.transform import Rotation;
    # Convert quaternions to rotation objects
    rot_ab = Rotation.from_quat(R_ab)
    rot_bc = Rotation.from_quat(R_bc)

    # Compose translations: rotate T_bc into frame A, then add T_ab
    T_ac = np.asarray(T_ab) + rot_ab.apply(T_bc)

    # Compose rotations (order matters)
    R_ac = (rot_ab * rot_bc).as_quat()

    return T_ac, R_ac

class Distance(Node):
    def __init__(self, SOURCE):
        super().__init__('DistanceGetter');
        self.timer = self.create_timer(1.0, self.timer_callback);#every one second, call the self.timer_callback
        #initial: Get distance from any Frame to Frame "camera_link"
        self.SOURCE = SOURCE;
        self.TARGET = "camera_link";
        self.tf_buffer = Buffer();
        self.tf_listener = TransformListener(self.tf_buffer, self);
        self.odom_pose = None
        self.odom_sub = self.create_subscription(
            Odometry,
            '/zed/zed_node/odom',
            self.odom_callback,
            10
        )

    #this should be tested with. Get from ZED data
    #depends on how the ZED camera is defined, fix this function
    def odom_callback(self, msg):
        self.odom_pose = msg.pose.pose
        self.odom_frame = msg.header.frame_id
        self.odom_child_frame = msg.child_frame_id


    def timer_callback(self):

        OdomValid = DistanceValid = False;
       
        if self.odom_pose is not None:
            OdomValid = True;
            p1 = self.odom_pose.position
            q1 = self.odom_pose.orientation

            self.get_logger().info(
                f'Odometry frames: {self.odom_frame} -> '
                f'{self.odom_child_frame}'
            )
            self.get_logger().info(
                f'Position: x={p1.x:.3f}, y={p1.y:.3f}, z={p1.z:.3f}'
            )
            self.get_logger().info(
                f'Orientation: x={q1.x:.3f}, y={q1.y:.3f}, '
                f'z={q1.z:.3f}, w={q1.w:.3f}'
            )
        else:
            self.get_logger().info('Cannot get the distance between ZED to the O')

        try:
            DistanceValid = True;
            now = rclpy.time.Time();
            trans = self.tf_buffer.lookup_transform(
                self.SOURCE, 
                self.TARGET, 
                now, 
                timeout = rclpy.duration.Duration(seconds = 1.0)
            );

            p2 = trans.transform.translation;
            q2 = trans.transform.rotation;

            self.get_logger().info(f'Distance from {self.SOURCE} -> {self.TARGET}');
            self.get_logger().info(
                f'Position: x={p2.x:.3f}, y={p2.y:.3f}, z={p2.z:.3f}'
            )
            self.get_logger().info(
                f'Orientation: x={q2.x:.3f}, y={q2.y:.3f}, '
                f'z={q2.z:.3f}, w={q2.w:.3f}'
            )
        except TransformException as ex:
            self.get_logger().info(f'Cannot get the distance between {self.SOURCE} to {self.TARGET} as: {ex}');

        if OdomValid and DistanceValid:
            TransformationValue, RotationValue = compose_transform(p1, q1, p2, q2);
            self.get_logger().info(f'Distance from {self.SOURCE} to ZED: ')
            self.get_logger().info(
                f'Position: x={TransformationValue.x:.3f}, y={TransformationValue.y:.3f}, z={TransformationValue.z:.3f}'
            )
            self.get_logger().info(
                f'Orientation: x={RotationValue.x:.3f}, y={RotationValue.y:.3f}, '
                f'z={RotationValue.z:.3f}, w={RotationValue.w:.3f}'
            )
        else:
            self.get_logger().info(f'Unfortunately, There is an error in getting data');

def main(args = None):
    rclpy.init(args = args);
    node = Distance(sys.argv[1]);
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main();