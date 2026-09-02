import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_share = FindPackageShare("rover_description")

    xacro_file = PathJoinSubstitution([pkg_share, "urdf", "rover.urdf.xacro"])
    world_file = PathJoinSubstitution([pkg_share, "worlds", "rover_world.sdf"])

    # ParameterValue(..., value_type=str) is required here -- without it,
    # launch_ros tries to auto-detect the parameter type by YAML-parsing the
    # Command substitution's output, and a URDF/XML string isn't valid YAML
    # (colons like `xmlns:xacro=` break the parse), which fails the launch
    # before robot_state_publisher ever starts.
    robot_description = {
        "robot_description": ParameterValue(
            Command(["xacro ", xacro_file]), value_type=str
        )
    }

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("ros_gz_sim"), "launch", "gz_sim.launch.py"
            )
        ),
        launch_arguments={"gz_args": [world_file, " -r"]}.items(),
    )

    # use_sim_time is essential here: without it robot_state_publisher stamps
    # TF with wall-clock while everything from Gazebo (the /odom message, the
    # odom->base_link transform, sensor data) is stamped with sim time off
    # /clock. The mismatch shows up as tf2 extrapolation errors the moment
    # anything tries to chain base_link->lidar_link with odom->base_link, and
    # it silently breaks slam_toolbox later.
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[robot_description, {"use_sim_time": True}],
    )

    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=["-topic", "robot_description", "-name", "rover", "-z", "0.3"],
        output="screen",
    )

    gz_bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        arguments=[
            "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
            "/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan",
            # Ground-truth odometry + the odom->base_link transform, both from
            # the OdometryPublisher plugin in rover.urdf.xacro. '[' means
            # gz -> ros only, so the bridge can never publish back into the sim
            # or inject a loop into /tf. The Pose_V on /odom_tf is remapped
            # onto /tf below so the TF tree gets its odom->base_link edge.
            "/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry",
            "/odom_tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V",
        ],
        remappings=[("/odom_tf", "/tf")],
        output="screen",
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster"],
        output="screen",
    )

    steer_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["steer_controller"],
        output="screen",
    )

    wheel_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["wheel_controller"],
        output="screen",
    )

    swerve_kinematics_node = Node(
        package="rover_swerve_controller",
        executable="swerve_kinematics_node",
        output="screen",
    )

    return LaunchDescription(
        [
            gz_sim,
            robot_state_publisher,
            spawn_robot,
            gz_bridge,
            joint_state_broadcaster_spawner,
            steer_controller_spawner,
            wheel_controller_spawner,
            swerve_kinematics_node,
        ]
    )
