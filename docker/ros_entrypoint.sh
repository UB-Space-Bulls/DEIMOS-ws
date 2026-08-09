#!/bin/bash
set -e

source /opt/ros/${ROS_DISTRO}/setup.bash

if [ -f "${ROS_WS}/install/setup.bash" ]; then
    source "${ROS_WS}/install/setup.bash"
fi

# rmw_zenoh_cpp needs a reachable Zenoh router for ROS 2 nodes to discover
# each other -- without one, nodes start fine but silently never see each
# other (topics/services just don't connect, no error beyond a startup
# warning). Auto-starting a router here is correct for a single
# self-contained machine (dockerfile.dev), but NOT for dockerfile.jetson/
# dockerfile.basestation once those need to talk to each other over the
# real base-station <-> rover network -- that router/client topology is
# still an explicit, undecided design choice (see CLAUDE.md's Zenoh
# section), so this only runs when ZENOH_ROUTER_AUTOSTART=1 is set.
if [ "${RMW_IMPLEMENTATION}" = "rmw_zenoh_cpp" ] && [ "${ZENOH_ROUTER_AUTOSTART:-0}" = "1" ]; then
    # setsid detaches the router into its own session/process group. Without
    # it, this plain `&` background job shares the entrypoint script's (and
    # after `exec`, the interactive shell's) process group -- so a Ctrl+C at
    # the terminal sends SIGINT to the whole foreground group and silently
    # kills the router along with whatever you meant to interrupt.
    setsid ros2 run rmw_zenoh_cpp rmw_zenohd > /tmp/zenohd.log 2>&1 < /dev/null &
    echo "[ros_entrypoint] Zenoh router auto-started in background (log: /tmp/zenohd.log)"
fi

exec "$@"
