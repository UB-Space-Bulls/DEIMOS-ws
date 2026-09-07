#!/bin/bash
# Starts an interactive dockerfile.dev container with rover_ws bind-mounted
# and the host display connected, so Gazebo/RViz windows can open. Run this
# instead of typing out the full `docker run` invocation by hand -- it also
# saves you from forgetting `--user`, which silently reintroduces the
# root-owned-build-files bug documented in CLAUDE.md.
#
# Usage: ./docker/run-dev.sh
# Rebuild the image first if you haven't yet, or if dockerfile.dev changed:
#   docker build -f docker/dockerfile.dev -t rover-dev .
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# One-time-per-login-session permission letting containers draw windows on
# this display. Safe to re-run; it's idempotent. Not every host has `xhost`
# (it ships in x11-xserver-utils, and WSL2's WSLg doesn't need it at all),
# so skip it rather than killing the whole script when it's missing.
if command -v xhost > /dev/null 2>&1; then
  xhost +local:docker > /dev/null
else
  echo "note: xhost not found -- skipping the X11 access grant." >&2
  echo "      Often fine (WSL2/WSLg doesn't need it). If Gazebo/RViz windows" >&2
  echo "      fail to open, install it: sudo apt install x11-xserver-utils" >&2
fi

DOCKER_ARGS=(
  -it --rm
  --net=host
  --name rover-dev-container
  -e DISPLAY="$DISPLAY"
  -v /tmp/.X11-unix:/tmp/.X11-unix
  -v "${REPO_ROOT}/rover_ws:/workspaces/rover_ws"
  --user "$(id -u):$(id -g)"
)

# GPU render node, for hardware-accelerated Gazebo/RViz rendering. Not present
# on every host (plain VMs, WSL2 without GPU passthrough) and `docker run`
# hard-errors on a missing --device, so only pass it when it actually exists.
if [ -d /dev/dri ]; then
  DOCKER_ARGS+=(--device /dev/dri:/dev/dri)
else
  echo "note: /dev/dri not found -- running without GPU passthrough" >&2
  echo "      (software rendering; Gazebo will be slower but should still work)." >&2
fi

docker run "${DOCKER_ARGS[@]}" rover-dev "$@"
