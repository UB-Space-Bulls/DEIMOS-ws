# zed_cuvslam.launch.py -- bring up isaac_ros_visual_slam (cuVSLAM) against a
# running ZED node, for the Isaac ROS VSLAM pull-forward validation
# (docker/dockerfile.isaac-dev, CLAUDE.md SLAM go/no-go plan).
#
# This launches ONLY the cuVSLAM side. Start the ZED node first, in another
# terminal:
#
#   ros2 launch zed_wrapper zed_camera.launch.py camera_model:=zed2
#
# then here:
#
#   ros2 launch /workspaces/rover_ws/zed_cuvslam.launch.py
#
# Topic / frame names below are for zed-ros2-wrapper v5.2.2 with the default
# camera_name:=zed (mTopicRoot = /zed/zed_node/, optical frames
# <name>_{left,right}_camera_frame_optical -- verified against the wrapper
# source). If you launch the ZED node with a different camera_name, override
# `cam` below or the remaps won't line up.
#
# cuVSLAM consumes the MONO8 rectified stereo pair (left/right .../gray/rect/
# image). Watch for:
#   ros2 topic hz /visual_slam/tracking/odometry     -- should track camera motion
#   ros2 topic echo /visual_slam/status              -- 0 == tracking OK
#   ros2 run rqt_tf_tree rqt_tf_tree                 -- map->odom->zed must exist

from launch import LaunchDescription
from launch_ros.actions import ComposableNodeContainer
from launch_ros.descriptions import ComposableNode

cam = 'zed'  # must match the ZED node's camera_name
root = f'/{cam}/zed_node'

remappings = [
    ('visual_slam/image_0',       f'{root}/left/gray/rect/image'),
    ('visual_slam/camera_info_0', f'{root}/left/gray/rect/camera_info'),
    ('visual_slam/image_1',       f'{root}/right/gray/rect/image'),
    ('visual_slam/camera_info_1', f'{root}/right/gray/rect/camera_info'),
]

parameters = [{
    'num_cameras': 2,
    'min_num_images': 2,
    'enable_image_denoising': False,
    'rectified_images': True,            # ZED .../rect/ images are rectified
    'enable_slam_visualization': True,   # publish landmarks/observations for RViz
    'enable_landmarks_view': True,
    'enable_observations_view': True,
    'enable_localization_n_mapping': True,
    # Frames: cuVSLAM needs TF from base_frame to each optical frame. The ZED
    # node's robot_state_publisher (zed_description) puts these on /tf_static.
    'base_frame': cam,
    'camera_optical_frames': [
        f'{cam}_left_camera_frame_optical',
        f'{cam}_right_camera_frame_optical',
    ],
    # publish map->odom (loop-closed) and odom->base_link (VO). The ZED node
    # is launched with its own pos-tracking off so these don't collide.
    'publish_map_to_odom_tf': True,
    'publish_odom_to_base_tf': True,
    'map_frame': 'map',
    'odom_frame': 'odom',
    # ZED publishes images RELIABLE by default (zed.yaml qos_reliability: 1).
    # If cuVSLAM logs no images arriving, this is the first knob -- try
    # 'SENSOR_DATA'. (Only image_qos is exposed; there's no separate
    # camera_info_qos param in 4.6.)
    'image_qos': 'DEFAULT',
}]


def generate_launch_description():
    visual_slam_node = ComposableNode(
        name='visual_slam_node',
        package='isaac_ros_visual_slam',
        plugin='nvidia::isaac_ros::visual_slam::VisualSlamNode',
        remappings=remappings,
        parameters=parameters,
    )

    return LaunchDescription([
        ComposableNodeContainer(
            name='visual_slam_launch_container',
            namespace='',
            package='rclcpp_components',
            executable='component_container',
            composable_node_descriptions=[visual_slam_node],
            output='screen',
        ),
    ])
