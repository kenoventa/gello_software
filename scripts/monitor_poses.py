#!/usr/bin/env python3
"""
Live Pose Monitor - Display current joint positions in real-time.

This script continuously displays the current joint positions of all robots 
and GELLO devices, allowing you to manually move them to match a saved 
calibration pose.

Usage:
    # Single-arm setup
    python scripts/monitor_poses.py --robot=ur --robot-ip=192.168.1.20 \
        --gello-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO528D-if00-port0

    # Bimanual setup
    python scripts/monitor_poses.py --robot=bimanual_ur \
        --robot-ip-left=192.168.1.20 --robot-ip-right=192.168.1.10 \
        --gello-left-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO5209-if00-port0 \
        --gello-right-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO528D-if00-port0

    # Compare with saved calibration
    python scripts/monitor_poses.py --robot=bimanual_ur \
        --robot-ip-left=192.168.1.20 --robot-ip-right=192.168.1.10 \
        --gello-left-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO5209-if00-port0 \
        --gello-right-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO528D-if00-port0 \
        --calibration-file=calibration_pose.json

Press Ctrl+C to exit.
"""

import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np
import tyro

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class Args:
    robot: str = "ur"
    """Robot type: ur, xarm, panda, bimanual_ur, etc."""
    robot_port: int = 6001
    """Port for robot server (not typically needed for hardware robots)."""
    robot_ip: str = "192.168.1.20"
    """IP address for the robot (single-arm or default)."""
    robot_ip_left: str = "192.168.1.20"
    """IP address for left robot (bimanual setup)."""
    robot_ip_right: str = "192.168.1.10"
    """IP address for right robot (bimanual setup)."""

    gello_port: Optional[str] = None
    """Serial port for GELLO device (single-arm setup)."""
    gello_left_port: Optional[str] = None
    """Serial port for left GELLO device (bimanual setup)."""
    gello_right_port: Optional[str] = None
    """Serial port for right GELLO device (bimanual setup)."""

    calibration_file: Optional[str] = None
    """Optional path to calibration file for comparison."""

    update_rate: float = 10.0
    """Update rate in Hz (default 10 Hz)."""

    verbose: bool = False
    """Print verbose output."""


def initialize_robot(robot_type: str, **kwargs) -> Any:
    """Initialize a robot based on type.

    Args:
        robot_type: Type of robot (ur, xarm, panda, bimanual_ur, etc.)
        **kwargs: Additional arguments (IPs, ports, etc.)

    Returns:
        Robot instance with get_joint_state() method.
    """
    if robot_type == "ur":
        from gello.robots.ur import URRobot

        return URRobot(robot_ip=kwargs.get("robot_ip", "192.168.1.20"))

    elif robot_type == "xarm":
        from gello.robots.xarm_robot import XArmRobot

        return XArmRobot(ip=kwargs.get("robot_ip", "192.168.1.20"))

    elif robot_type == "panda":
        from gello.robots.panda import PandaRobot

        return PandaRobot(robot_ip=kwargs.get("robot_ip", "192.168.1.20"))

    elif robot_type == "bimanual_ur":
        from gello.robots.robot import BimanualRobot
        from gello.robots.ur import URRobot

        robot_left = URRobot(robot_ip=kwargs.get("robot_ip_left", "192.168.1.20"))
        robot_right = URRobot(robot_ip=kwargs.get("robot_ip_right", "192.168.1.10"))
        return BimanualRobot(robot_left, robot_right)

    else:
        raise ValueError(f"Unsupported robot type: {robot_type}")


def initialize_gello_agent(port: str) -> Any:
    """Initialize a GELLO agent for a given port.

    Args:
        port: Serial port path for GELLO device.

    Returns:
        GelloAgent instance.
    """
    from gello.agents.gello_agent import GelloAgent

    return GelloAgent(port=port)


