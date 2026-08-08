# Space Bulls Rover Software

This repository contains the primary ROS 2 workspace for the University at Buffalo Space Bulls rover.

The rover software is built around **ROS 2 Jazzy** and is designed to run across the rover's onboard NVIDIA Jetson computers, the base station, and development machines.

This README is intended to provide a high-level overview of the software architecture: **what technologies we use, what each one is responsible for, and where different parts of the system should run.**

For installation guides, tutorials, development setup instructions, and other educational material, see the **Space Bulls Resources repository**.

---

## Software Stack

### ROS 2 Jazzy

**ROS 2 Jazzy** is the foundation of the rover software stack.

ROS 2 provides the communication and software framework used to connect the rover's sensors, actuators, autonomy systems, operator controls, and other software components.

All primary rover computers use ROS 2 Jazzy, including:

* Onboard Jetson computers
* Base station computers
* Development environments

Individual ROS 2 packages within this workspace should generally be responsible for one subsystem or well-defined software function.

---

### Zenoh

**Zenoh** is used as the rover's ROS 2 middleware through the Zenoh RMW implementation.

It is responsible for transporting ROS 2 messages between processes and computers throughout the rover system.

Zenoh handles communication between systems such as:

* Onboard computers
* Base station
* Sensors and perception nodes
* Control systems
* Operator interfaces

In general:

**If ROS 2 nodes need to communicate with each other, Zenoh handles the underlying transport.**

---

### Isaac ROS

**Isaac ROS** provides GPU-accelerated perception capabilities using NVIDIA Jetson hardware.

It is used for computationally intensive perception workloads such as:

* Visual SLAM
* Depth processing
* Image processing
* Point cloud processing
* nvblox
* Other GPU-accelerated perception pipelines

Isaac ROS runs **on the rover's Jetson computers only** because it relies on NVIDIA's Jetson/Tegra GPU platform.

Because JetPack 7.2 support is relatively recent, individual Isaac ROS packages should be validated on the team's specific Jetson and JetPack configuration before being incorporated into the rover's production software.

---

### Nav2

**Nav2** is responsible for autonomous rover navigation.

Nav2 provides tools for:

* Path planning
* Path following
* Obstacle avoidance
* Localization integration
* Costmaps
* Autonomous navigation behaviors

In general:

**If the rover needs to determine how to drive from one location to another, that functionality belongs within or interfaces with Nav2.**

Perception systems provide information about the environment, while Nav2 uses that information to make navigation decisions.

---

### MoveIt 2

**MoveIt 2** is responsible for motion planning for the rover's robotic arm and manipulators.

MoveIt handles tasks such as:

* Arm trajectory planning
* Kinematics
* Collision checking
* Manipulator planning
* End-effector positioning

In general:

**If the rover needs to determine how the arm should move from one pose to another, that functionality belongs within or interfaces with MoveIt 2.**

MoveIt determines the desired motion, while the lower-level control system is responsible for actually commanding the motors.

---

### ros2_control

**ros2_control** provides the hardware abstraction and low-level control framework for the rover's actuators.

It provides the interface between ROS 2 software and physical hardware such as:

* Drive motors
* Arm motors
* Steering actuators
* Motor controllers
* Encoders
* Other controllable mechanisms

ros2_control separates higher-level software from the details of individual motor controllers and hardware interfaces.

For example:

```text
MoveIt 2
    ↓
ros2_control
    ↓
Motor Controller
    ↓
Arm Motor
```

or:

```text
Nav2
    ↓
Drive Controller
    ↓
ros2_control
    ↓
Motor Controller
    ↓
Drive Motor
```

In general:

**If software needs to directly command or receive feedback from an actuator, it should interface through ros2_control whenever practical.**

---

# Docker Environments

The software stack is distributed using three primary Docker environments.

Each environment serves a different role in the rover system.

## Onboard Jetson Image

The **Jetson image** is used on the rover's NVIDIA Jetson computers.

It contains software required for onboard rover operation, including:

* ROS 2 Jazzy
* Zenoh RMW
* Isaac ROS
* Perception dependencies
* Hardware interfaces
* Rover runtime packages

