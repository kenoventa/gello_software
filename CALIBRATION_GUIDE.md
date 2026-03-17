# Pose Calibration System - Usage Guide

## Overview

This calibration system helps you quickly set up your bimanual teleoperation system by:

1. **Recording starting poses** - Save the current configuration of both robots and GELLO devices
2. **Live monitoring** - Display real-time joint positions while you manually adjust the robots to match the saved configuration

This solves the practical problem of needing to position constrained robots in the same configuration every time before starting teleoperation.

## Scripts

### 1. `scripts/save_calibration_pose.py` - Record Poses

Records the current joint positions of all robots and GELLO devices and saves them to a JSON file.

**Usage:**

```bash
# Bimanual UR setup with GELLO
python scripts/save_calibration_pose.py \
  --robot=bimanual_ur \
  --robot-ip-left=192.168.1.20 \
  --robot-ip-right=192.168.1.10 \
  --gello-left-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO5209-if00-port0 \
  --gello-right-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO528D-if00-port0 \
  --output=calibration_pose.json \
  --verbose
```

**Single-arm example:**

```bash
python scripts/save_calibration_pose.py \
  --robot=ur \
  --robot-ip=192.168.1.20 \
  --gello-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO528D-if00-port0 \
  --output=calibration_pose.json
```

**Output file example (`calibration_pose.json`):**

```json
{
  "robot": [-1.5708, -1.5708, 1.5708, -1.5708, -1.5708, 0.0],
  "gello_left": [0.1234, -0.5678, 1.2345, -0.9876, 0.5432, 0.1111],
  "gello_right": [0.1234, -0.5678, 1.2345, -0.9876, 0.5432, 0.1111]
}
```

### 2. `scripts/monitor_poses.py` - Live Monitor

Continuously displays the current joint positions of all robots and GELLO devices. Optionally compares with a saved calibration pose to show how close you are.

**Usage (without calibration file):**

```bash
python scripts/monitor_poses.py \
  --robot=bimanual_ur \
  --robot-ip-left=192.168.1.20 \
  --robot-ip-right=192.168.1.10 \
  --gello-left-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO5209-if00-port0 \
  --gello-right-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO528D-if00-port0 \
  --update-rate=10
```

**Usage (with calibration comparison):**

```bash
python scripts/monitor_poses.py \
  --robot=bimanual_ur \
  --robot-ip-left=192.168.1.20 \
  --robot-ip-right=192.168.1.10 \
  --gello-left-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO5209-if00-port0 \
  --gello-right-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO528D-if00-port0 \
  --calibration-file=calibration_pose.json \
  --update-rate=10
```

**Monitor output example:**

```
====================================================================================================
LIVE POSE MONITOR - Press Ctrl+C to exit
====================================================================================================

[00001] Time: 14:23:45

ROBOT_LEFT:
  Current (rad):  -1.5708 -1.5708  1.5708 -1.5708 -1.5708  0.0000
  Current (deg):   -90.00° -90.00°  90.00° -90.00° -90.00°   0.00°
  Target (rad):   -1.5500 -1.5600  1.5700 -1.5600 -1.5600  0.0000
  Target (deg):   -88.79° -89.45°  89.97° -89.45° -89.45°   0.00°
  Error (rad):    0.0208  0.0108  0.0008  0.0108  0.0108  0.0000
  Error (deg):     1.19°   0.62°   0.05°   0.62°   0.62°   0.00° ✓ CLOSE

ROBOT_RIGHT:
  Current (rad):  -1.5600 -1.5600  1.5708 -1.5708 -1.5708  0.0000
  Current (deg):   -89.45° -89.45°  90.00° -90.00° -90.00°   0.00°
  Target (rad):   -1.5500 -1.5600  1.5700 -1.5600 -1.5600  0.0000
  Target (deg):   -88.79° -89.45°  89.97° -89.45° -89.45°   0.00°
  Error (rad):    0.0100  0.0000  0.0008  0.0108  0.0108  0.0000
  Error (deg):     0.57°   0.00°   0.05°   0.62°   0.62°   0.00° ✓ CLOSE

GELLO_LEFT:
  Current (rad):  0.1234 -0.5678  1.2345 -0.9876  0.5432  0.1111
  Current (deg):   7.07° -32.52°  70.69° -56.59°  31.12°   6.37°
  Target (rad):   0.1234 -0.5678  1.2345 -0.9876  0.5432  0.1111
  Target (deg):   7.07° -32.52°  70.69° -56.59°  31.12°   6.37°
  Error (rad):    0.0000  0.0000  0.0000  0.0000  0.0000  0.0000
  Error (deg):     0.00°   0.00°   0.00°   0.00°   0.00°   0.00° ✓ CLOSE

GELLO_RIGHT:
  Current (rad):  0.1100 -0.5800  1.2500 -0.9700  0.5500  0.1200
  Current (deg):   6.30° -33.24°  71.62° -55.57°  31.51°   6.88°
  Target (rad):   0.1234 -0.5678  1.2345 -0.9876  0.5432  0.1111
  Target (deg):   7.07° -32.52°  70.69° -56.59°  31.12°   6.37°
  Error (rad):    0.0134  0.0122  0.0155  0.0176  0.0068  0.0089
  Error (deg):     0.77°   0.70°   0.89°   1.01°   0.39°   0.51° ✓ CLOSE
```

