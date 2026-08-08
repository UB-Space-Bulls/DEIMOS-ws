# Docker Environments

This directory contains the Docker environments used to build, test, and run Space Bulls rover software.

We maintain three primary images:

- **Development** — used by team members to write, build, test, and simulate rover software.
- **Base Station** — used for software that runs on the operator/base-station computer.
- **Jetson** — used for software that runs onboard the rover's NVIDIA Jetson computers.

The goal is to keep the ROS 2 software itself as portable as possible while separating machine-specific dependencies into the appropriate Docker image.

## Directory Layout

```text
docker/
├── dev/
│   └── Dockerfile
├── basestation/
│   └── Dockerfile
├── jetson/
│   └── Dockerfile
└── README.md
```

The exact contents of each image will evolve as the rover software stack develops.

---

## Development Image

The development image provides a consistent environment for writing and testing rover software.

It should contain the common tools and dependencies needed by developers, such as:

- ROS 2 Jazzy
- Zenoh RMW
- ROS 2 build tools
- Testing and debugging tools
- Simulation dependencies
- Common rover software dependencies

The development image should avoid depending on Jetson-specific hardware or NVIDIA Tegra libraries unless they are specifically required for a development workflow.

**Use this image for normal software development.**

---

## Base Station Image

The base-station image contains software required by the rover operator station.

This may include:

- ROS 2 Jazzy
- Zenoh RMW
- Teleoperation nodes
- Operator interfaces
- Visualization and diagnostics
- Mission-control software
- Base-station launch files and configuration

The base station should generally remain independent of Jetson-specific libraries.

**Use this image for software that runs on the operator computer.**

---

## Jetson Image

The Jetson image contains software that runs onboard the rover's NVIDIA Jetson computers.

This includes the common ROS 2 stack plus hardware- and GPU-specific dependencies such as:

- ROS 2 Jazzy
- Zenoh RMW
- Isaac ROS
- NVIDIA / Jetson runtime dependencies
- Hardware interfaces
- Sensor drivers
- Rover runtime packages

This is where software that directly depends on the Jetson platform, onboard sensors, GPU acceleration, or physical rover hardware should be validated and run.

**Use this image for software running physically onboard the rover.**

---

# What Transfers From Development to Jetson?

A major goal of this architecture is for most rover software to be developed and tested in the development image, then moved to the Jetson environment with little or no code change.

As a general rule:

> Software that talks to ROS 2 topics, services, actions, and standard interfaces should be portable. Software that talks directly to hardware or platform-specific libraries may not be.

## Usually Transfers With Little or No Change

The following should generally transfer cleanly from the development environment to the Jetson:

- **Nav2 configuration** — costmap, planner, controller, behavior, and other parameter files
- **Nav2 launch files**
- **MoveIt 2 configuration** — SRDF, planning groups, kinematics configuration, planning parameters, and launch files
- **ros2_control controller definitions** — controller YAML files, controller configuration, and portable controller logic
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

These components should be written so that their behavior depends on ROS interfaces rather than the specific computer they happen to run on.

---

## May Require Jetson-Specific Changes or Validation

Some software cannot be treated as completely portable because it depends on the onboard hardware or NVIDIA software stack.

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

These components may still share source code with the development environment, but they must be tested in the Jetson container with the actual hardware and runtime dependencies.

---

# Keep Platform Differences Out of ROS Logic

Whenever possible, rover software should be structured so that platform-specific details remain at the edges of the system.

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

# Development Workflow

The intended workflow is approximately:

```text
Develop in dev image
        ↓
Build and test
        ↓
Test ROS interfaces / simulation
        ↓
Run the same rover packages in Jetson image
        ↓
Validate hardware-specific behavior on rover
```

The Docker images provide different environments, but they should run the **same rover source packages whenever practical**.

Avoid maintaining separate "development code" and "Jetson code" versions of the same ROS 2 node. Platform differences should instead be handled through dependencies, configuration, launch files, or hardware-interface layers.

---

# General Rule

When deciding where something belongs, ask:

**Does this code care what computer or physical device it is running on?**

If **no**, it should probably be portable between development, base station, and/or Jetson environments.

If **yes**, the machine-specific dependency should be isolated to the appropriate Docker image or hardware-interface layer.