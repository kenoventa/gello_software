# System Architecture & Workflow

Complete breakdown of the pose capture system architecture, how it works, and when components are used.

## System Components

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     POSE CAPTURE SYSTEM ARCHITECTURE                    │
└─────────────────────────────────────────────────────────────────────────┘

┌─ AUTOMATIC CAPTURE (RECOMMENDED) ──────────────────────────────────────┐
│                                                                         │
│  run_with_pose_capture.py (scripts/run_with_pose_capture.py)          │
│  ├─ Takes robot/GELLO connection parameters                           │
│  ├─ Calls capture_pose() for START config                             │
│  ├─ Spawns experiments/run_env.py subprocess                          │
│  ├─ On user Ctrl+C, calls capture_pose() for STOP config              │
│  └─ Saves combined session to config_pose/session_*.json              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─ MANUAL CAPTURE (WHEN YOU NEED FINE CONTROL) ──────────────────────────┐
│                                                                         │
│  capture_pose.py (scripts/capture_pose.py)                            │
│  ├─ For START: Creates new session file with start config             │
│  │  $ python3 capture_pose.py --capture-type=start ...                │
│  └─ For STOP: Updates existing session with stop config               │
│     $ python3 capture_pose.py --capture-type=stop --session-id=... ... │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─ CORE FUNCTIONALITY ────────────────────────────────────────────────────┐
│                                                                         │
│  pose_capture_helper.py (scripts/pose_capture_helper.py)              │
│  ├─ initialize_robot(robot_type, ...)                                 │
│  ├─ initialize_gello_agent(...)                                       │
│  ├─ capture_pose(robot, gello_agent)                                  │
│  ├─ save_session(session_data, config_dir)                            │
│  ├─ load_session(session_id, config_dir)                              │
│  └─ update_session(session_id, config_data, config_dir)               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─ VIEWING ──────────────────────────────────────────────────────────────┐
│                                                                         │
│  list_poses.py (scripts/list_poses.py)                                │
│  └─ Lists all saved sessions from config_pose/ folder                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

┌─ STORAGE ──────────────────────────────────────────────────────────────┐
│                                                                         │
│  config_pose/ (directory)                                             │
│  ├─ session_20260316_142345.json  (1 session = start + stop)         │
│  ├─ session_20260316_151823.json  (multiple sessions possible)       │
│  └─ session_20260316_165412.json                                     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Automatic Capture (Recommended)

```
USER RUNS:
  python3 scripts/run_with_pose_capture.py --robot-ip-left=... --robot-ip-right=...

           ┌─────────────────────────────────────────────────────────┐
           │     run_with_pose_capture.py starts                     │
           └────────────────────┬────────────────────────────────────┘
                                │
                    ┌───────────▼────────────┐
                    │  Create session_data   │
                    │  with START timestamp  │
                    └───────────┬────────────┘
                                │
                ┌───────────────▼──────────────────┐
                │ capture_pose() - START CONFIG     │
                │  - Read robot joint states       │
                │  - Read GELLO sensor positions   │
                │  - Store in session_data         │
                └───────────┬──────────────────────┘
                            │
            ┌───────────────▼────────────────┐
            │ spawn subprocess:              │
            │ experiments/run_env.py         │
            │ (normal teleoperation)         │
            └───────────┬────────────────────┘
                        │
                (user teleoperates)
                        │
            ┌───────────▼────────────────┐
            │ User presses Ctrl+C        │
            │ Signal handler triggered   │
            └───────────┬────────────────┘
                        │
        ┌───────────────▼──────────────────┐
        │ capture_pose() - STOP CONFIG      │
        │  - Read robot joint states       │
        │  - Read GELLO sensor positions   │
        │  - Store in session_data         │
        └───────────┬──────────────────────┘
                    │
    ┌───────────────▼────────────────┐
    │ save_session(session_data)     │
    │ Creates: session_*.json with   │
    │  - config_start                │
    │  - config_stop                 │
    │  - timestamps                  │
    └───────────┬────────────────────┘
                │
    ┌───────────▼──────────────┐
    │ File saved to config_pose/│
    │ session_YYYYMMDD_HHMMSS │
    │       .json              │
    └──────────────────────────┘
```

### Manual Capture (Fine-Grained Control)

#### Start New Session