def initialize_bimanual_gello_agents(left_port: str, right_port: str) -> tuple:
    """Initialize bimanual GELLO agents.

    Args:
        left_port: Serial port for left GELLO.
        right_port: Serial port for right GELLO.

    Returns:
        Tuple of (agent_left, agent_right).
    """
    from gello.agents.gello_agent import GelloAgent

    agent_left = GelloAgent(port=left_port)
    agent_right = GelloAgent(port=right_port)
    return agent_left, agent_right


def get_agent_joint_state(agent: Any) -> np.ndarray:
    """Extract joint state from an agent, handling RelativeAgent wrapper.

    Args:
        agent: GelloAgent or RelativeAgent wrapping a GelloAgent.

    Returns:
        Joint state as numpy array.
    """
    # Handle RelativeAgent wrapper
    if hasattr(agent, "leader_agent"):
        # This is a RelativeAgent, get the underlying agent
        agent = agent.leader_agent

    # Get joint state
    if hasattr(agent, "_robot"):
        # GelloAgent has a _robot attribute
        return agent._robot.get_joint_state()
    elif hasattr(agent, "act"):
        # Fallback: call act with empty observation
        return agent.act({})
    else:
        raise ValueError(f"Cannot get joint state from agent: {agent}")


def load_calibration_pose(filepath: str) -> Dict[str, Any]:
    """Load calibration pose from JSON file.

    Args:
        filepath: Path to calibration JSON file.

    Returns:
        Dictionary of poses.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Calibration file not found: {filepath}")

    with open(filepath, "r") as f:
        data = json.load(f)

    # Convert lists back to numpy arrays
    for key in data:
        if isinstance(data[key], list):
            data[key] = np.array(data[key])

    return data


def format_joints_rad(joints: np.ndarray) -> str:
    """Format joints in radians.

    Args:
        joints: Joint array.

    Returns:
        Formatted string.
    """
    return " ".join([f"{j:7.4f}" for j in joints])


def format_joints_deg(joints: np.ndarray) -> str:
    """Format joints in degrees.

    Args:
        joints: Joint array.

    Returns:
        Formatted string.
    """
    joints_deg = np.rad2deg(joints)
    return " ".join([f"{j:8.2f}°" for j in joints_deg])


def compute_error(current: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Compute error between current and target poses.

    Args:
        current: Current joint positions.
        target: Target joint positions.

    Returns:
        Absolute error in radians.
    """
    return np.abs(current - target)


def print_header(is_bimanual: bool = False, has_calibration: bool = False):
    """Print display header.

    Args:
        is_bimanual: Whether this is bimanual setup.
        has_calibration: Whether calibration file is loaded.
    """
    print("\033[2J\033[H")  # Clear screen
    print("=" * 100)
    print("LIVE POSE MONITOR - Press Ctrl+C to exit")
    print("=" * 100)
    print()


def print_pose_comparison(
    name: str, current: np.ndarray, target: Optional[np.ndarray] = None
):
    """Print a pose with optional target comparison.

    Args:
        name: Name of the device.
        current: Current joint positions.
        target: Optional target joint positions for comparison.
    """
    print(f"\n{name}:")
    print(f"  Current (rad): {format_joints_rad(current)}")
    print(f"  Current (deg): {format_joints_deg(current)}")

    if target is not None:
        if len(current) == len(target):
            error = compute_error(current, target)
            max_error = np.max(error)

            print(f"  Target (rad):  {format_joints_rad(target)}")
            print(f"  Target (deg):  {format_joints_deg(target)}")
            print(f"  Error (rad):   {format_joints_rad(error)}")
            print(f"  Error (deg):   {format_joints_deg(np.rad2deg(error))}")

            # Color-coded max error
            if max_error < 0.1:  # ~6 degrees
                status = "✓ CLOSE"
            elif max_error < 0.3:  # ~17 degrees
                status = "⚠ MODERATE"
            else:
                status = "✗ FAR"
            print(
                f"  Max error: {max_error:.4f} rad ({np.rad2deg(max_error):.2f}°) {status}"
            )
        else:
            print(
                f"  ⚠ Target size mismatch: current={len(current)}, target={len(target)}"
            )


