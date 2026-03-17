#!/usr/bin/env python3
"""
Manual Pose Capture - Record robot and GELLO poses at any time.

This script captures current joint positions and saves them to a session file.
Can be used to manually capture start/stop configs or update existing sessions.

Usage:
    # Capture and create new session
    python3 scripts/capture_pose.py \
      --robot=bimanual_ur \
      --robot-ip-left=192.168.1.20 \
      --robot-ip-right=192.168.1.10 \
      --gello-left-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO5209-if00-port0 \
      --gello-right-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO528D-if00-port0 \
      --capture-type=start

    # Capture stop config for existing session
    python3 scripts/capture_pose.py \
      --robot=bimanual_ur \
      --robot-ip-left=192.168.1.20 \
      --robot-ip-right=192.168.1.10 \
      --gello-left-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO5209-if00-port0 \
      --gello-right-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO528D-if00-port0 \
      --capture-type=stop \
      --session-id=20260316_142345
"""

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import tyro

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.pose_capture_helper import PoseCaptureManager, print_pose_info


@dataclass
class Args:
    robot: str = "ur"
    """Robot type: ur, xarm, panda, bimanual_ur, etc."""
    robot_port: int = 6001
    """Port for ZMQ robot server (from launch_nodes.py)."""
    hostname: str = "127.0.0.1"
    """Hostname for ZMQ communication."""

    gello_port: Optional[str] = None
    """Serial port for GELLO device (single-arm setup)."""
    gello_left_port: Optional[str] = None
    """Serial port for left GELLO device (bimanual setup)."""
    gello_right_port: Optional[str] = None
    """Serial port for right GELLO device (bimanual setup)."""

    capture_type: str = "start"
    """Capture type: 'start' for new session or 'stop' to update existing"""

    session_id: Optional[str] = None
    """Session ID for updating existing session (format: YYYYMMDD_HHMMSS)"""

    config_dir: str = "config_pose"
    """Directory to save captured poses."""
    verbose: bool = False
    """Print detailed output."""


def main(args: Args):
    """Main function to capture poses."""
    manager = PoseCaptureManager(config_dir=args.config_dir)

    print("\n" + "=" * 80)
    if args.capture_type == "start":
        print("CAPTURING NEW SESSION - START CONFIGURATION")
    else:
        print("CAPTURING SESSION - STOP CONFIGURATION")
    print("=" * 80)

    # Capture pose
    print("\nCapturing poses from all devices...", flush=True)
    pose_data = manager.capture_pose(
        robot_type=args.robot,
        robot_port=args.robot_port,
        hostname=args.hostname,
        gello_port=args.gello_port,
        gello_left_port=args.gello_left_port,
        gello_right_port=args.gello_right_port,
        capture_type=args.capture_type,
    )

    if pose_data is None:
        print("✗ Failed to capture poses")
        sys.exit(1)

    # Determine session ID
    if args.capture_type == "start":
        # Create new session
        session_id = datetime.fromisoformat(pose_data["timestamp"]).strftime(
            "%Y%m%d_%H%M%S"
        )

        # Create session data
        from scripts.run_with_pose_capture import create_session_data

        session_data = create_session_data(
            pose_data, capture_type="start", session_id=session_id
        )

        # Save session file
        filepath = manager.config_dir / f"session_{session_id}.json"
        with open(filepath, "w") as f:
            json.dump(session_data, f, indent=2)

        print("Saving to config_pose folder...", end=" ", flush=True)
        print("✓")

        print_pose_info(pose_data, verbose=args.verbose)

        print("\n" + "=" * 80)
        print(f"✓ NEW SESSION CREATED")
        print(f"  Session ID: {session_id}")
        print(f"  File: {filepath}")
        print("=" * 80 + "\n")

    else:  # capture_type == "stop"
        if args.session_id is None:
            print("✗ Error: --session-id required for stop capture")
            sys.exit(1)

        session_id = args.session_id

        # Load and update existing session
        try:
            filepath = manager.config_dir / f"session_{session_id}.json"
            with open(filepath, "r") as f:
                session_data = json.load(f)

            # Add stop config
            session_data["timestamp_stop"] = pose_data["timestamp"]
            session_data["timestamp_stop_unix"] = pose_data["timestamp_unix"]
            session_data["config_stop"] = {
                "robot_left": pose_data.get("robot_left"),
                "robot_right": pose_data.get("robot_right"),
                "gello_left": pose_data.get("gello_left"),
                "gello_right": pose_data.get("gello_right"),
            }

            # Save updated session
            with open(filepath, "w") as f:
                json.dump(session_data, f, indent=2)

            print("Saving to config_pose folder...", end=" ", flush=True)
            print("✓")

            print_pose_info(pose_data, verbose=args.verbose)

            print("\n" + "=" * 80)
            print(f"✓ SESSION UPDATED WITH STOP CONFIG")
            print(f"  Session ID: {session_id}")
            print(f"  File: {filepath}")
            print("=" * 80 + "\n")

        except FileNotFoundError:
            print(f"✗ Session file not found: session_{session_id}.json")
            sys.exit(1)
        except Exception as e:
            print(f"✗ Error: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    args = tyro.cli(Args)
    main(args)
