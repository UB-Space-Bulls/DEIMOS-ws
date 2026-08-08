# Space Bulls Rover Software

This repository contains the primary ROS 2 workspace for the University at Buffalo Space Bulls rover.

The rover software is built around **ROS 2 Jazzy** and is designed to run across the rover's onboard NVIDIA Jetson computers, the base station, and development machines.

This README provides a high-level overview of the software architecture: **what technologies we use, what each one is responsible for, and where different parts of the system should run.**

For installation guides, tutorials, development setup instructions, and other educational material, see the **Space Bulls Resources repository**.

---

## Software Stack

### ROS 2 Jazzy

**ROS 2 Jazzy** is the foundation of the rover software stack and is used everywhere:

- Onboard NVIDIA Jetson Orin computers via JetPack 7.2
- Base station computers
- Development environments

ROS 2 provides the framework used to connect the rover's sensors, actuators, autonomy systems, operator controls, and other software components.

---

### Zenoh

**Zenoh** is used through `rmw_zenoh_cpp` as the ROS 2 RMW/messaging layer between the base station and rover.

It provides the underlying transport for ROS 2 topics, services, and actions across the rover network.

Zenoh deployment is an explicit part of the rover network architecture. The rover and base station will use a configured Zenoh router/client topology rather than relying on implicit discovery behavior. Router and endpoint configuration should be kept in version-controlled configuration files so the network can be reproduced consistently.

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

The final router topology may change as networking is tested on the rover, but it should remain deliberately configured.

In general:

> If ROS 2 nodes on different computers need to communicate, Zenoh handles the underlying transport.

---

### Nav2

**Nav2** is responsible for autonomous rover navigation.

It provides functionality such as:

- Path planning
- Path following
- Costmaps
- Obstacle avoidance
- Localization integration
- Autonomous navigation behaviors

In general:

> If the rover needs to determine how to drive from one location to another, that functionality belongs within or interfaces with Nav2.

---

### MoveIt 2

**MoveIt 2** is responsible for robotic arm and manipulator motion planning.

It provides functionality such as:

- Arm trajectory planning
- Kinematics
- Collision checking
- Manipulator planning
- End-effector positioning

In general:

> If the rover needs to determine how the arm should move from one pose to another, that functionality belongs within or interfaces with MoveIt 2.

---

### ros2_control

**ros2_control** provides the hardware abstraction and low-level control framework for rover actuators.

It provides the interface between higher-level ROS 2 software and hardware such as:

- Drive motors
- Arm motors
- Motor controllers
- Encoders
- Other controllable mechanisms

A typical control path looks like:

```text
MoveIt 2 / Nav2
       ↓
ros2_control
       ↓
Hardware Interface
       ↓
Motor Controller
       ↓
Physical Actuator
```

In simulation, the hardware layer can instead be provided through `gz_ros2_control` so the same controller configuration and higher-level software can be exercised against Gazebo Harmonic.

In general:

> If software needs to command or receive feedback from an actuator, it should interface through ros2_control whenever practical.

---

### Isaac ROS

**Isaac ROS is an experimental component of the current Space Bulls stack.**

Space Bulls intends to use Isaac ROS only in the onboard Jetson environment for GPU-accelerated perception workloads such as:

- Visual SLAM
- Depth processing
- Point-cloud processing
- nvblox
- Image-processing pipelines
- Other GPU-accelerated perception workloads

The team's **Orin + JetPack 7.2** configuration is relatively new and must be validated package-by-package on the actual Jetson hardware before Isaac ROS is treated as production-ready.

The rover architecture should therefore **not depend on Isaac ROS being available for core rover operation**. Isaac ROS should remain optional until the required packages have been validated and shown to be reliable on the team's hardware.

---

# Simulation

We use two simulation tools for different purposes.

## Gazebo Harmonic

**Gazebo Harmonic is the team's primary simulation environment.**

It is intended to be broadly available to developers for developing and testing:

- Nav2
- MoveIt 2
- ros2_control through `gz_ros2_control`
- Mission logic
- Robot descriptions and transforms
- General ROS 2 integration

Gazebo Harmonic should be the default simulator for normal rover software development and should not require NVIDIA Jetson hardware.

---

## Isaac Sim

**Isaac Sim is optional and GPU-gated.**

It may be used later for perception-focused workflows such as:

- Synthetic training data generation
- Object-detection dataset generation
- Waypoint-detection dataset generation
- Perception verification
- More advanced photorealistic simulation

Isaac Sim is **not required for the current development workflow and is not blocking the software stack**. Its role should be revisited when perception development reaches the point where its GPU-heavy capabilities provide clear value.

---

# Docker Architecture

The project uses three Docker images with intentionally different responsibilities.

| Dockerfile | Architecture | Purpose |
|---|---|---|
| `dockerfile.jetson` | ARM64 | Onboard rover runtime environment; Jetson-specific dependencies and experimentally validated Isaac ROS packages |
| `dockerfile.basestation` | x86_64 | Stable ground-control environment; protected from casual development changes |
| `dockerfile.dev` | x86_64 | Portable development environment for Jetson-bound source code; safe to modify and break during development |

The **development image is currently built**.

Because the development and Jetson environments use different CPU architectures, source code and configuration should transfer between them, but compiled x86_64 build artifacts should not. Rover packages must be built for ARM64 inside the Jetson environment.

For more detail about the Docker environments and what should transfer between them, see [`docker/README.md`](docker/README.md).

---

# Where Does Something Belong?

| Task | Primary System |
|---|---|
| ROS 2 framework | ROS 2 Jazzy |
| Rover ↔ base-station messaging | Zenoh / `rmw_zenoh_cpp` |
| Zenoh network topology | Version-controlled Zenoh router/client configuration |
| Autonomous driving | Nav2 |
| Path planning | Nav2 |
| Obstacle avoidance | Nav2 |
| Arm motion planning | MoveIt 2 |
| Arm kinematics | MoveIt 2 |
| Collision-aware manipulator planning | MoveIt 2 |
| Motor commands | ros2_control |
| Encoder / actuator feedback | ros2_control hardware interfaces |
| Physical hardware integration | ros2_control / device-specific ROS 2 packages |
| GPU-accelerated perception | Isaac ROS on Jetson, experimental until validated |
| General simulation | Gazebo Harmonic |
| Simulated ros2_control hardware | `gz_ros2_control` |
| Synthetic perception data | Isaac Sim, optional |
| Operator controls | Base-station ROS 2 packages |
| Software development and testing | Development Docker image |

---

# High-Level Architecture

```text
                     Operator / Mission Control
                            Base Station
                                │
                         rmw_zenoh_cpp
                                │
                          Zenoh Router
                                │
                         Rover Network
                                │
                     Zenoh Router / Client
                                │
                         rmw_zenoh_cpp
                                │
                       ROS 2 Jazzy Rover
                 ┌──────────────┴──────────────┐
                 │                             │
                 ▼                             ▼
           Perception                      Autonomy
           Isaac ROS                         Nav2
        (experimental)                        │
                 │                             │
                 └──────────────┬──────────────┘
                                │
                         MoveIt 2 / Control
                                │
                         ros2_control
                                │
                       Hardware Interfaces
                                │
                             Hardware
```

The exact architecture will continue to evolve as rover systems are developed and integrated.

---

# General Design Philosophy

When adding software to the rover:

- Prefer existing ROS 2 standards and interfaces over custom solutions when possible.
- Keep hardware-specific code separated from higher-level autonomy and planning logic.
- Use ros2_control as the primary abstraction between actuators and higher-level software.
- Keep Jetson-specific dependencies isolated to the onboard environment.
- Treat Isaac ROS as optional and experimental until the required packages are validated on Orin + JetPack 7.2.
- Use Gazebo Harmonic as the default team-wide simulator.
- Use `gz_ros2_control` to keep simulated control interfaces close to the real ros2_control architecture.
- Treat Isaac Sim as an optional perception tool rather than a required dependency.
- Keep ROS 2 packages focused on clearly defined responsibilities.
- Design nodes and packages so individual systems can be tested independently.
- Keep Zenoh router/client configuration version controlled and intentionally deployed.
- Transfer source code and configuration between x86_64 development and ARM64 Jetson environments, then rebuild for the target architecture.
- Use Docker environments to maintain consistent dependencies across team members and rover computers.

---

# Additional Resources

Setup instructions, tutorials, development guides, ROS 2 educational material, and team documentation are maintained separately in the **Space Bulls Resources repository**.

This repository should primarily contain software required to build, test, and operate the rover.