## Workflow

### Step 1: Set up initial configuration

When your system is ready (robots and GELLO devices connected), record the initial pose:

```bash
python scripts/save_calibration_pose.py \
  --robot=bimanual_ur \
  --robot-ip-left=192.168.1.20 \
  --robot-ip-right=192.168.1.10 \
  --gello-left-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO5209-if00-port0 \
  --gello-right-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO528D-if00-port0 \
  --output=my_calibration.json \
  --verbose
```

This creates `my_calibration.json` with the current poses.

### Step 2: Before teleoperation - Use monitor to align

Before starting teleoperation each time, use the monitor to align the robots and GELLO:

```bash
python scripts/monitor_poses.py \
  --robot=bimanual_ur \
  --robot-ip-left=192.168.1.20 \
  --robot-ip-right=192.168.1.10 \
  --gello-left-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO5209-if00-port0 \
  --gello-right-port=/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO528D-if00-port0 \
  --calibration-file=my_calibration.json \
  --update-rate=10
```

The monitor will show:
- **Current** position (in radians and degrees)
- **Target** position from your saved calibration
- **Error** (difference between current and target)
- **Status**: ✓ CLOSE (< 6°), ⚠ MODERATE (6-17°), ✗ FAR (> 17°)

Manually move the robots and GELLO devices to minimize the error until all are **✓ CLOSE**.

### Step 3: Start teleoperation

Once aligned (all devices showing ✓ CLOSE), press Ctrl+C to stop the monitor and start teleoperation:

```bash
python experiments/launch_nodes.py --robot=bimanual_ur
python experiments/run_env.py --bimanual --agent=gello --use-relative-mode
```

## Parameters

### Common parameters for both scripts:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--robot` | `ur` | Robot type: `ur`, `xarm`, `panda`, `bimanual_ur` |
| `--robot-ip` | `192.168.1.20` | IP for single-arm robot |
| `--robot-ip-left` | `192.168.1.20` | IP for left robot (bimanual) |
| `--robot-ip-right` | `192.168.1.10` | IP for right robot (bimanual) |
| `--gello-port` | - | Serial port for GELLO (single-arm) |
| `--gello-left-port` | - | Serial port for left GELLO (bimanual) |
| `--gello-right-port` | - | Serial port for right GELLO (bimanual) |
| `--verbose` | `False` | Print detailed output |

### Parameters specific to `save_calibration_pose.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--output` | `calibration_pose.json` | Output JSON file path |

### Parameters specific to `monitor_poses.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--calibration-file` | - | Optional JSON file for pose comparison |
| `--update-rate` | `10` | Update frequency in Hz (updates per second) |

## Finding your GELLO serial ports

To find your GELLO device serial ports, run:

```bash
ls -la /dev/serial/by-id/
```

You'll see output like:
```
usb-FTDI_USB__-__Serial_Converter_FTAO5209-if00-port0 -> ../../ttyUSB0
usb-FTDI_USB__-__Serial_Converter_FTAO528D-if00-port0 -> ../../ttyUSB1
```

Use the full path (e.g., `/dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FTAO5209-if00-port0`) as the port argument.

## Advanced: Saving multiple calibrations

You can save different calibrations for different scenarios:

```bash
# Tight workspace calibration
python scripts/save_calibration_pose.py ... --output=tight_workspace.json

# Normal workspace calibration
python scripts/save_calibration_pose.py ... --output=normal_workspace.json

# Then use the appropriate one for monitoring
python scripts/monitor_poses.py ... --calibration-file=tight_workspace.json
```

## Troubleshooting

### "Connection refused" error

- Ensure robots are powered on and the correct IPs are specified
- Check that `launch_nodes.py` is running (required for teleoperation)

### "Port not found" error for GELLO

- Check serial ports with `ls /dev/serial/by-id/`
- Ensure USB cable is connected
- Try replugging the USB cable

### Large errors in monitor

If the error doesn't decrease despite manual adjustment:
- Check that the GELLO devices are actually moving (not locked)
- Verify robot is not in protective mode
- Reset recorded calibration if the workspace has changed

### Monitor not updating

- Ensure all connections are stable
- Try reducing `--update-rate` if there are communication issues

## Notes

- These scripts do **not modify** the existing teleoperation code
- They use only the existing APIs (`get_joint_state()`, etc.)
- The calibration file is a simple JSON that can be manually edited if needed
- Relative mode automaticallycaptures initial poses on first act() call - the recorder captures the current hardware state
