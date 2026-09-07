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

# Hand the container the host GPU for hardware-accelerated GL (Gazebo/RViz).
# Native Linux exposes a DRM render node at /dev/dri; WSL2 has no /dev/dri
# and instead exposes the GPU via /dev/dxg plus the driver libs mounted at
# /usr/lib/wsl. If neither is present the container still runs -- Gazebo/RViz
# just fall back to software (llvmpipe) rendering, which is fine for
# CPU-only sim.
gpu_args=()
if [ -e /dev/dri ]; then
  gpu_args+=(--device /dev/dri:/dev/dri)
elif [ -e /dev/dxg ]; then
  gpu_args+=(--device /dev/dxg:/dev/dxg
             -v /usr/lib/wsl:/usr/lib/wsl
             -e LD_LIBRARY_PATH=/usr/lib/wsl/lib)
fi

docker run -it --rm \
  --net=host \
  --name rover-dev-container \
  -e DISPLAY="$DISPLAY" \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -v "${REPO_ROOT}/rover_ws:/workspaces/rover_ws" \
  "${gpu_args[@]}" \
  --user "$(id -u):$(id -g)" \
  rover-dev "$@"
