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

- **ROS 2 Jazzy** across the entire system — Jetson, base station, and dev
  environment. (Chosen over Humble because Jazzy has a longer support window,
  runs on the current Ubuntu LTS, and JetPack 7.2 added Ubuntu 24.04 support
  for the Orin family, closing the gap that used to force Humble on Jetson.)
- **Zenoh** as the RMW/middleware layer connecting the base station and rover.
- **Nav2** for navigation and path planning.
- **MoveIt 2** for arm/manipulator motion planning.
- **ros2_control** for the hardware abstraction layer driving actuators.
- **Isaac ROS** for GPU-accelerated perception (VSLAM, nvblox, object
  detection, etc.) — Jetson-only, since it needs the Tegra GPU.

## ROS 2 packages in this repo (`rover_ws/src/`)

- **`rover_description`** — the real chassis package: placeholder
  box/cylinder swerve geometry, `ros2_control` wiring, Gazebo Harmonic
  world, and controller config. This is what Nav2/sim/mission work should
  build against.
- **`rover_swerve_controller`** — the custom inverse-kinematics node
  (`swerve_kinematics_node.py`) that converts `/cmd_vel` into per-module
  steer-angle + wheel-speed commands, since no stock `ros2_controllers`
  swerve plugin exists.
- **`rover_test_description`** — preliminary/dev-only package holding a
  CAD-derived (SolidWorks-to-URDF export) version of the chassis: real
  meshes and swerve topology, rewired for Gazebo Harmonic/`gz_ros2_control`
  and renamed to the `front_left`/`front_right`/`rear_left`/`rear_right`
  convention. Kept separate from `rover_description` — its geometry hasn't
  been folded into the real package yet. Launch `display.launch.py` (RViz)
  or `gazebo.launch.py` (Gazebo) to eyeball the CAD model.

## Hardware

- **Jetson Orin** (Nano/NX/AGX) on the rover, running **JetPack 7.2**
  (Jetson Linux 39.2, Ubuntu 24.04, kernel 6.8).
- Physical hardware expected to be available for testing by **early December**.

### Known open item
Isaac ROS 4.0 (the Jazzy-compatible release) was originally validated for
Jetson Thor. JetPack 7.2 added Orin *OS-level* support (Ubuntu 24.04), but
package-level validation of specific GPU-accelerated Isaac ROS packages on
the Orin + JetPack 7.2 combination should be re-checked against
https://nvidia-isaac-ros.github.io before relying on any one package in
competition-critical code paths.

## SLAM strategy

Rover has both **lidar** and a **stereo camera**. SLAM plan uses both
sensors across two implementations, both running on ROS 2 Jazzy — this is
NOT an "Isaac ROS vs. Jazzy" choice, both options are Jazzy underneath:

- **`slam_toolbox`** (lidar-based, CPU-only, no Isaac ROS dependency) —
  build this FIRST, starting in the Aug–Nov portable dev window, in Gazebo.
  Mature, battle-tested, natively integrated with Nav2. Fully decoupled
  from the Orin/JetPack 7.2 Isaac ROS validation risk. Caveat: fundamentally
  2D SLAM, assumes largely planar motion — may not handle rough
  Mars-analog terrain as gracefully as full 3D VSLAM.
- **Isaac ROS VSLAM** (`isaac_ros_visual_slam`, stereo-camera-based,
  GPU-accelerated) — the more capable option if it works, since it's
  better suited to uneven terrain. Requires validation on real hardware.

**Go/no-go plan:**
1. Aug–Nov: build and tune `slam_toolbox` in Gazebo as part of normal
   portable dev work — real, usable SLAM, not a backup sitting idle.
2. Early Dec (hardware arrives): time-boxed validation of Isaac ROS VSLAM
   on the actual Orin + JetPack 7.2 combo — does it work, at acceptable
   performance, on this specific hardware/software combination.
3. **Go** → Isaac ROS VSLAM becomes primary; `slam_toolbox` stays available
   as a proven fallback.
   **No-go** → keep using `slam_toolbox`, already tuned and integrated
   from the fall — no scrambling required.

Design the SLAM node as a swappable component — Nav2/costmap pipeline
should consume standard `/map` and `/odom` topics rather than anything
Isaac-ROS-specific baked in throughout the codebase, so switching between
the two implementations later is a small change, not a rearchitecture.

