# Space Bulls — Nav2 Migration and Validation (A1)

## Overview

This package configures Nav2 for the Space Bulls rover
simulation using ROS 2 Jazzy.

The current simulation uses odom as its navigation reference
frame. Global map localization is not yet implemented.

## Requirements

- ROS 2 Jazzy
- Nav2
- RViz2
- Gazebo Harmonic
- Docker development environment (recommended)
- WSL2/WSLg for graphical use on Windows

The repository's docker/dockerfile.dev provides the main
ROS 2 dependencies.

## 1. Start Development Environment

From the repository root:

```bash
docker build -f docker/dockerfile.dev -t rover-dev .
./docker/run-dev.sh
```

The Docker image only needs rebuilding when its dependencies
or Dockerfile change.

## 2. Build Workspace

Inside the Docker container:

```bash
cd /workspaces/rover_ws
colcon build --symlink-install
source install/setup.bash
```

## 3. Launch Rover Simulation

In the first container terminal:

```bash
ros2 launch rover_description gazebo.launch.py
```

This launches the Gazebo simulation, robot description,
controllers, odometry, and sensor interfaces.

## 4. Launch Nav2

Open a second WSL terminal:

```bash
docker exec -it rover-dev-container bash
```

Then launch navigation:

```bash
ros2 launch rover_navigation nav2_sim.launch.py
```

This starts the configured Nav2 nodes and RViz.

## 5. Verify Navigation Interfaces

In a container terminal, check:

```bash
ros2 topic list
ros2 topic echo --once /odom
ros2 topic echo --once /scan
ros2 run tf2_ros tf2_echo odom base_link
```

Stop tf2_echo using Ctrl+C.

Check Nav2 actions:

```bash
ros2 action list
```

## 6. Test Navigation in RViz

1. Confirm the RViz Fixed Frame is odom.
2. Verify the rover model and TF displays.
3. Inspect local and global costmaps.
4. Select the Nav2 Goal tool.
5. Send a reachable navigation goal.
6. Observe rover movement and goal completion.
7. Test additional goals and obstacle behavior.

A successful launch alone does not establish that
navigation or obstacle avoidance works correctly.

## Coordinate Frames

Current A1 configuration:

- RViz Fixed Frame: odom
- BT Navigator global frame: odom
- Global costmap frame: odom
- Local costmap frame: odom
- Robot base frame: base_link

The simulation must provide odom -> base_link TF.

A map -> odom transform is not required for this
odometry-based setup. Global localization can be
integrated later.

## Troubleshooting

ROS 2 command not found:
- Enter the Docker development container.

RViz frame errors:
- Verify odom -> base_link is being published.

Missing costmap or obstacle data:
- Verify /scan and /odom are publishing.

Navigation goals fail:
- Check Nav2 lifecycle states, TF, action servers,
  and velocity command connections.

Map display warnings:
- The default RViz configuration includes a /map
  display. No /map publisher is required for A1's
  current odometry-only setup.

## Known Limitations

- Navigation uses odometry rather than global localization.
- Odometry drift may accumulate over time.
- Gazebo must be launched separately from Nav2.
- Runtime behavior must be validated in simulation.

## Package Files

- launch/nav2_sim.launch.py
- config/nav2_params.yaml
- rviz/nav2.rviz
- package.xml
