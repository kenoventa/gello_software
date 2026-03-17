#!/bin/bash
# Quick Start Guide - Bimanual UR Teleoperation Calibration
# Save this for easy copy-paste during setup

# ============================================================================
# STEP 1: Record Your Initial Pose (do this once when system is set up)
# ============================================================================

python3 scripts/save_calibration_pose.py \
  --robot=bimanual_ur \
  --robot-ip-left=192.168.1.20 \
  --robot-ip-right=192.168.1.10 \
  --gello-left-port="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO5209-if00-port0" \
  --gello-right-port="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO528D-if00-port0" \
  --output=my_calibration.json \
  --verbose

# Output: my_calibration.json with your starting configuration


# ============================================================================
# STEP 2: Before Each Teleoperation Session - Monitor and Align
# ============================================================================

python3 scripts/monitor_poses.py \
  --robot=bimanual_ur \
  --robot-ip-left=192.168.1.20 \
  --robot-ip-right=192.168.1.10 \
  --gello-left-port="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO5209-if00-port0" \
  --gello-right-port="/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO528D-if00-port0" \
  --calibration-file=my_calibration.json \
  --update-rate=10

# The monitor will show current positions and errors
# Manually move robots/GELLO to match the target (all joints should show ✓ CLOSE)
# Press Ctrl+C when done


# ============================================================================
# STEP 3: Start Teleoperation (in separate terminal window)
# ============================================================================

# Terminal 1: Start robot node server
python3 experiments/launch_nodes.py --robot=bimanual_ur

# Terminal 2: Start teleoperation environment
python3 experiments/run_env.py --bimanual --agent=gello --use-relative-mode

# Now you can teleoperate!


# ============================================================================
# USEFUL COMMANDS
# ============================================================================

# Find your GELLO device ports:
ls -la /dev/serial/by-id/

# View your saved calibration:
cat my_calibration.json

# Create multiple calibrations for different scenarios:
# (e.g., different workspace configurations)
python3 scripts/save_calibration_pose.py ... --output=workspace1.json
python3 scripts/save_calibration_pose.py ... --output=workspace2.json

# Edit calibration file manually (JSON format):
nano my_calibration.json

# Clean up calibration files when no longer needed:
rm my_calibration.json

# ============================================================================
# TROUBLESHOOTING
# ============================================================================

# If monitor shows "Connection refused":
# - Ensure robot nodes are running (Step 1: launch_nodes.py)
# - Check robot IPs are correct with networkping
# - Try rebooting the robot

# If GELLO shows "Port not found":
# - Check physical USB connection
# - Run: ls /dev/serial/by-id/ to find correct port
# - Try reconnecting USB cable

# If monitor shows large errors:
# - Check robots aren't in protective mode
# - Verify GELLO devices aren't locked/stuck
# - Save a new calibration if workspace changed
