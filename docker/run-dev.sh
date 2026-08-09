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
# this display. Safe to re-run; it's idempotent.
xhost +local:docker > /dev/null

docker run -it --rm \
  --net=host \
  --name rover-dev-container \
  -e DISPLAY="$DISPLAY" \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v "${REPO_ROOT}/rover_ws:/workspaces/rover_ws" \
  --device /dev/dri:/dev/dri \
  --user "$(id -u):$(id -g)" \
  rover-dev "$@"
