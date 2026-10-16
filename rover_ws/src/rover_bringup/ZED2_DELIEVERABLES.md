# ZED 2 ROS 2 Test Guide

Tested with ROS 2 Jazzy and ZED SDK 5.5.0 on the development computer.
The ZED SDK and ROS 2 wrapper must already be installed and built.

Confirmed during testing: RGB, depth, point cloud, IMU, odometry that updates
with movement, and RViz visualization. Sustained rates and Jetson deployment
still need separate verification.

## 1. Source the workspace

Run in every new terminal used for this test:

```bash
source /opt/ros/jazzy/setup.bash
source ~/DEIMOS-ws/rover_ws/install/setup.bash
```

Use the same ROS domain and communication middleware settings in each terminal.

## 2. Create the working configuration

```bash
cat > /tmp/zed-test.yaml <<'EOF'
/**:
  ros__parameters:
    pos_tracking:
      pos_tracking_enabled: true
    depth:
      depth_stabilization: 0
EOF
```

During troubleshooting, tracking was temporarily set to `false` to test RGB,
depth, and the cloud separately. The final working configuration uses `true`
so odometry is available.

## 3. Launch the camera

Close any ZED SDK tools first. Run this command and leave the terminal running:

```bash
ros2 launch zed_wrapper zed_camera.launch.py \
  camera_model:=zed2 \
  camera_name:=zed \
  enable_ipc:=false \
  publish_tf:=false \
  publish_map_tf:=false \
  ros_params_override_path:=/tmp/zed-test.yaml
```

Keep the camera still and facing a well-lit, textured scene during startup.
These settings disable intra-process communication and motion-transform
broadcasting. Odometry messages remain enabled.

## 4. Check the topics

Open another terminal, source the workspace, then run:

```bash
ros2 topic list -t
```

Check each required output:

```bash
# RGB
timeout 20s ros2 topic echo \
  /zed/zed_node/rgb/color/rect/image \
  --once --field header --qos-reliability best_effort

# Depth
timeout 20s ros2 topic echo \
  /zed/zed_node/depth/depth_registered \
  --once --field header --qos-reliability best_effort

# Point cloud
timeout 20s ros2 topic echo \
  /zed/zed_node/point_cloud/cloud_registered \
  --once --field header --qos-reliability best_effort

# IMU
timeout 20s ros2 topic echo \
  /zed/zed_node/imu/data \
  --once --qos-reliability best_effort

# Odometry
timeout 30s ros2 topic echo \
  /zed/zed_node/odom \
  --once --qos-reliability best_effort
```

Each command should print a message and exit. A timeout with no message means
delivery was not confirmed. Listing a topic alone does not prove it is streaming.

## 5. Measure publication rates

Run each command **separately** for about 30 seconds. Press Ctrl+C before
starting the next command; these commands do not exit automatically.

```bash
ros2 topic hz /zed/zed_node/rgb/color/rect/image --window 100
ros2 topic hz /zed/zed_node/depth/depth_registered --window 100
ros2 topic hz /zed/zed_node/point_cloud/cloud_registered --window 100
ros2 topic hz /zed/zed_node/imu/data --window 100
ros2 topic hz /zed/zed_node/odom --window 100
```

Record the measured rates. Startup delays and message losses can affect the
averages; configured rates are not proof of actual performance.

## 6. Test movement

```bash
ros2 topic echo /zed/zed_node/odom \
  --field pose.pose --qos-reliability best_effort
```

Slowly move and rotate the camera. Confirm position and orientation change
while RGB, depth, and the cloud continue updating. Press Ctrl+C to stop the echo.

## 7. View the camera in RViz

Install RViz once if needed, in the ROS environment used for this test:

```bash
sudo apt update
sudo apt install ros-jazzy-rviz2
```

From a sourced terminal with a graphical display:

```bash
rviz2
```

1. Set **Global Options → Fixed Frame** to `zed_camera_link`.
2. Select **Add → By topic** and add the following displays.
3. Set each display's topic **Reliability Policy** to **Best Effort**.

| Display | Topic |
| --- | --- |
| Image | `/zed/zed_node/rgb/color/rect/image` |
| Image | `/zed/zed_node/depth/depth_registered` |
| PointCloud2 | `/zed/zed_node/point_cloud/cloud_registered` |

Confirm both images and the colored cloud update. Use `zed_camera_link` as the
fixed frame because motion TF broadcasting is disabled in this test. Save the
RViz configuration through **File → Save Config As** if desired.

## 8. Troubleshooting

- **Camera or sensors fail to open:** stop the camera launch, close ZED tools,
  and reconnect the camera directly to a USB 3 port.
- **Self-calibration warning:** clear both lenses' views and point the camera
  at a well-lit scene with visible details, avoiding nearby obstructions.
- **Tracking appears stuck:** temporarily set `pos_tracking_enabled: false`,
  restart, and check RGB/depth/cloud. Odometry is unavailable during this test.
  Restore `true` afterward and restart again.
- **Message-loss warnings:** a received message confirms delivery, but repeated
  losses or stalls require checking sustained rates and system/USB load.
- **Empty RViz displays:** verify the exact topic names, Best Effort reliability,
  and fixed frame `zed_camera_link`.

For SDK-only troubleshooting, stop ROS launch and run these tools one at a time:

```bash
/usr/local/zed/tools/ZED_Diagnostic
/usr/local/zed/tools/ZED_Depth_Viewer
```

Close each tool before launching another camera application. Run commands at a
shell prompt, not in the terminal while ROS launch is occupying it.

## 9. Save the working setup

`/tmp/zed-test.yaml` is temporary. Copy it into the project to keep it:

```bash
mkdir -p ~/DEIMOS-ws/rover_ws/src/rover_bringup/config
cp -i /tmp/zed-test.yaml \
  ~/DEIMOS-ws/rover_ws/src/rover_bringup/config/zed2-tested.yaml
```

On subsequent launches, replace the final launch argument with:

```bash
ros_params_override_path:=$HOME/DEIMOS-ws/rover_ws/src/rover_bringup/config/zed2-tested.yaml
```

This preserves the YAML only; keep the other working launch arguments too.
Creating the directory alone does not create or install a ROS package.

Before marking hardware acceptance complete, save RViz screenshots, measured
topic rates, software versions, and a short record of the motion test. Test
for several minutes with all streams active. The successful development-computer
test does not establish compatibility or performance on the Jetson.
