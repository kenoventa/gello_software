#!/usr/bin/env python3
"""
Pose Capture Helper - Core functions for capturing and saving poses with timestamp.

This module provides the core functionality for capturing robot and GELLO poses
and saving them to the config_pose folder with timestamps.

Used by:
- capture_start.py (during teleoperation startup)
- capture_stop.py (during teleoperation shutdown)
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def rad_to_deg(joints: Optional[list]) -> Optional[list]:
    """Convert a list of joint angles from radians to degrees."""
    if joints is None:
        return None
    return np.rad2deg(joints).tolist()


class PoseCaptureManager:
    """Manages pose capture with timestamp and formatting."""

    def __init__(self, config_dir: str = "config_pose"):
        """Initialize pose capture manager.

        Args:
            config_dir: Directory to save captured poses.
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def initialize_robot(self, robot_type: str, **kwargs) -> Any:
        """Initialize a robot via ZMQClientRobot (connects to server from launch_nodes.py)."""
        from gello.zmq_core.robot_node import ZMQClientRobot

        port = kwargs.get("robot_port", 6001)
        hostname = kwargs.get("hostname", "127.0.0.1")

        return ZMQClientRobot(port=port, host=hostname)

    def initialize_gello_agent(self, port: str) -> Any:
        """Initialize a GELLO agent for a given port."""
        from gello.agents.gello_agent import GelloAgent

        return GelloAgent(port=port)

    def initialize_bimanual_gello_agents(
        self, left_port: str, right_port: str
    ) -> tuple:
        """Initialize bimanual GELLO agents."""
        from gello.agents.gello_agent import GelloAgent

        agent_left = GelloAgent(port=left_port)
        agent_right = GelloAgent(port=right_port)
        return agent_left, agent_right

    def get_agent_joint_state(self, agent: Any) -> np.ndarray:
        """Extract joint state from an agent, handling RelativeAgent wrapper."""
        # Handle RelativeAgent wrapper
        if hasattr(agent, "leader_agent"):
            agent = agent.leader_agent

        # Get joint state
        if hasattr(agent, "_robot"):
            return agent._robot.get_joint_state()
        elif hasattr(agent, "act"):
            return agent.act({})
        else:
            raise ValueError(f"Cannot get joint state from agent: {agent}")

    def capture_pose(
        self,
        robot_type: str,
        robot_port: int = 6001,
        hostname: str = "127.0.0.1",
        gello_port: Optional[str] = None,
        gello_left_port: str = "/dev/serial/by-id/usb-FTDI_USB__-Serial_Converter_FTAO5209-if00-port0",
        gello_right_port: str = "/dev/serial/by-id/usb-FTDI_USB__-Serial_Converter_FTAO528D-if00-port0",
        capture_type: str = "start",
    ) -> Dict[str, Any]:
        """Capture current poses from all devices.

        Args:
            robot_type: Robot type (ur, xarm, bimanual_ur, etc.)
            robot_port: ZMQ port for robot server (default 6001 from launch_nodes.py)
            hostname: Hostname/IP for ZMQ communication (default 127.0.0.1)
            gello_port: Serial port for single GELLO
            gello_left_port: Serial port for left GELLO (bimanual)
            gello_right_port: Serial port for right GELLO (bimanual)
            capture_type: "start" or "stop" for naming

        Returns:
            Dictionary with captured poses and metadata.
        """
        timestamp = datetime.now().isoformat()
        timestamp_unix = time.time()

        try:
            # Initialize robot (connects to server from launch_nodes.py)
            robot = self.initialize_robot(
                robot_type,
                robot_port=robot_port,
                hostname=hostname,
            )

            # Read robot pose
            is_bimanual = "bimanual" in robot_type
            robot_joints = robot.get_joint_state()

            result = {
                "timestamp": timestamp,
                "timestamp_unix": timestamp_unix,
                "capture_type": capture_type,
                "robot_type": robot_type,
            }

            # Split poses if bimanual
            if is_bimanual:
                n_dofs_per_arm = len(robot_joints) // 2
                result["robot_left"] = robot_joints[:n_dofs_per_arm].tolist()
                result["robot_right"] = robot_joints[n_dofs_per_arm:].tolist()
            else:
                # For single-arm, save as robot_left for consistency
                result["robot_left"] = robot_joints.tolist()
                result["robot_right"] = None

            # Initialize GELLO agents
            gello_poses = {}
            if is_bimanual:
                if gello_left_port and gello_right_port:
                    try:
                        agent_left, agent_right = self.initialize_bimanual_gello_agents(
                            gello_left_port, gello_right_port
                        )
                        gello_poses["gello_left"] = self.get_agent_joint_state(
                            agent_left
                        ).tolist()
                        gello_poses["gello_right"] = self.get_agent_joint_state(
                            agent_right
                        ).tolist()
                    except Exception as e:
                        print(f"⚠ Warning: Could not capture GELLO bimanual: {e}")
                        gello_poses["gello_left"] = None
                        gello_poses["gello_right"] = None
                else:
                    print(
                        f"⚠ GELLO ports not provided (gello_left: {gello_left_port}, gello_right: {gello_right_port})"
                    )
                    print(f"   Skipping GELLO capture")
                    gello_poses["gello_left"] = None
                    gello_poses["gello_right"] = None
            else:
                if gello_port:
                    try:
                        agent = self.initialize_gello_agent(gello_port)
                        gello_poses["gello_left"] = self.get_agent_joint_state(
                            agent
                        ).tolist()
                        gello_poses["gello_right"] = None
                    except Exception as e:
                        print(f"⚠ Warning: Could not capture GELLO: {e}")
                        gello_poses["gello_left"] = None
                        gello_poses["gello_right"] = None
                else:
                    print(f"⚠ GELLO port not provided (gello_port: {gello_port})")
                    print(f"   Skipping GELLO capture")
                    gello_poses["gello_left"] = None
                    gello_poses["gello_right"] = None

            result.update(gello_poses)

            # Convert to degrees
            result["robot_left"] = rad_to_deg(result.get("robot_left"))
            result["robot_right"] = rad_to_deg(result.get("robot_right"))
            result["gello_left"] = rad_to_deg(result.get("gello_left"))
            result["gello_right"] = rad_to_deg(result.get("gello_right"))

            return result

        except Exception as e:
            print(f"✗ Error capturing pose: {e}")
            import traceback

            traceback.print_exc()
            return None

    def save_session(self, session_data: Dict[str, Any]) -> str:
        """Save complete session with start and stop configs.

        Args:
            session_data: Dictionary with session_id, config_start, config_stop.

        Returns:
            Path to saved file.
        """
        if session_data is None:
            raise ValueError("No session data to save")

        if "session_id" not in session_data:
            raise ValueError("Session data must have session_id")

        session_id = session_data["session_id"]
        filename = f"session_{session_id}.json"
        filepath = self.config_dir / filename

        # Save to JSON
        with open(filepath, "w") as f:
            json.dump(session_data, f, indent=2)

        return str(filepath)

    def load_session(self, session_id: str) -> Dict[str, Any]:
        """Load existing session file.

        Args:
            session_id: Session ID (filename without .json)

        Returns:
            Session data dictionary.
        """
        filename = f"session_{session_id}.json"
        filepath = self.config_dir / filename

        if not filepath.exists():
            raise FileNotFoundError(f"Session file not found: {filepath}")

        with open(filepath, "r") as f:
            return json.load(f)

    def update_session(
        self, session_id: str, pose_data: Dict[str, Any], capture_type: str = "stop"
    ) -> str:
        """Add stop config to existing session file.

        Args:
            session_id: Session ID of existing session.
            pose_data: Stop configuration data.
            capture_type: Should be "stop".

        Returns:
            Path to updated file.
        """
        if pose_data is None:
            raise ValueError("No pose data to save")

        # Load existing session
        try:
            session_data = self.load_session(session_id)
        except FileNotFoundError:
            raise ValueError(f"Cannot find session {session_id} to update")

        # Add stop config
        session_data["timestamp_stop"] = pose_data["timestamp"]
        session_data["timestamp_stop_unix"] = pose_data["timestamp_unix"]
        session_data["config_stop"] = {
            "robot_left": pose_data.get("robot_left"),
            "robot_right": pose_data.get("robot_right"),
            "gello_left": pose_data.get("gello_left"),
            "gello_right": pose_data.get("gello_right"),
        }

        return self.save_session(session_data)

    def get_latest_poses(self) -> Dict[str, str]:
        """Get paths to latest start and stop pose files.

        Returns:
            Dictionary with 'start' and 'stop' keys pointing to latest files.
        """
        results = {"start": None, "stop": None}

        if not self.config_dir.exists():
            return results

        start_files = sorted(self.config_dir.glob("pose_start_*.json"))
        stop_files = sorted(self.config_dir.glob("pose_stop_*.json"))

        if start_files:
            results["start"] = str(start_files[-1])
        if stop_files:
            results["stop"] = str(stop_files[-1])

        return results