(RTAB-Map, which fuses lidar + stereo together, is a third option worth
knowing about if either sensor alone proves insufficient on rough terrain —
more setup complexity than `slam_toolbox` alone, not currently the plan.)

## Docker architecture — three images, three jobs

Filenames are lowercase (`dockerfile.<target>`, not `Dockerfile.<target>`) —
match the case exactly in build commands on Linux.

1. **`docker/dockerfile.jetson`** — ARM64, `FROM ${BASE_IMAGE}` (default
   `nvcr.io/nvidia/l4t-jetpack:r39.2.0`). Runs onboard the rover. Full stack
   including Isaac ROS GPU perception. Will NOT run on a laptop —
   Tegra-specific drivers baked in. **Verify the exact `l4t-jetpack` tag
   exists on NGC before building** — NGC images have historically lagged
   Jetson Linux releases by weeks.

2. **`docker/dockerfile.basestation`** — x86_64, `FROM ros:jazzy-desktop`.
   The actual ground-control software that runs during competition: RViz2,
   teleop, monitoring. This is the STABLE image — treat changes here as
   deliberate and reviewed, not casual experimentation. GUI/monitoring
   approach is still TBD; current file has a placeholder teleop/rqt setup.

3. **`docker/dockerfile.dev`** — x86_64, `FROM ros:jazzy-ros-base`.
   Portable dev environment for writing/testing Jetson-bound code (Nav2,
   MoveIt 2, ros2_control, non-GPU logic) on any laptop, GPU or not.
   Deliberately excludes Isaac ROS GPU packages. Safe to break — this is
   isolated from `dockerfile.basestation` specifically so experimentation
   here can't accidentally affect working ground-control code.

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

NOT portable, needs real Jetson time regardless: ros2_control hardware
interface plugins (talk to real motor controllers over CAN/serial), camera/
sensor drivers (Tegra-specific Argus/ISP pipeline), Isaac ROS GPU perception
nodes, sensor calibration, real-time tuning under actual thermal/power
constraints.

## Simulation strategy

- **Gazebo Harmonic** — default sim for the whole team. Validates Nav2,
  MoveIt 2, ros2_control (via `gz_ros2_control`), and mission logic. Runs
  on any laptop, CPU-only is fine. Native ROS 2 integration means launch
  files and params carry over unchanged to real code. `gz_ros2_control`
  keeps the simulated hardware interface swappable for the real one
  without touching controller definitions.
- **Isaac Sim** — optional, situational, GPU-gated. Two real uses:
  1. **Perception verification** — stress-tests whether perception nodes
     (object/waypoint detection, VSLAM) correctly interpret realistic,
     photorealistic camera input. Gazebo's simplified rendering doesn't
     meaningfully challenge a perception model the way Isaac Sim's
     RTX-rendered output does.
  2. **Synthetic training data** — Isaac Sim's Replicator framework can
     generate large labeled datasets via domain randomization (varied
     lighting/angle/texture), useful for pretraining an object/waypoint
     detector before real-world footage exists.
  Not needed team-wide; only relevant to whoever works on perception, and
  only if/when Gazebo's camera simulation proves insufficient.

Neither simulator is part of what ships to competition — both are dev-time
tools. The real rover does NOT run a simulation before every movement;
Nav2/MoveIt 2 compute trajectories via planning algorithms checked against
real sensor data and constraints, not by rehearsing in a simulator live.

## Timeline (Aug–Feb)

- **Aug–Nov**: portable dev work (Gazebo setup, Nav2/MoveIt2/ros2_control
  configs, base station GUI, Zenoh bridge, mission logic) — parallelizable
  across the team, any laptop.
- **Early Dec**: hardware arrives. Flash JetPack 7.2, verify Docker + GPU
  passthrough on the real Jetson.
- **Dec–mid Jan**: hardware integration — ros2_control hardware interfaces,
  real camera/perception validation, sensor calibration. Highest-risk phase;
  budget extra time here. Note: this window likely overlaps winter break/
  finals — decide explicitly whether integration work continues (even
  partially, remote) over break, since that affects how much buffer is
  actually available.
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
