# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Space Bulls Mars Rover — Project Context

This file summarizes the software architecture and decisions for the URC
(University Rover Challenge) rover's dev environment. Read this before making
changes to any Dockerfile or ROS 2 package structure.

## Communication style

Most people working in this repo have limited ROS 2 experience — don't
assume familiarity with ROS jargon (nodes, topics, `ros2_control`, `colcon`,
TF, RMW, etc.). Explain a term the first time it comes up rather than
assuming it's known. Don't strip out real technical content to "simplify"
it though — keep the precision, just make it land for someone who hasn't
used ROS before. For anything longer than a couple sentences, follow the
full explanation with a short **TL;DR** in plain language.

Also work in some Gen Z slang naturally where it fits — no cap, rizz,
crashout, huzz, or similar. Doesn't need to be forced into every sentence,
just keep things from reading completely dry.

## Software stack

- **ROS 2 Jazzy** across the entire system — rover, base station, and dev
  environment. One wrinkle: the Orin Nano runs an older Ubuntu (22.04, from
  JetPack 6.x — see Hardware), and ROS 2 Jazzy targets Ubuntu 24.04. So on the
  Orin, Jazzy runs **inside a container** on top of the older host OS instead
  of natively; everywhere else (base station, the rover's second computer, dev
  laptops) it's Ubuntu 24.04 and Jazzy is native. (Jazzy over Humble: longer
  support window, current Ubuntu LTS, and containerizing on the Orin sidesteps
  the host-OS mismatch that would otherwise force Humble there.)
- **Zenoh** as the RMW/middleware layer system-wide. ("RMW" = ROS Middleware —
  the pluggable transport ROS 2 nodes use to discover and talk to each other.)
  It carries both the base-station ↔ rover radio link and the Orin ↔ ThinkPad
  link over the rover's onboard Ethernet.
- **Nav2** for navigation and path planning.
- **MoveIt 2** for arm/manipulator motion planning.
- **ros2_control** for the hardware abstraction layer driving actuators.
- GPU-accelerated perception (**Isaac ROS** — VSLAM, nvblox, object detection)
  is **out of scope for this cycle**: too heavy for the Orin Nano 8GB, and
  gated behind JetPack 7 which this Orin isn't running. See SLAM strategy for
  what carries the localization load instead.

## ROS 2 packages in this repo (`rover_ws/src/`)

- **`rover_description`** — the real chassis package: CAD-derived
  (SolidWorks-to-URDF export) swerve geometry, `ros2_control` wiring,
  Gazebo Harmonic world, and controller config. This is what Nav2/sim/
  mission work should build against. Launch `display.launch.py` (RViz) or
  `gazebo.launch.py` (Gazebo) to see the model. **The CAD geometry itself
  is still an early/interim export, not the finalized rover design** —
  treat every mesh, mass, and joint origin here as provisional until it
  comes from released-for-manufacture CAD, the same way the box/cylinder
  placeholder it replaced was provisional. (There used to be a separate
  `rover_test_description` package for validating this CAD geometry before
  it was folded in here — that's done now, so it no longer exists.)
  `rover_swerve_controller/swerve_kinematics_node.py`'s wheel radius and
  module positions are derived from this geometry (mesh bounding box and
  joint origins) — re-derive them again if the chassis geometry changes.
- **`rover_swerve_controller`** — the custom inverse-kinematics node
  (`swerve_kinematics_node.py`) that converts `/cmd_vel` into per-module
  steer-angle + wheel-speed commands, since no stock `ros2_controllers`
  swerve plugin exists.

## Hardware

Two computers ride on the rover, linked over onboard Ethernet:

- **Jetson Orin Nano 8GB** — the sensor-facing computer. Wired to the **ZED 2**
  stereo camera (USB) and the **Unitree L2** lidar (a compact 3D spinning
  lidar). Also the natural home for the `ros2_control` hardware-interface
  plugins (motor controllers over CAN/serial) and the swerve kinematics node,
  since those talk to physical devices on the chassis. Runs **JetPack 6.x**
  (currently ~6.1 = Jetson Linux 36.4, Ubuntu 22.04, kernel 5.15). This unit
  reportedly can't be flashed to JetPack 7.2 — which is fine, nothing in the
  current plan needs it; ROS 2 Jazzy runs in a container on top (see Docker
  architecture).
- **ThinkPad laptop with an NVIDIA T500 GPU** (x86_64) — the second, heavier
  compute node, for work that isn't bolted to the rover's sensors or
  actuators: Nav2 planning, SLAM, MoveIt 2, mission/autonomy logic. **The exact
  division of labor between the two computers is still TBD.** Its OS isn't
  fixed yet — target **Ubuntu 24.04 + ROS 2 Jazzy** so it matches the dev
  environment and base station and code moves onto it unchanged. Reality check
  on the T500: it's a modest GPU (Turing, 4GB) — fine for light CUDA and
  visualization, not a perception accelerator, so don't pencil in GPU-hungry
  workloads for it.

**Not on the rover:** the old **Jetson Nano** (2019, Tegra X1) is too old for
this stack — it caps out at JetPack 4.6 / Ubuntu 18.04, so no Jazzy and no
modern anything. It stays a spare for onboarding and throwaway experiments,
nothing on the flight rover.

Physical hardware: an Orin Nano is already on hand; full hardware for
integration testing is still expected around **early December**.

## SLAM strategy

The rover carries a **Unitree L2 lidar** and a **ZED 2 stereo camera**. SLAM
— "Simultaneous Localization And Mapping", i.e. building a map of the
surroundings while continuously tracking where the rover is inside it — is
built on **`slam_toolbox`**, full stop. The old Isaac ROS VSLAM go/no-go is
dead now that Isaac ROS is out of scope.

- **`slam_toolbox`** (lidar-based, CPU-only) — mature, battle-tested, and
  natively wired into Nav2. Build and tune it in Gazebo during the Aug–Nov
  portable-dev window so it's real, working SLAM before hardware integration
  starts. Light enough to run on either onboard computer.
  - Caveat: `slam_toolbox` is fundamentally **2D** SLAM — it works off one flat
    scan line and assumes roughly planar motion. The Unitree L2 is a **3D**
    lidar, so its point cloud has to be flattened to a 2D scan first (the
    `pointcloud_to_laserscan` node) before `slam_toolbox` can eat it. On rough
    Mars-analog terrain that planar assumption may get shaky.

- **RTAB-Map** is the named fallback if 2D SLAM can't cope with the terrain.
  It does full 3D graph SLAM and can fuse the L2 lidar and the ZED 2 together
  into one map. More setup and more compute than `slam_toolbox` — it'd most
  likely live on the ThinkPad + T500. Not the plan today, but the sensors and
  the compute headroom for it are already on the rover.

Design the SLAM node as a **swappable component**: the Nav2 / costmap pipeline
should consume plain `/map` and `/odom` topics with nothing
SLAM-implementation-specific baked in across the codebase, so swapping
`slam_toolbox` for RTAB-Map later stays a small change, not a rearchitecture.

**TL;DR:** `slam_toolbox` on the lidar is the whole SLAM plan, tuned in Gazebo
over the fall. Flatten the Unitree L2's 3D cloud to a 2D scan to feed it. If
planar SLAM can't handle the terrain, swap in RTAB-Map (3D, lidar + stereo
fused) on the ThinkPad — cheap to do because everything downstream just reads
`/map` and `/odom`.

