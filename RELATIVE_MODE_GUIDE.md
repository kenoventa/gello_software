# GELLO-UR Teleoperation: Absolute vs Relative Mode Analysis

## Problem Statement

Your UR robot is constrained by a safety cage and cannot reach the canonical joint configuration that GELLO expects at startup. The current teleoperation system attempts to move the UR robot to match GELLO's absolute joint positions, which can cause it to move toward the cage and risk collision.

**Your specific case:**
- Calibrated offsets expect: `(0, -π/2, π/2, -π/2, -π/2, 0)` radians
- UR robot cannot reach this configuration due to cage constraints
- Robot attempts to move there anyway, creating collision risk

## Current Architecture (ABSOLUTE MODE)

### Control Flow Chain

```
experiments/run_env.py
├─ Creates RobotEnv(ZMQClientRobot)  [connects to UR server]
├─ Creates GelloAgent(port)           [reads GELLO encoders]
└─ Calls run_control_loop()
   │
   └─ Main Loop (100 Hz typical):
      ├─ action = agent.act(obs)
      │  └─ GelloAgent.act() returns CURRENT GELLO POSITION (absolute)
      │
      ├─ env.step(action)
      │  └─ robot.command_joint_state(action)
      │     └─ URRobot.command_joint_state(action)
      │        └─ self.robot.servoJ(action[:6], ...)  [ABSOLUTE servo command]
      │
      └─ Update obs = env.get_obs()
```

### How GELLO Reads Its Position

**File:** `gello/robots/dynamixel.py`

```python
def get_joint_state(self) -> np.ndarray:
    # Read raw encoder values from Dynamixel motors
    raw_pos = self._driver.get_joints()
    
    # Apply calibration: (raw - offset) * sign
    pos = (raw_pos - self._joint_offsets) * self._joint_signs
    
    return pos  # Returns ABSOLUTE joint angles in radians
```

The offsets are calibrated via `scripts/gello_get_offset.py` and ensure that when GELLO is in a known physical configuration, the reported angles are correct.

### Where Absolute Commands Are Sent

**File:** `gello/robots/ur.py` (lines 64-70)

```python
def command_joint_state(self, joint_state: np.ndarray) -> None:
    velocity = 0.01
    acceleration = 0.01
    dt = 1.0 / 500  # 2ms
    lookahead_time = 0.2
    gain = 100

    robot_joints = joint_state[:6]
    t_start = self.robot.initPeriod()
    self.robot.servoJ(
        robot_joints,        # ← ABSOLUTE joint targets
        velocity, acceleration, dt, lookahead_time, gain
    )
    self.robot.waitPeriod(t_start)
```

**Key Point:** `servoJ()` is an ABSOLUTE position servo. It commands the robot to move to the specified joint configuration, regardless of the current pose.

### The Problem

When you start teleoperation:

1. GELLO is in some physical pose (e.g., hand on user's shoulder)
2. GELLO reports its position (e.g., `[0.5, -1.0, 1.5, -1.2, -1.4, 0.1]`)
3. This becomes the ACTION sent to UR
4. UR tries to move to `[0.5, -1.0, 1.5, -1.2, -1.4, 0.1]` via `servoJ()`
5. But UR cannot reach certain angles due to cage
6. UR moves **toward** that configuration, potentially hitting the cage

## Solution: Relative Mode

Instead of commanding absolute positions, implement **relative control**:

```
delta = GELLO_current - GELLO_initial
UR_target = UR_initial + delta
```

### How It Works

1. **Initialization (first act() call):**
   - Capture and store initial GELLO position
   - Capture and store initial UR position (its CURRENT safe pose)

2. **Steady State (subsequent act() calls):**
   - Read current GELLO position
   - Compute: `delta = current_gello - initial_gello`
   - Return: `UR_target = initial_ur + delta`

3. **Result:**
   - UR only moves relative to its starting position
   - UR never tries to reach GELLO's absolute configuration
   - Safe even if UR cannot reach GELLO's initial pose
   - Preserves teleoperative motion mapping

### Example Scenario

**Initial state (cage constraint, joint 0 limited to -20°):**
- GELLO position: `[0.5, -1.0, 1.5, -1.2, -1.4, 0.1]`
- UR position: `[-0.35, -1.5, 1.2, -1.5, -1.5, 0.0]` (stuck in corner)

**When you move hand forward (increases joint 1):**
- New GELLO position: `[0.5, -0.5, 1.5, -1.2, -1.4, 0.1]`
- Delta: `[0, +0.5, 0, 0, 0, 0]`
- UR target: `[-0.35, -1.0, 1.2, -1.5, -1.5, 0.0]` (moves safely)

## Implementation

### New File: `gello/agents/relative_agent.py`

Created a `RelativeAgent` wrapper that:
- Wraps any underlying agent (typically `GelloAgent`)
- Captures initial poses on first `act()` call
- Returns relative commands: `initial_ur + (current_gello - initial_gello)`

### Modified: `experiments/run_env.py`

Added:
- **Flag:** `--use-relative-mode` (default False)
- **Logic:** Wraps GelloAgent with RelativeAgent when flag is set
- **Support:** Works for both single-arm and bimanual configurations

## Usage

### Run with Relative Mode (RECOMMENDED FOR YOUR SETUP)

```bash
# Terminal 1: Start the UR server (robot at safe position)
python experiments/launch_nodes.py --robot ur

# Terminal 2: Start relative mode teleoperation
python experiments/run_env.py --agent=gello --use-relative-mode
```

### Run with Absolute Mode (Original Behavior)

```bash
# Terminal 1: Start the UR server
python experiments/launch_nodes.py --robot ur

# Terminal 2: Start absolute mode (default)
python experiments/run_env.py --agent=gello
```

## Important Notes for Your Setup

### 1. Starting Position Matters

With relative mode, **your UR starting position is critical**. The robot will only move relative to where it starts.

**Procedure:**
1. Use teach pendant or freedrive mode to place UR in a safe, reachable configuration
2. Start the server: `python experiments/launch_nodes.py --robot ur`
3. Start relative mode teleoperation: `python experiments/run_env.py --agent=gello --use-relative-mode`
4. RelativeAgent will capture this starting position automatically

### 2. Offset Calibration Still Needed

You still need accurate GELLO offsets for smooth teleoperation. The relative mode just adds safety:

```bash
python scripts/gello_get_offset.py \
    --start-joints 0 -1.57 1.57 -1.57 -1.57 0 \
    --joint-signs 1 1 -1 1 1 1 \
    --port /dev/serial/by-id/usb-FTDI_USB__-__Serial_Converter_FT7WBG6
```

This is still correct because the offsets are internal to GELLO and independent of UR.

### 3. Motion Range

With relative mode, the maximum UR motion range is limited by:
- The reachable space around the initial UR position
- The range of GELLO motion from its initial position

For example, if UR starts at joint 1 = -1.5 rad, and its joint limit is -2.0 to -1.0 rad, then GELLO joint 1 can only move ±0.5 rad from its initial position without hitting limits.

### 4. Optional: Override Initial UR Pose

If you want to use a different initial pose than where the robot currently is, you can use the existing `--start-joints` flag (though this is for reset reference, not initial relative pose):

```bash
python experiments/run_env.py --agent=gello --use-relative-mode --start-joints "-1.5 -1.5 1.2 -1.5 -1.5 0"
```

## Technical Details: Why This Works

### Preserves Mapping
- User moves GELLO in teleoperation → operator makes change in workspace
- Delta captures that change
- Delta applied to UR's current position → UR makes equivalent change in workspace
- **Result:** Kinesthetic mapping is preserved even with offset initial poses

### Diagram of Motion Flow

```
User moves hand:
  GELLO physical motion → GELLO readings change

Current system (absolute):
  Action = GELLO reading
  UR moves to match GELLO reading (bad if unreachable)

Proposed system (relative):
  Delta = GELLO reading - GELLO initial reading
  Action = UR initial + Delta
  UR moves by same amount as GELLO (safe and natural)
```

## Files Modified

1. **gello/agents/relative_agent.py** (NEW)
   - RelativeAgent wrapper class
   - Handles relative control computation
   - Tracks initial poses

2. **experiments/run_env.py**
   - Added `use_relative_mode` CLI flag
   - Conditional wrapping of GelloAgent with RelativeAgent
   - Support for bimanual setup

## Troubleshooting

### "WARNING: Large joint position differences detected"

This warning appears when the initial GELLO and UR poses are very different. This is **expected and normal** in relative mode. The relative agent will initialize anyway. You may see this warning when:
- UR is stuck in corner due to cage
- GELLO is in operator's hand (not canonical pose)

**Action:** Just proceed (continue the teleoperation). This is why relative mode exists!

### Robot moves slowly or inconsistently

**Causes:**
- GELLO offsets are inaccurate (calibrate with `gello_get_offset.py`)
- UR servo parameters need tuning (velocity, acceleration in `ur.py`)
- Motion is hitting joint limits

**Check:**
1. Run single-agent test first: move UR directly, verify smooth motion
2. Verify GELLO readings: `python scripts/gello_get_offset.py` and check live values
3. Check UR joint limits in Polyscope

## Advantages of This Implementation

1. **Minimal Code Change:** Wrapper pattern leverages existing architecture
2. **Backward Compatible:** `--use-relative-mode` is optional
3. **Safe:** Robot doesn't try to reach unreachable absolute poses
4. **Natural:** Relative motion mapping is familiar to teleoperation users
5. **Bimanual Support:** Works with existing bimanual configuration
6. **Debugging:** Can switch modes easily to compare behavior

## Future Enhancements (Optional)

1. **Null Space Recovery:** If joint limits approached, move in null space to maintain task space
2. **Adaptive Gain:** Scale delta based on distance to limits
3. **Singularity Avoidance:** Check for approaching singularities
4. **Safe Zone Definition:** Allow user to define safe position bounds
