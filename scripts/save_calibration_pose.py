#!/usr/bin/env python3
"""
Pose Recorder Script - Save the current poses of robots and GELLO devices.

This script reads the current joint positions from all robots and GELLO devices
and saves them to a JSON file for later restoration during calibration.

Usage:
    # Single-arm setup
    python scripts/save_calibration_pose.py --robot=ur --robot-ip=192.168.1.20 \
        --gello-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO528D-if00-port0

    # Bimanual setup
    python scripts/save_calibration_pose.py --robot=bimanual_ur \
        --robot-ip-left=192.168.1.20 --robot-ip-right=192.168.1.10 \
        --gello-left-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO5209-if00-port0 \
        --gello-right-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO528D-if00-port0

"""

import json
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
    gello_left_port: str = (
        "/dev/serial/by-id/usb-FTDI_USB__-Serial_Converter_FTAO5209-if00-port0"
    )
    """Serial port for left GELLO device (bimanual setup)."""
    gello_right_port: str = (
        "/dev/serial/by-id/usb-FTDI_USB__-Serial_Converter_FTAO528D-if00-port0"
    )
    """Serial port for right GELLO device (bimanual setup)."""

    output: str = "calibration_pose.json"
    """Output file path for saving poses."""

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


def save_pose_to_json(
    poses: Dict[str, Any], output_path: str, verbose: bool = False
) -> None:
    """Save poses to a JSON file.

    Args:
        poses: Dictionary of poses.
        output_path: Path to output JSON file.
        verbose: Whether to print verbose output.
    """
    # Convert numpy arrays to lists for JSON serialization
    poses_serializable = {}
    for key, val in poses.items():
        if isinstance(val, np.ndarray):
            poses_serializable[key] = val.tolist()
        elif isinstance(val, dict):
            poses_serializable[key] = {}
            for k, v in val.items():
                if isinstance(v, np.ndarray):
                    poses_serializable[key][k] = v.tolist()
                else:
                    poses_serializable[key][k] = v
        else:
            poses_serializable[key] = val

    with open(output_path, "w") as f:
        json.dump(poses_serializable, f, indent=2)

    if verbose:
        print(f"✓ Poses saved to {output_path}")


def load_pose_from_json(input_path: str) -> Dict[str, Any]:
    """Load poses from a JSON file.

    Args:
        input_path: Path to input JSON file.

    Returns:
        Dictionary of poses.
    """
    with open(input_path, "r") as f:
        return json.load(f)


def format_joints_for_display(
    joints: np.ndarray, name: str = "", in_degrees: bool = False
) -> str:
    """Format joint array for display.

    Args:
        joints: Joint array.
        name: Label for the joints.
        in_degrees: Whether to convert to degrees.

    Returns:
        Formatted string.
    """
    if in_degrees:
        joints_display = np.rad2deg(joints)
        unit = "°"
    else:
        joints_display = joints
        unit = " rad"

    formatted = ", ".join([f"{j:.4f}{unit}" for j in joints_display])
    if name:
        return f"{name}: [{formatted}]"
    return f"[{formatted}]"


def main(args: Args):
    """Main function to record poses."""
    print("\n" + "=" * 80)
    print("POSE RECORDER - Save current robot and GELLO poses")
    print("=" * 80)

    try:
        # Initialize robot
        print(f"\nInitializing robot ({args.robot})...", end=" ", flush=True)
        robot = initialize_robot(
            args.robot,
            robot_ip=args.robot_ip,
            robot_ip_left=args.robot_ip_left,
            robot_ip_right=args.robot_ip_right,
        )
        print("✓")

        # Wait a moment for robot to settle
        time.sleep(0.5)

        # Initialize GELLO agents
        agents = {}
        is_bimanual = "bimanual" in args.robot
        if is_bimanual:
            # Bimanual setup
            if args.gello_left_port and args.gello_right_port:
                print(f"Initializing GELLO devices (bimanual)...", end=" ", flush=True)
                agent_left, agent_right = initialize_bimanual_gello_agents(
                    args.gello_left_port, args.gello_right_port
                )
                agents["gello_left"] = agent_left
                agents["gello_right"] = agent_right
                print("✓")
            else:
                print(f"⚠ No GELLO ports specified for bimanual setup")
        else:
            # Single-arm setup
            if args.gello_port:
                print(f"Initializing GELLO device...", end=" ", flush=True)
                agent = initialize_gello_agent(args.gello_port)
                agents["gello"] = agent
                print("✓")
            else:
                print(f"⚠ No GELLO port specified")

        # Read joint states
        print(f"\nReading joint poses...", end=" ", flush=True)
        poses = {}

        # Robot poses
        robot_joints = robot.get_joint_state()
        poses["robot"] = robot_joints
        if args.verbose:
            print(f"\n  Robot: {format_joints_for_display(robot_joints)}")
            print(
                f"  Robot (deg): {format_joints_for_display(robot_joints, in_degrees=True)}"
            )

        # GELLO poses
        for name, agent in agents.items():
            agent_joints = get_agent_joint_state(agent)
            poses[name] = agent_joints
            if args.verbose:
                print(f"  {name}: {format_joints_for_display(agent_joints)}")
                print(
                    f"  {name} (deg): {format_joints_for_display(agent_joints, in_degrees=True)}"
                )

        print("✓")

        # Save to file
        print(f"\nSaving to {args.output}...", end=" ", flush=True)
        save_pose_to_json(poses, args.output, verbose=True)

        # Print summary
        print("\n" + "=" * 80)
        print("POSE SAVED SUCCESSFULLY")
        print("=" * 80)
        print("\nSummary:")
        print(f"  Output file: {args.output}")
        print(f"  Robot joints (rad): {format_joints_for_display(robot_joints)}")
        print(
            f"  Robot joints (deg): {format_joints_for_display(robot_joints, in_degrees=True)}"
        )

        for name, joints in poses.items():
            if name != "robot":
                print(f"  {name} (rad): {format_joints_for_display(joints)}")
                print(
                    f"  {name} (deg): {format_joints_for_display(joints, in_degrees=True)}"
                )

        print("\n✓ Ready to use with monitor_poses.py and teleoperation")
        print("=" * 80 + "\n")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    args = tyro.cli(Args)
    main(args)
