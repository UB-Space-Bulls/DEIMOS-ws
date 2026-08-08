# Docker Environments

This directory contains the Docker environments used to build, test, and run Space Bulls rover software.

We maintain three primary images:

- **`dockerfile.dev`** — x86_64 development environment for Jetson-bound source code. This is the environment team members should normally use while writing, building, testing, and simulating software. It is intentionally safe to modify and break during development.
- **`dockerfile.basestation`** — x86_64 base-station environment for stable ground-control software. This image should remain comparatively stable and should be protected from casual development changes.
- **`dockerfile.jetson`** — ARM64 onboard environment for NVIDIA Jetson Orin computers. This contains the rover runtime stack, Jetson-specific dependencies, and any Isaac ROS packages that have been validated on the team's hardware.

The **development image is currently built**. The base-station and Jetson images remain part of the target architecture and should be brought online as their runtime requirements are finalized.

## Building and Running the Development Image

Run from the repo root:

```bash
docker build -f docker/dockerfile.dev -t rover-dev .
docker run -it --rm -v $(pwd)/rover_ws:/workspaces/rover_ws rover-dev
```

The `-v` bind mount maps the local `rover_ws` into the container so edits made outside the container are reflected inside it live.

## Verifying the Setup

Once you're in the container (`ros_entrypoint.sh` has already sourced `/opt/ros/jazzy/setup.bash` for you), run these to confirm the environment is actually ready before you start developing:

```bash
# ROS 2 is installed and on the right distro
ros2 --version
echo $ROS_DISTRO   # should print: jazzy

# Zenoh RMW is active (not the default DDS implementation)
echo $RMW_IMPLEMENTATION   # should print: rmw_zenoh_cpp

# Nav2 / MoveIt 2 / ros2_control packages installed correctly
ros2 pkg list | grep -E "nav2_bringup|moveit_ros|ros2_control"

# Full environment sanity check
ros2 doctor
```

Then confirm pub/sub actually works end-to-end. Open a second terminal into the same running container (`docker exec -it <container_id_or_name> bash`) and run one command in each:

```bash
# Terminal 1
ros2 run demo_nodes_cpp talker

# Terminal 2
ros2 run demo_nodes_py listener
```

The listener should start printing `I heard: [Hello World: N]` messages from the talker. If it does, Zenoh discovery and ROS 2 communication are both working inside the container. `Ctrl+C` both to stop.

## Why `dev` and `jetson` Bind-Mount the Workspace

`dockerfile.dev` and `dockerfile.jetson` both mount `rover_ws` from the host at `docker run` time instead of `COPY`-ing it into the image. The image only provides the OS, ROS 2 Jazzy, and the rest of the toolchain — the actual rover source lives outside the container and is attached live.

The practical effect: team members build the image **once**, then just re-run the container to pick up code changes in `rover_ws`. A rebuild is only needed when the *Dockerfile itself* changes — new system/apt packages, a different base image tag, etc. — not for ordinary source edits.

`dockerfile.basestation` intentionally works the other way: it `COPY`s tested code into the image rather than bind-mounting it, so ground-control software only updates through a deliberate, reviewed rebuild instead of live edits.

---

For the shared ROS 2 software stack (Zenoh, Nav2, MoveIt 2, ros2_control, Isaac ROS) and the Zenoh network topology, see the top-level [`README.md`](../README.md). The rest of this document covers Docker-specific details: what transfers between the development and Jetson environments, and how platform-specific code should be structured.

---

# What Transfers From Development to Jetson?

A major goal of this architecture is for most rover software to be developed and tested in `dockerfile.dev`, then built and run in `dockerfile.jetson` with little or no **source-code** change.

As a general rule:

> Software that talks to ROS 2 topics, services, actions, and standard interfaces should be portable. Software that talks directly to hardware or platform-specific libraries may not be.

## Important: Source Transfers, Build Artifacts Do Not

The development image is **x86_64**, while the Jetson image is **ARM64**.

That means source code and configuration should transfer between the two environments, but compiled x86_64 binaries and `colcon` build artifacts should not be copied to the Jetson and expected to run.

The intended model is:

```text
                Same Rover Source
                      │
             ┌────────┴────────┐
             │                 │
     dockerfile.dev      dockerfile.jetson
          x86_64               ARM64
             │                 │
       colcon build       colcon build
             │                 │
      x86_64 binaries      ARM64 binaries
```

Each target environment should build the rover source for its own CPU architecture.

## Usually Transfers With Little or No Source Change

The following should generally transfer cleanly from the development environment to the Jetson:

- **Nav2 configuration**
  - Costmap parameters
  - Planner parameters
  - Controller parameters
  - Behavior configuration
  - Launch files
- **MoveIt 2 configuration**
  - SRDF
  - Planning groups
  - Kinematics configuration
  - Planning parameters
  - Launch files
- **ros2_control controller definitions**
  - Controller YAML files
  - Controller configuration
  - Controller gains
  - Portable controller logic
- **Custom ROS 2 nodes** for:
  - Mission logic
  - Autonomy
  - State machines
  - Decision-making
  - Coordination between subsystems
- **Message, service, and action definitions**
- **Zenoh RMW configuration**
- **Launch files** that do not depend on machine-specific hardware
- **Parameter files** that do not contain machine-specific paths or device identifiers
- **Unit tests** for the above software

These components should depend on ROS interfaces rather than on the specific computer they happen to run on.

---

## Requires Jetson-Specific Validation or Integration

Some software depends directly on the onboard hardware or NVIDIA software stack and therefore cannot be assumed to transfer without validation.

Examples include:

- **Isaac ROS packages and pipelines**
- CUDA- or GPU-dependent software
- Jetson/Tegra-specific libraries
- Camera drivers that require physical devices
- CAN interfaces
- Serial devices
- USB device mappings
- Motor-controller drivers
- IMU and encoder hardware interfaces
- ros2_control hardware-interface plugins
- GPIO or other direct hardware access
- Device-specific udev rules
- Machine-specific networking or device configuration

These components may still share source code with the development environment, but they must be built and tested in the Jetson image with the actual hardware and runtime dependencies.

---

# Simulation

Gazebo Harmonic is the default simulator and runs inside the development image — see the top-level [`README.md`](../README.md) for the full simulation strategy (Gazebo Harmonic vs. optional Isaac Sim).

A major goal is to keep the control structure similar between simulation and hardware:

```text
Higher-Level ROS 2 Software
          ↓
      ros2_control
          ↓
   ┌──────┴──────┐
   │             │
Simulation     Rover
   │             │
gz_ros2_control  Real Hardware Interface
   │             │
Gazebo Harmonic  Motors / Sensors
```

---

# Keep Platform Differences Out of ROS Logic

Whenever possible, rover software should be structured so platform-specific details remain at the edges of the system.

For example:

```text
Mission / Autonomy Node
        ↓
     ROS 2 Topic
        ↓
ros2_control Controller
        ↓
 Hardware Interface
        ↓
 CAN / Motor Controller
```

The mission node should not need to know whether the motor controller is connected through CAN, USB, or another physical interface. That responsibility belongs to the hardware layer.

Similarly:

```text
Navigation Logic
        ↓
      Nav2
        ↓
   ROS 2 Interfaces
        ↓
Drivetrain Controllers
```

This separation allows higher-level software to be developed and tested without requiring the physical rover.

---

# Intended Development Workflow

```text
Develop source in dockerfile.dev
        ↓
Build and test for x86_64
        ↓
Test ROS interfaces in Gazebo Harmonic / unit tests
        ↓
Use the same rover source in dockerfile.jetson
        ↓
Rebuild for ARM64
        ↓
Validate hardware- and GPU-specific behavior on rover
```

The Docker images provide different environments, but they should use the **same rover source packages whenever practical**.

Avoid maintaining separate "development code" and "Jetson code" versions of the same ROS 2 node. Platform differences should instead be handled through dependencies, configuration, launch files, or hardware-interface layers.

---

# General Rule

When deciding where something belongs, ask:

**Does this code care what computer or physical device it is running on?**

If **no**, it should probably be portable between development, base station, and/or Jetson environments.

If **yes**, the machine-specific dependency should be isolated to the appropriate Docker image or hardware-interface layer.