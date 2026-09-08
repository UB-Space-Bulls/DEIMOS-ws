#!/bin/bash
# Starts an interactive rover-isaac-dev container: the throwaway x86_64 GPU
# sandbox for the Isaac ROS VSLAM pull-forward validation (see CLAUDE.md's SLAM
# go/no-go plan and docker/dockerfile.isaac-dev's header).
#
# This is the isaac-dev counterpart to run-dev.sh, but it needs THREE things
# run-dev.sh doesn't:
#   1. --gpus all              -> real CUDA compute, via the NVIDIA Container
#                                 Toolkit. run-dev.sh's `--device /dev/dri` is
#                                 display-only (Mesa/OpenGL for RViz windows)
#                                 and does NOT expose CUDA -- different plumbing.
#   2. USB passthrough         -> the ZED 2 is a raw-USB (libusb) device to the
#                                 ZED SDK, not a plain V4L2 webcam, so the
#                                 container needs /dev/bus/usb plus permission
#                                 to talk to USB character devices.
#   3. NVIDIA_DRIVER_CAPABILITIES=all -> without it the injected driver only
#                                 brings `utility`+`compute`; cuVSLAM and the
#                                 ZED SDK also want `video` (NVDEC) and
#                                 `graphics`.
#
# Usage:
#   ./docker/run-isaac-dev.sh                 # interactive bash in the container
#   ./docker/run-isaac-dev.sh ros2 topic list # run one command and exit
#   PRIVILEGED=1 ./docker/run-isaac-dev.sh    # fall back to --privileged if the
#                                             # targeted USB passthrough below
#                                             # doesn't pick the camera up
#
# Build the image first if you haven't (see dockerfile.isaac-dev header for the
# checkpoint step; this script runs the *full* image):
#   docker build -f docker/dockerfile.isaac-dev -t rover-isaac-dev .
set -e

IMAGE="rover-isaac-dev"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# --- image present? -----------------------------------------------------------
if ! docker image inspect "$IMAGE" > /dev/null 2>&1; then
  echo "error: image '$IMAGE' not found. Build it first:" >&2
  echo "  docker build -f docker/dockerfile.isaac-dev -t $IMAGE ." >&2
  exit 1
fi

# --- NVIDIA Container Toolkit present? ---------------------------------------
# `docker run --gpus all` hard-errors if the toolkit's runtime hook isn't
# installed/configured. Catch it here with a clearer message than the raw
# "could not select device driver" from the daemon.
if ! command -v nvidia-ctk > /dev/null 2>&1 \
   && ! grep -qi nvidia <(docker info 2>/dev/null); then
  echo "error: NVIDIA Container Toolkit doesn't look installed/configured." >&2
  echo "       Without it, --gpus all fails. Install it, then:" >&2
  echo "         sudo nvidia-ctk runtime configure --runtime=docker" >&2
  echo "         sudo systemctl restart docker" >&2
  echo "       Verify: docker run --rm --gpus all ubuntu nvidia-smi" >&2
  exit 1
fi

# --- X11 access grant (same idempotent dance as run-dev.sh) -----------------
if command -v xhost > /dev/null 2>&1; then
  xhost +local:docker > /dev/null
else
  echo "note: xhost not found -- skipping the X11 access grant." >&2
  echo "      Fine on WSL2/WSLg. If ZED_Explorer / RViz windows fail to open," >&2
  echo "      install it: sudo apt install x11-xserver-utils" >&2
fi

DOCKER_ARGS=(
  -it --rm
  --net=host
  --name rover-isaac-dev-container
  --gpus all
  -e NVIDIA_VISIBLE_DEVICES=all
  -e NVIDIA_DRIVER_CAPABILITIES=all
  -e DISPLAY="$DISPLAY"
  -v /tmp/.X11-unix:/tmp/.X11-unix
  -v "${REPO_ROOT}/rover_ws:/workspaces/rover_ws"
  --user "$(id -u):$(id -g)"
  # Point HOME at the bind-mounted, user-owned workspace so ROS (~/.ros/log),
  # colcon, and the ZED SDK (calibration cache) have somewhere writable --
  # otherwise --user with no matching /etc/passwd entry gives them HOME=/ .
  -e HOME=/workspaces/rover_ws
)

# --- ZED 2 USB passthrough --------------------------------------------------
# Targeted approach (default): bind the USB filesystem and allow USB character
# devices (major 189) through the cgroup device filter. This is narrower than
# --privileged. If the ZED SDK still can't see the camera (some hosts, some
# hub topologies), re-run with PRIVILEGED=1.
if [ "${PRIVILEGED:-0}" = "1" ]; then
  echo "note: PRIVILEGED=1 -- running with --privileged (broad host access)." >&2
  DOCKER_ARGS+=(--privileged -v /dev/bus/usb:/dev/bus/usb)
else
  if [ -d /dev/bus/usb ]; then
    DOCKER_ARGS+=(
      -v /dev/bus/usb:/dev/bus/usb
      --device-cgroup-rule='c 189:* rmw'
    )
  else
    echo "warn: /dev/bus/usb missing -- USB passthrough skipped, the ZED won't" >&2
    echo "      be visible. (Fine if you're only doing an offline SVO replay.)" >&2
  fi
  # The ZED 2 also exposes UVC video nodes; pass any that exist so v4l2 tooling
  # and the SDK's fallback path work too. Not fatal if there are none right now.
  for v in /dev/video*; do
    [ -e "$v" ] && DOCKER_ARGS+=(--device "$v:$v")
  done
fi

# --- friendly reminder if the camera isn't plugged in ----------------------
if ! lsusb 2>/dev/null | grep -qiE '2b03:'; then
  echo "note: no Stereolabs (2b03:) device on USB right now -- plug the ZED 2" >&2
  echo "      into a USB3 port before trying to open it inside the container." >&2
fi

exec docker run "${DOCKER_ARGS[@]}" "$IMAGE" "$@"