## Docker architecture — three images, three jobs

Filenames are lowercase (`dockerfile.<target>`, not `Dockerfile.<target>`) —
match the case exactly in build commands on Linux.

1. **`docker/dockerfile.jetson`** — ARM64, `FROM ${BASE_IMAGE}`. The default
   base image should track the Orin's actual **JetPack 6.x** — an
   `nvcr.io/nvidia/l4t-jetpack:r36.4.x` tag matching the installed Jetson
   Linux version, **not** the stale `r39.2.0` (JetPack 7.2) value. Runs on the
   Orin Nano onboard the rover: ROS 2 Jazzy (containerized), the
   `ros2_control` hardware-interface plugins, and the sensor drivers (the ZED
   SDK for the ZED 2 — it needs CUDA, so keep a CUDA-capable base image — plus
   the Unitree L2 driver). **No Isaac ROS.** Will NOT run on a laptop — Tegra
   drivers baked in. **Verify the exact `l4t-jetpack` tag exists on NGC before
   building** — NGC images have historically lagged Jetson Linux releases by
   weeks.

2. **`docker/dockerfile.basestation`** — x86_64, `FROM ros:jazzy-desktop`.
   The actual ground-control software that runs during competition: RViz2,
   teleop, monitoring. This is the STABLE image — treat changes here as
   deliberate and reviewed, not casual experimentation. GUI/monitoring
   approach is still TBD; current file has a placeholder teleop/rqt setup.

3. **`docker/dockerfile.dev`** — x86_64, `FROM ros:jazzy-ros-base`.
   Portable dev environment for writing/testing rover-bound code (Nav2,
   MoveIt 2, ros2_control, SLAM, mission logic) on any laptop, GPU or not.
   Safe to break — it's isolated from `dockerfile.basestation` specifically so
   experimentation here can't accidentally affect working ground-control code.
   The rover's ThinkPad, once its OS is set, can run this same image (or a
   close sibling) since it's x86_64 too.

All three share `ros_entrypoint.sh`, which sources `/opt/ros/jazzy/setup.bash`
on every container start (this can't be a static `ENV` var — ROS's env setup
does more than set variables, so it has to actually execute each time).

### Common footguns when building/running

- **Always build/run from the repo root**, not from inside `docker/`. All
  three Dockerfiles `COPY docker/ros_entrypoint.sh /`, which only resolves
  correctly when the build context is the repo root — i.e.
  `docker build -f docker/dockerfile.<target> -t <tag> .` run from the top
  of the repo. Building from inside `docker/` breaks the `COPY` because the
  context shifts. The same applies to `-v $(pwd)/rover_ws:...` in
  `docker run` — `pwd` has to actually be the repo root or the mount points
  at the wrong (usually nonexistent) directory.
