# Docker Environments

This directory contains the Docker environments used to build, test, and run Space Bulls rover software.

We maintain three primary images:

- **`dockerfile.dev`** — x86_64 development environment for Jetson-bound source code. This is the environment team members should normally use while writing, building, testing, and simulating software. It is intentionally safe to modify and break during development.
- **`dockerfile.basestation`** — x86_64 base-station environment for stable ground-control software. This image should remain comparatively stable and should be protected from casual development changes.
- **`dockerfile.jetson`** — ARM64 onboard environment for NVIDIA Jetson Orin computers. This contains the rover runtime stack, Jetson-specific dependencies, and any Isaac ROS packages that have been validated on the team's hardware.

The **development image is currently built**. The base-station and Jetson images remain part of the target architecture and should be brought online as their runtime requirements are finalized.

---

## Software Shared Across Environments

The project uses **ROS 2 Jazzy** across all three environments:

- Jetson, through JetPack 7.2 on NVIDIA Orin hardware
- Base station
- Development environment

Other major shared components include:

- **Zenoh through `rmw_zenoh_cpp`** as the ROS 2 RMW/messaging layer between the base station and rover
- **Nav2** for navigation and path planning
- **MoveIt 2** for manipulation and arm motion planning
- **ros2_control** for controller definitions, hardware abstraction, and low-level actuator control

**Isaac ROS is experimental in the current Space Bulls architecture.** The team intends to use it only in the Jetson environment for GPU-accelerated perception, but individual packages must be validated on the exact Orin + JetPack 7.2 configuration before they are treated as production-ready. Core rover operation should not depend on Isaac ROS until that validation is complete.

---

# Zenoh Deployment

Zenoh networking should be deliberately configured rather than treated as an invisible implementation detail.

ROS 2 nodes use `rmw_zenoh_cpp`, which connects them into the Zenoh network. The rover and base station should use a defined router/client topology with version-controlled configuration.

A simplified topology is:

```text
Base Station ROS 2 Nodes
        ↓
   rmw_zenoh_cpp
        ↓
  Zenoh Router
        ↓
   Rover Network
        ↓
  Zenoh Router / Client
        ↓
   rmw_zenoh_cpp
        ↓
Rover ROS 2 Nodes
```

The exact router/client arrangement can be adjusted after rover networking tests, but the deployment should remain explicit and reproducible.

Zenoh configuration files should eventually be stored in version control, for example:

```text
config/
└── zenoh/
    ├── basestation.json5
    └── rover.json5
```

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

## Gazebo Harmonic

**Gazebo Harmonic is the primary team-wide simulator.**

It should be broadly usable by developers for testing:

- Nav2
- MoveIt 2
- ros2_control through `gz_ros2_control`
- Mission logic
- Robot descriptions and transforms
- General ROS 2 integration

Gazebo Harmonic should be the default simulator used inside the development environment.

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

## Isaac Sim

**Isaac Sim is optional and GPU-gated.**

Its likely future uses include:

- Synthetic training data generation
- Object-detection dataset generation
- Waypoint-detection dataset generation
- Perception verification
- More advanced photorealistic simulation

Isaac Sim is **not required for the current development workflow and is not blocking the software stack**. It should be revisited later when perception development can benefit from it.

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