```
USER RUNS:
  python3 scripts/capture_pose.py --capture-type=start --robot-ip-left=... ...

           ┌──────────────────────────────────────┐
           │ capture_pose.py --capture-type=start │
           └────────┬─────────────────────────────┘
                    │
        ┌───────────▼──────────────┐
        │ Initialize robot/GELLO   │
        └───────────┬──────────────┘
                    │
        ┌───────────▼──────────────────┐
        │ capture_pose()               │
        │  - Read joint states         │
        │  - Create session_data       │
        └───────────┬──────────────────┘
                    │
        ┌───────────▼──────────────────────┐
        │ save_session()                   │
        │ Saves START config to file:     │
        │ config_pose/session_*.json      │
        │ (STOP config is None initially) │
        └───────────┬──────────────────────┘
                    │
        ┌───────────▼──────────────┐
        │ Returns session_id       │
        │ e.g., 20260316_142345    │
        └──────────────────────────┘
```

#### Update Existing Session

```
USER RUNS:
  python3 scripts/capture_pose.py --capture-type=stop --session-id=20260316_142345 ...

           ┌────────────────────────────────────────────┐
           │ capture_pose.py --capture-type=stop        │
           │               --session-id=20260316_142345 │
           └────────┬───────────────────────────────────┘
                    │
        ┌───────────▼──────────────────────┐
        │ load_session(20260316_142345)    │
        │ Load existing START config       │
        └───────────┬──────────────────────┘
                    │
        ┌───────────▼──────────────────────┐
        │ Initialize robot/GELLO           │
        └───────────┬──────────────────────┘
                    │
        ┌───────────▼──────────────────────┐
        │ capture_pose()                   │
        │  - Read joint states (STOP time) │
        └───────────┬──────────────────────┘
                    │
        ┌───────────▼──────────────────────┐
        │ update_session()                 │
        │  - Keep START config             │
        │  - Add STOP config               │
        │  - Add STOP timestamp            │
        │  - Save updated file             │
        └───────────┬──────────────────────┘
                    │
        ┌───────────▼──────────────────────┐
        │ Session complete:                │
        │ Both START and STOP configs      │
        │ in one file                      │
        └──────────────────────────────────┘
```

## When to Use What

### Use run_with_pose_capture.py (Automatic) When:

✅ You want to do normal teleoperation AND capture poses
✅ You want one file per teleoperation session
✅ You want automatic capture (no manual steps)
✅ You want consistent timestamps for session start/stop
✅ You want the simplest workflow

**Example:**
```bash
# Just run this, everything else happens automatically!
python3 scripts/run_with_pose_capture.py \
  --robot-ip-left=192.168.1.20 \
  --robot-ip-right=192.168.1.10 \
  --gello-left-port=/dev/serial/by-id/usb-...
  
# Captures START → teleops → press Ctrl+C → captures STOP → saves file
```

### Use capture_pose.py (Manual) When:

✅ You want fine-grained control over when to capture
✅ You captured configs separately and need flexibility
✅ You're doing testing/debugging and need manual control
✅ You're integrating with your own custom script
✅ You want to capture specific robot states for reference

**Example:**
```bash
# Capture START when ready
python3 scripts/capture_pose.py --capture-type=start ...
# Returns: session_20260316_142345

# (do whatever you want)

# Capture STOP when ready
python3 scripts/capture_pose.py --capture-type=stop --session-id=20260316_142345 ...
```

## File Organization

### By Use Case

**Teleoperation with automatic capture:**
```
gello_software/
├── scripts/
│   ├── run_with_pose_capture.py  ← USE THIS (automatic)
│   ├── pose_capture_helper.py    ← (dependency, don't call directly)
│   ├── list_poses.py             ← (view results)
│   └── ...
└── config_pose/
    ├── session_20260316_142345.json ← (auto-saved after teleoperation)
    └── ...
```

**Manual testing/debugging:**
```
gello_software/
├── scripts/
│   ├── capture_pose.py          ← USE THIS (manual start/stop)
│   ├── pose_capture_helper.py   ← (dependency, don't call directly)
│   ├── list_poses.py            ← (view results)
│   └── ...
└── config_pose/
    ├── session_20260316_142345.json ← (manually created)
    └── ...
```

## Session File Details

### File Format

**Location:** `config_pose/session_YYYYMMDD_HHMMSS.json`

**Structure:**
```json
{
  "session_id": "20260316_142345",
  "robot_type": "bimanual_ur",
  "timestamp_start": "2026-03-16T14:23:45.123456",
  "timestamp_start_unix": 1742217825.123456,
  "timestamp_stop": "2026-03-16T14:35:12.987654",
  "timestamp_stop_unix": 1742218512.987654,
  "config_start": {
    "robot_left": [joint1, joint2, ...],
    "robot_right": [joint1, joint2, ...],
    "gello_left": [joint1, joint2, ...],
    "gello_right": [joint1, joint2, ...]
  },
  "config_stop": {
    "robot_left": [joint1, joint2, ...],
    "robot_right": [joint1, joint2, ...],
    "gello_left": [joint1, joint2, ...],
    "gello_right": [joint1, joint2, ...]
  }
}
```