def print_pose_info(pose_data: Dict[str, Any], verbose: bool = False):
    """Print captured pose information.

    Args:
        pose_data: Dictionary with captured pose data.
        verbose: Whether to print full details.
    """
    if pose_data is None:
        print("✗ No pose data available")
        return

    print(f"\nCapture Information:")
    print(f"  Timestamp: {pose_data['timestamp']}")
    print(f"  Type: {pose_data['capture_type']}")
    print(f"  Robot: {pose_data['robot_type']}")

    # Robot poses
    if pose_data.get("robot_left"):
        joints = np.array(pose_data["robot_left"])
        joints_deg = np.rad2deg(joints)
        print(f"\n  Robot Left ({len(joints)} DOFs):")
        if verbose:
            print(f"    RAD: {[f'{j:.4f}' for j in joints]}")
            print(f"    DEG: {[f'{j:.2f}°' for j in joints_deg]}")
        else:
            print(f"    RAD: [{', '.join([f'{j:.4f}' for j in joints])}]")
            print(f"    DEG: [{', '.join([f'{j:.2f}°' for j in joints_deg])}]")

    if pose_data.get("robot_right"):
        joints = np.array(pose_data["robot_right"])
        joints_deg = np.rad2deg(joints)
        print(f"\n  Robot Right ({len(joints)} DOFs):")
        if verbose:
            print(f"    RAD: {[f'{j:.4f}' for j in joints]}")
            print(f"    DEG: {[f'{j:.2f}°' for j in joints_deg]}")
        else:
            print(f"    RAD: [{', '.join([f'{j:.4f}' for j in joints])}]")
            print(f"    DEG: [{', '.join([f'{j:.2f}°' for j in joints_deg])}]")

    # GELLO poses
    if pose_data.get("gello_left"):
        joints = np.array(pose_data["gello_left"])
        joints_deg = np.rad2deg(joints)
        print(f"\n  GELLO Left ({len(joints)} DOFs):")
        if verbose:
            print(f"    RAD: {[f'{j:.4f}' for j in joints]}")
            print(f"    DEG: {[f'{j:.2f}°' for j in joints_deg]}")
        else:
            print(f"    RAD: [{', '.join([f'{j:.4f}' for j in joints])}]")
            print(f"    DEG: [{', '.join([f'{j:.2f}°' for j in joints_deg])}]")

    if pose_data.get("gello_right"):
        joints = np.array(pose_data["gello_right"])
        joints_deg = np.rad2deg(joints)
        print(f"\n  GELLO Right ({len(joints)} DOFs):")
        if verbose:
            print(f"    RAD: {[f'{j:.4f}' for j in joints]}")
            print(f"    DEG: {[f'{j:.2f}°' for j in joints_deg]}")
        else:
            print(f"    RAD: [{', '.join([f'{j:.4f}' for j in joints])}]")
            print(f"    DEG: [{', '.join([f'{j:.2f}°' for j in joints_deg])}]")
