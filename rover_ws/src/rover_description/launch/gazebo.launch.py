import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_share = FindPackageShare("rover_description")

    xacro_file = PathJoinSubstitution([pkg_share, "urdf", "rover.urdf.xacro"])
    world_file = PathJoinSubstitution([pkg_share, "worlds", "rover_world.sdf"])

    robot_description = {"robot_description": Command(["xacro ", xacro_file])}

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory("ros_gz_sim"), "launch", "gz_sim.launch.py"
            )
        ),
        launch_arguments={"gz_args": [world_file, " -r"]}.items(),
    )

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[robot_description],
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
        ],
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