### Accessing Data

```python
import json

# Load session
with open('config_pose/session_20260316_142345.json') as f:
    session = json.load(f)

# Access start config
robot_left_start = session['config_start']['robot_left']

# Access stop config
robot_left_stop = session['config_stop']['robot_left']

# Access timestamps
start_time = session['timestamp_start']  # ISO string
stop_time = session['timestamp_stop']    # ISO string
```

## Integration Points

### With existing run_env.py

The automatic capture system wraps `experiments/run_env.py` as a subprocess:

```python
# Inside run_with_pose_capture.py:
process = subprocess.Popen([
    'python3',
    'experiments/run_env.py',
    '--bimanual',
    '--use-relative-mode',
    # ... other args
])

# After pose capture, runs subprocess
# When user presses Ctrl+C, signal handler triggers capture_pose()
# Then gracefully terminates subprocess
```

**Important:** The original `run_env.py` code is NOT modified in any way. We only:
1. Call it as a subprocess
2. Capture poses before/after the subprocess
3. Save results to a separate folder

### With robot/GELLO classes

All capture functions use the standard APIs:

```python
# From robot.py protocol:
robot.get_joint_state()  # Returns array of joint positions

# From gello_agent.py:
agent = GelloAgent(port="/dev/...")
agent.get_state()  # Returns joint positions

# In pose_capture_helper.py, we just read these
```

No modifications to robot code needed!

### With existing experiments

The system works alongside existing code:

```bash
# Old way (no capture):
python3 experiments/run_env.py ...

# New way (with auto capture):
python3 scripts/run_with_pose_capture.py ...
# Internally calls: experiments/run_env.py

# Both can coexist, choose which to use per session
```

## Performance Characteristics

### Capture Time

- **Time to capture START config:** ~200-500ms
  - Depends on robot type (UR faster than XArm)
  - Depends on number of devices (bimanual slower)

- **Time to capture STOP config:** ~200-500ms
  - Same as START

- **Total overhead:** ~400-1000ms (less than 1 second)

### Storage

- **File size per session:** ~1-2 KB
  - Typical session: 1.5 KB
  - Multiple sessions accumulate slowly

### Session Duration

- **Minimum:** Immediately create START, then immediately STOP
  - Creates valid session file with both configs
  - Use case: Verify poses are captured correctly
  
- **Maximum:** Run for hours
  - No time limit on teleoperation
  - Only saves START timestamp and STOP timestamp
  - No runtime overhead

## System State Machine

```
                    ┌─────────────────┐
                    │   Not Started   │
                    └────────┬────────┘
                             │
                  (run with_pose_capture.py)
                             │
                    ┌────────▼────────┐
                    │ Capturing START │
                    │   (reading pose)│
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  START captured │
                    │ Ready to teleoperate
                    └────────┬────────┘
                             │
                   (spawn run_env.py)
                             │
                    ┌────────▼────────┐
                    │  Teloperating   │
                    │  (normal ops)   │
                    └────────┬────────┘
                             │
                  (Ctrl+C / END signal)
                             │
                    ┌────────▼────────┐
                    │ Capturing STOP  │
                    │   (reading pose)│
                    └────────┬────────┘
                             │
                    ┌────────▼─────────┐
                    │ Session Complete │
                    │ File saved to:   │
                    │ config_pose/...  │
                    └──────────────────┘
```

## Error Handling

### If START capture fails:
- Aborts before starting teleoperation
- No session file created
- User can retry

### If teleoperation crashes:
- Subprocess terminates
- Signal handler attempts to capture STOP
- Saves partial session (with START, missing STOP)
- User can try again or manually capture STOP

### If STOP capture fails:
- Session partially saved (with START config)
- Error message printed
- User can manually capture STOP later with `capture_pose.py --capture-type=stop --session-id=...`

## Compatibility

- **Python versions:** 3.7+
- **Robot types:** UR, XArm, Panda, Bimanual (any combination)
- **GELLO types:** DynamixelRobot (via GELLO agent)
- **Operating systems:** Linux, macOS (Windows untested)

## Deprecation Notes

Older scripts for reference only:
- `capture_start.py` - deprecated in favor of `capture_pose.py --capture-type=start`
- `capture_stop.py` - deprecated in favor of `capture_pose.py --capture-type=stop`
- `save_calibration_pose.py` - older manual calibration tool, kept for reference

Use unified `capture_pose.py` for all manual capture needs.

---

**Key Principles:**
1. Single session = One JSON file (with both START and STOP)
2. Automatic recommended for normal teleoperation
3. Manual capture available for special cases
4. All existing code remains untouched
5. Non-invasive integration approach