- **Host vs. container UID mismatch** — if `colcon build` runs inside the
  container as root (the default) against the bind-mounted `rover_ws`, the
  resulting `build/`, `install/`, `log/` directories come out root-owned on
  the host, and a later host-side `colcon build` will fail with a
  `PermissionError`. Either build consistently in one place (always
  container, or always host), or pass `--user $(id -u):$(id -g)` to
  `docker run` so output ownership matches the host user.
- **`dockerfile.dev`'s apt-get list has to be kept in sync with every
  package's `package.xml` by hand** — nothing here runs `rosdep install`,
  so adding a new `exec_depend`/`test_depend` to a package (e.g.
  `ament_lint_auto`, `joint_state_publisher`, `rviz2`) doesn't
  automatically get it installed in the image. When you add a new
  workspace dependency, double-check it's also in `dockerfile.dev`'s
  apt-get list, or the container build/launch will fail even though the
  host might already have it installed separately.

### What transfers cleanly between `dockerfile.dev` and `dockerfile.jetson`
Portable (little to no change): Nav2 costmap/planner configs, MoveIt 2
SRDF/planning configs, ros2_control controller *definitions* (not the
hardware interface plugin), custom ROS 2 nodes for mission/autonomy logic,
message/service/action definitions, Zenoh config.

NOT portable, needs real Orin time regardless: ros2_control hardware
interface plugins (talk to real motor controllers over CAN/serial), camera/
sensor drivers (the ZED SDK and the Unitree L2 driver against real devices),
sensor calibration, real-time tuning under actual thermal/power constraints.

## Simulation strategy

- **Gazebo Harmonic** — default sim for the whole team. Validates Nav2,
  MoveIt 2, ros2_control (via `gz_ros2_control`), and mission logic. Runs
  on any laptop, CPU-only is fine. Native ROS 2 integration means launch
  files and params carry over unchanged to real code. `gz_ros2_control`
  keeps the simulated hardware interface swappable for the real one
  without touching controller definitions.
- **Isaac Sim** — **dropped**, along with Isaac ROS. Its only real
  justifications were GPU perception work: feeding a perception model
  photorealistic, RTX-rendered input that Gazebo's simpler rendering can't
  stress, and generating synthetic labeled training data via domain
  randomization. With that work out of scope and no GPU big enough to lean on,
  Gazebo Harmonic covers what the team actually needs. Revisit only if a
  serious camera-based perception effort comes back.

Neither simulator is part of what ships to competition — both are dev-time
tools. The real rover does NOT run a simulation before every movement;
Nav2/MoveIt 2 compute trajectories via planning algorithms checked against
real sensor data and constraints, not by rehearsing in a simulator live.

## Timeline (Aug–Feb)

- **Aug–Nov**: portable dev work (Gazebo setup, Nav2/MoveIt2/ros2_control
  configs, base station GUI, Zenoh bridge, mission logic) — parallelizable
  across the team, any laptop.
- **Early Dec**: hardware arrives. Confirm the Orin's JetPack 6.x, verify
  Docker + CUDA passthrough on the Orin, and get the ThinkPad's OS + ROS 2
  installed and talking to the Orin over onboard Ethernet.
- **Dec–mid Jan**: hardware integration — ros2_control hardware interfaces,
  ZED 2 + Unitree L2 bringup on the Orin, `slam_toolbox` running on real lidar
  data, sensor calibration. Highest-risk phase; budget extra time here. Note:
  this window likely overlaps winter break/finals — decide explicitly whether
  integration work continues (even partially, remote) over break, since that
  affects how much buffer is actually available.
- **Mid Jan–Feb**: full base station ↔ rover integration testing, end-to-end
  mission runs, debugging buffer.

## GitHub structure

- Dockerfiles and `ros_entrypoint.sh` live under a `docker/` directory at
  the repo root.
- `.gitignore` should exclude colcon build artifacts: `build/`, `install/`,
  `log/`.
- Build commands (adjust paths to match actual repo layout):
  - `docker build -f docker/dockerfile.dev -t rover-dev .`
  - `docker run -it --rm -v $(pwd)/rover_ws:/workspaces/rover_ws rover-dev`

## Conventions

- Dockerfile naming: lowercase `dockerfile.<target>` prefix style (not
  suffix or per-folder), so all three sort together and stay visible at a
  glance. Case matters on Linux — `Dockerfile.dev` will NOT match the
  actual `docker/dockerfile.dev` file.
- `dockerfile.dev` and `dockerfile.jetson` expect a bind-mounted workspace
  (`-v` at `docker run` time, `$ROS_WS` = `/workspaces/rover_ws`) for live
  edits during development.
- `dockerfile.basestation` expects a deliberate `COPY` of tested code, not a
  bind mount — this is what enforces its stability.
