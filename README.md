# ClawUnitree

AI-powered autonomous control for Unitree Go2 robot dog, built on the [DimOS](https://github.com/dimensionalOS/dimos) robotics framework.

## What It Does

- **Natural language control** — Talk to the robot via text or voice ("go explore", "what do you see?", "follow that person")
- **Autonomous exploration** — Frontier-based navigation with real-time SLAM and obstacle avoidance
- **Spatial memory** — The robot remembers what it sees using CLIP embeddings + ChromaDB, queryable by text
- **Vision** — Camera observation with LLM-powered scene description
- **Person following** — Track and follow people using vision + re-identification

## Architecture

```
User (text/voice/web UI)
        │
        ▼
   Agent (Claude Sonnet) ──► Skills (move, observe, explore, recall, speak, ...)
        │
        ▼
   DimOS Framework ──► Perception, Mapping, Navigation, Memory
        │
        ▼
   Unitree Go2 (WebRTC) ──► Camera, LiDAR, IMU, Motor Control
```

The system is modular — modules communicate via typed reactive streams and are composed using blueprints. See [ARCHITECTURE.md](ARCHITECTURE.md) for the full technical breakdown.

## Quick Start

### Prerequisites

- Python 3.12+
- Unitree Go2 robot on the same network
- Anthropic API key (for the agent)

### Setup

```bash
cd dimos
cp .env.example .env   # Add ROBOT_IP, ANTHROPIC_API_KEY, OPENAI_API_KEY
source .venv/bin/activate
```

### Run

```bash
# Start the full agentic stack
dimos run unitree-go2-agentic -d

# Connect via web UI
open http://localhost:5555

# Or use the CLI
dimos humancli

# Stop
dimos stop
```

### Useful Flags

```bash
dimos run unitree-go2-agentic -d --new-memory   # Wipe spatial memory and start fresh
dimos run unitree-go2-agentic -d --disable SpeakSkill  # Disable a module
```

## Agent Skills

| Skill | Description |
|-------|-------------|
| `observe` | Capture camera frame, LLM describes what it sees |
| `begin_exploration` / `end_exploration` | Autonomous frontier-based exploration |
| `navigate_with_text` | Go to a location by text query ("go to the kitchen") |
| `recall_memory` | Search visual memory ("have you seen a rabbit?") |
| `tag_location` | Save current position with a name |
| `follow_person` / `stop_following` | Track and follow a person |
| `look_out_for` / `stop_looking_out` | Continuous monitoring for objects |
| `execute_sport_command` | Robot tricks (StandUp, Sit, FrontFlip, etc.) |
| `relative_move` | Move forward/left/rotate by specified amounts |
| `speak` | Text-to-speech through robot speakers |

## Key Components

| Component | Description |
|-----------|-------------|
| **GO2Connection** | WebRTC bridge to the robot (camera, lidar, odom, commands) |
| **VoxelGridMapper** | 3D voxel map from LiDAR (Open3D, GPU-accelerated) |
| **CostMapper** | 2D occupancy grid projected from voxel map |
| **ReplanningAStarPlanner** | A* path planning with stuck detection and replanning |
| **WavefrontFrontierExplorer** | Autonomous exploration using frontier detection |
| **SpatialMemory** | CLIP-based visual memory with ChromaDB persistence |
| **Agent** | LangGraph agent with Claude Sonnet powering natural language control |

## Visualization

- **Rerun** — Native 3D visualization of point clouds, camera, and robot pose (launches automatically)
- **Web UI** — Browser-based control at `http://localhost:5555`
- **WebSocket** — Map, path, and costmap streaming at `ws://localhost:7779`

## License

Apache License 2.0
