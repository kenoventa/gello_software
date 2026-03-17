#!/usr/bin/env python3
"""
List Saved Poses - View all captured start and stop configurations.

This script displays all saved poses in the config_pose folder, showing
timestamps and basic statistics.

Usage:
    python3 scripts/list_poses.py
    python3 scripts/list_poses.py --config-dir=config_pose --verbose
"""

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import tyro


@dataclass
class Args:
    config_dir: str = "config_pose"
    """Directory containing saved poses."""
    verbose: bool = False
    """Print detailed pose information."""


def format_timestamp(iso_ts: str) -> str:
    """Format ISO timestamp nicely."""
    try:
        dt = datetime.fromisoformat(iso_ts)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return iso_ts


def load_pose_file(filepath: Path) -> dict:
    """Load pose from JSON file."""
    with open(filepath, "r") as f:
        return json.load(f)


def print_pose_summary(pose_data: dict, filepath: Path):
    """Print summary of a pose file."""
    timestamp = pose_data.get("timestamp", "N/A")
    capture_type = pose_data.get("capture_type", "N/A")
    robot_type = pose_data.get("robot_type", "N/A")

    print(f"\n{'=' * 80}")
    print(f"File: {filepath.name}")
    print(f"Type: {capture_type.upper()}")
    print(f"Time: {format_timestamp(timestamp)}")
    print(f"Robot: {robot_type}")
    print(f"{'=' * 80}")

    # Robot Left
    if pose_data.get("robot_left"):
        joints = np.array(pose_data["robot_left"])
        joints_deg = np.rad2deg(joints)
        print(f"\nRobot Left ({len(joints)} DOFs):")
        print(f"  RAD: [{', '.join([f'{j:.4f}' for j in joints])}]")
        print(f"  DEG: [{', '.join([f'{j:.2f}°' for j in joints_deg])}]")

    # Robot Right
    if pose_data.get("robot_right"):
        joints = np.array(pose_data["robot_right"])
        joints_deg = np.rad2deg(joints)
        print(f"\nRobot Right ({len(joints)} DOFs):")
        print(f"  RAD: [{', '.join([f'{j:.4f}' for j in joints])}]")
        print(f"  DEG: [{', '.join([f'{j:.2f}°' for j in joints_deg])}]")

    # GELLO Left
    if pose_data.get("gello_left"):
        joints = np.array(pose_data["gello_left"])
        joints_deg = np.rad2deg(joints)
        print(f"\nGELLO Left ({len(joints)} DOFs):")
        print(f"  RAD: [{', '.join([f'{j:.4f}' for j in joints])}]")
        print(f"  DEG: [{', '.join([f'{j:.2f}°' for j in joints_deg])}]")

    # GELLO Right
    if pose_data.get("gello_right"):
        joints = np.array(pose_data["gello_right"])
        joints_deg = np.rad2deg(joints)
        print(f"\nGELLO Right ({len(joints)} DOFs):")
        print(f"  RAD: [{', '.join([f'{j:.4f}' for j in joints])}]")
        print(f"  DEG: [{', '.join([f'{j:.2f}°' for j in joints_deg])}]")


def main(args: Args):
    """List all saved poses."""
    config_dir = Path(args.config_dir)

    if not config_dir.exists():
        print(f"Directory {args.config_dir} does not exist.")
        sys.exit(1)

    # Find all pose files
    start_files = sorted(config_dir.glob("pose_start_*.json"))
    stop_files = sorted(config_dir.glob("pose_stop_*.json"))
    all_files = sorted(start_files + stop_files)

    if not all_files:
        print(f"No pose files found in {args.config_dir}")
        sys.exit(0)

    print("\n" + "=" * 80)
    print(f"SAVED POSES IN: {config_dir.absolute()}")
    print(
        f"Total files: {len(all_files)} (start: {len(start_files)}, stop: {len(stop_files)})"
    )
    print("=" * 80)

    if not args.verbose:
        # Show simple table
        print(f"\n{'File':<40} {'Type':<6} {'Time':<19}")
        print("-" * 80)
        for filepath in all_files:
            try:
                pose_data = load_pose_file(filepath)
                timestamp_str = format_timestamp(pose_data.get("timestamp", "N/A"))
                capture_type = pose_data.get("capture_type", "N/A").upper()
                print(f"{filepath.name:<40} {capture_type:<6} {timestamp_str:<19}")
            except Exception as e:
                print(f"{filepath.name:<40} ERROR: {e}")
    else:
        # Show detailed view
        for filepath in all_files:
            try:
                pose_data = load_pose_file(filepath)
                print_pose_summary(pose_data, filepath)
            except Exception as e:
                print(f"\n✗ Error loading {filepath.name}: {e}")

    print("\n" + "=" * 80)
    print("TIP: Use --verbose to see full pose details")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    args = tyro.cli(Args)
    main(args)
