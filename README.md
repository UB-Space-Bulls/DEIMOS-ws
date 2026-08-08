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

**Zenoh** is used as the ROS 2 RMW/messaging layer between the base station and rover.

It provides the underlying transport for ROS 2 topics, services, and actions across the rover network.

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

In general:

> If software needs to command or receive feedback from an actuator, it should interface through ros2_control whenever practical.

---

### Isaac ROS

**Isaac ROS** provides GPU-accelerated perception on the rover's NVIDIA Jetson computers.

Potential uses include:

- Visual SLAM
- Depth processing
- Point-cloud processing
- nvblox
- Image-processing pipelines
- Other GPU-accelerated perception workloads

Isaac ROS is **Jetson-only** in our architecture because it relies on the NVIDIA Jetson/Tegra GPU platform.

Package-by-package validation for the team's **Orin + JetPack 7.2** configuration remains an open hardware-validation item. Isaac ROS components should be confirmed on the actual Jetson hardware before being treated as production-ready.

---

# Simulation

We use two simulation tools for different purposes.

## Gazebo

**Gazebo is the team's primary simulation environment.**

It is intended to be CPU-friendly and broadly available to developers for developing and testing:

- Nav2
- MoveIt 2
- ros2_control
- Mission logic
- Robot descriptions and transforms
- General ROS 2 integration

Gazebo should be the default simulator for normal rover software development and should not require NVIDIA GPU hardware.

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
| `Dockerfile.jetson` | ARM64 | Onboard rover environment; full runtime stack including Isaac ROS |
| `Dockerfile.basestation` | x86_64 | Stable ground-control environment; protected from casual development changes |
| `Dockerfile.dev` | x86_64 | Portable development environment for Jetson-bound code; safe to modify and break during development |

The **development image is currently built**.

For more detail about the Docker environments and what should transfer between them, see [`docker/README.md`](docker/README.md).

---

# Where Does Something Belong?

| Task | Primary System |
|---|---|
| ROS 2 framework | ROS 2 Jazzy |
| Rover ↔ base-station messaging | Zenoh RMW |
| Autonomous driving | Nav2 |
| Path planning | Nav2 |
| Obstacle avoidance | Nav2 |
| Arm motion planning | MoveIt 2 |
| Arm kinematics | MoveIt 2 |
| Collision-aware manipulator planning | MoveIt 2 |
| Motor commands | ros2_control |
| Encoder / actuator feedback | ros2_control hardware interfaces |
| Physical hardware integration | ros2_control / device-specific ROS 2 packages |
| GPU-accelerated perception | Isaac ROS on Jetson |
| General simulation | Gazebo |
| Synthetic perception data | Isaac Sim, optional |
| Operator controls | Base-station ROS 2 packages |
| Software development and testing | Development Docker image |

---

# High-Level Architecture

```text
                     Operator / Mission Control
                            Base Station
                                │
                              Zenoh
                                │
                                ▼
                       ROS 2 Jazzy Rover
                 ┌──────────────┴──────────────┐
                 │                             │
                 ▼                             ▼
           Perception                      Autonomy
           Isaac ROS                         Nav2
          (Jetson only)                       │
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
- Keep Isaac ROS out of environments that do not require Jetson GPU acceleration.
- Use Gazebo as the default team-wide simulator.
- Treat Isaac Sim as an optional perception tool rather than a required dependency.
- Keep ROS 2 packages focused on clearly defined responsibilities.
- Design nodes and packages so individual systems can be tested independently.
- Use Docker environments to maintain consistent dependencies across team members and rover computers.

---

# Additional Resources

Setup instructions, tutorials, development guides, ROS 2 educational material, and team documentation are maintained separately in the **Space Bulls Resources repository**.

This repository should primarily contain software required to build, test, and operate the rover.