def main(args: Args):
    """Main function to monitor poses."""
    try:
        # Initialize robot
        print("Initializing robot...", flush=True)
        robot = initialize_robot(
            args.robot,
            robot_ip=args.robot_ip,
            robot_ip_left=args.robot_ip_left,
            robot_ip_right=args.robot_ip_right,
        )

        is_bimanual = "bimanual" in args.robot

        # Initialize GELLO agents
        agents = {}
        if is_bimanual:
            if args.gello_left_port and args.gello_right_port:
                print("Initializing GELLO devices (bimanual)...", flush=True)
                agent_left, agent_right = initialize_bimanual_gello_agents(
                    args.gello_left_port, args.gello_right_port
                )
                agents["GELLO_LEFT"] = agent_left
                agents["GELLO_RIGHT"] = agent_right
            else:
                print("⚠ No GELLO ports specified for bimanual setup")
        else:
            if args.gello_port:
                print("Initializing GELLO device...", flush=True)
                agent = initialize_gello_agent(args.gello_port)
                agents["GELLO"] = agent
            else:
                print("⚠ No GELLO port specified")

        # Load calibration file if provided
        calibration_poses = None
        if args.calibration_file:
            print(f"Loading calibration from {args.calibration_file}...", flush=True)
            try:
                calibration_poses = load_calibration_pose(args.calibration_file)
            except Exception as e:
                print(f"⚠ Could not load calibration: {e}")

        time.sleep(0.5)

        # Main monitoring loop
        update_interval = 1.0 / args.update_rate
        print_header(is_bimanual, calibration_poses is not None)

        iteration = 0
        while True:
            iteration += 1

            # Clear screen and print header every N iterations for refresh
            if iteration % 100 == 0:
                print_header(is_bimanual, calibration_poses is not None)

            # Read current poses
            try:
                robot_joints = robot.get_joint_state()

                print(f"\n[{iteration:5d}] Time: {time.strftime('%H:%M:%S')}")

                # Robot poses
                if is_bimanual:
                    # Split bimanual pose
                    n_dofs_per_arm = len(robot_joints) // 2
                    robot_left = robot_joints[:n_dofs_per_arm]
                    robot_right = robot_joints[n_dofs_per_arm:]

                    target_left = (
                        calibration_poses["robot"][:n_dofs_per_arm]
                        if calibration_poses
                        else None
                    )
                    target_right = (
                        calibration_poses["robot"][n_dofs_per_arm:]
                        if calibration_poses
                        else None
                    )

                    print_pose_comparison("ROBOT_LEFT", robot_left, target_left)
                    print_pose_comparison("ROBOT_RIGHT", robot_right, target_right)
                else:
                    target_robot = (
                        calibration_poses["robot"] if calibration_poses else None
                    )
                    print_pose_comparison("ROBOT", robot_joints, target_robot)

                # GELLO poses
                for name, agent in agents.items():
                    agent_joints = get_agent_joint_state(agent)

                    # Map agent name to calibration key
                    calib_key = name.lower()
                    target_agent = None
                    if calibration_poses:
                        if calib_key in calibration_poses:
                            target_agent = calibration_poses[calib_key]
                        elif name == "GELLO_LEFT" and "gello_left" in calibration_poses:
                            target_agent = calibration_poses["gello_left"]
                        elif (
                            name == "GELLO_RIGHT" and "gello_right" in calibration_poses
                        ):
                            target_agent = calibration_poses["gello_right"]
                        elif name == "GELLO" and "gello" in calibration_poses:
                            target_agent = calibration_poses["gello"]

                    print_pose_comparison(name, agent_joints, target_agent)

                print()

            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"✗ Error reading poses: {e}", flush=True)

            # Wait for next update
            time.sleep(update_interval)

    except KeyboardInterrupt:
        print("\n\nMonitor stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    args = tyro.cli(Args)
    main(args)