This environment is optimized around the NVIDIA Jetson platform and may contain Jetson-specific CUDA, GPU, and Isaac ROS dependencies.

**Use this image for software that runs physically onboard the rover.**

---

## Base Station Image

The **base station image** contains software used by the operator station.

This may include:

* ROS 2 Jazzy
* Zenoh RMW
* Rover communication tools
* Operator interfaces
* Teleoperation
* Visualization
* Diagnostics
* Mission control software

The base station should not depend on Jetson-specific GPU libraries unless there is a specific reason to do so.

**Use this image for software that runs on the computers controlling or monitoring the rover remotely.**

---

## Development Image

The **development image** provides a consistent environment for writing, building, testing, and simulating rover software.

It contains the common development dependencies required by team members.

The development environment may include:

* ROS 2 Jazzy
* Zenoh RMW
* Build tools
* Testing tools
* Simulation tools
* Debugging tools
* Development dependencies

The goal of this image is to allow team members to develop against a consistent software environment regardless of their personal computer configuration.

**Use this image when writing and testing rover software.**

Hardware-specific functionality may still require testing using the Jetson or other physical rover hardware.

---

# Where Does Something Belong?

A general guide for determining where software functionality belongs:

| Task                                 | Primary System                                |
| ------------------------------------ | --------------------------------------------- |
| Communication between ROS 2 nodes    | ROS 2 + Zenoh                                 |
| GPU perception                       | Isaac ROS                                     |
| Camera and depth processing          | Isaac ROS / ROS 2 perception packages         |
| Mapping                              | Isaac ROS / nvblox                            |
| Visual localization / VSLAM          | Isaac ROS                                     |
| Autonomous driving                   | Nav2                                          |
| Path planning                        | Nav2                                          |
| Obstacle avoidance                   | Nav2                                          |
| Arm motion planning                  | MoveIt 2                                      |
| Arm kinematics                       | MoveIt 2                                      |
| Collision-aware manipulator planning | MoveIt 2                                      |
| Motor commands                       | ros2_control                                  |
| Encoder feedback                     | ros2_control hardware interfaces              |
| Physical hardware integration        | ros2_control / device-specific ROS 2 packages |
| Rover-to-base-station communication  | ROS 2 + Zenoh                                 |
| Operator controls                    | Base station ROS 2 packages                   |
| Visualization and monitoring         | Base station                                  |
| Software development and testing     | Development Docker image                      |
| GPU-specific runtime software        | Jetson Docker image                           |

---

# High-Level Architecture

The rover software can be thought of as several layers:

```text
                    Operator / Mission Control
                           Base Station
                               │
                               │
                            Zenoh
                               │
                               ▼
                   ┌─────────────────────┐
                   │      ROS 2 Jazzy    │
                   │                     │
                   │   Rover Software    │
                   └─────────────────────┘
                      │              │
              ┌───────┘              └────────┐
              ▼                               ▼
         Perception                       Autonomy
        Isaac ROS                           Nav2
              │                               │
              └──────────────┬────────────────┘
                             │
                             ▼
                       Motion / Control
                    MoveIt 2 / ros2_control
                             │
                             ▼
                         Hardware
```

The exact architecture will continue to evolve as rover systems are developed and integrated.

---

# General Design Philosophy

When adding software to the rover:

* Prefer existing ROS 2 standards and interfaces over custom solutions when possible.
* Keep hardware-specific code separated from higher-level autonomy and planning logic.
* Use ros2_control as the primary abstraction between actuators and higher-level software.
* Keep Jetson-specific dependencies isolated to the onboard environment.
* Avoid requiring Jetson-specific software on the base station or normal development machines.
* Keep ROS 2 packages focused on clearly defined responsibilities.
* Design nodes and packages so individual systems can be tested independently.
* Use Docker environments to maintain consistent dependencies across team members and rover computers.

---

# Additional Resources

Setup instructions, tutorials, development guides, ROS 2 educational material, and team documentation are maintained separately in the **Space Bulls Resources repository**.

This repository should primarily contain software required to build, test, and operate the rover.
