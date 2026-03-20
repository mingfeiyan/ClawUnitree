# DimOS + Unitree Go2 Architecture Guide

## 1. Project Structure

```
openclawunitree/
└── dimos/                          # DimOS v0.0.11 - Dimensional Robotics OS
    ├── dimos/                      # Main package
    │   ├── core/                   # Framework runtime
    │   │   ├── blueprints.py       # Module composition & wiring
    │   │   ├── module.py           # Base Module class
    │   │   ├── worker.py           # Subprocess workers for modules
    │   │   ├── worker_manager.py   # Manages worker pool
    │   │   ├── module_coordinator.py # Deploys & starts modules
    │   │   ├── stream.py           # Reactive In/Out streams
    │   │   ├── transport.py        # LCM & shared memory transports
    │   │   └── global_config.py    # Config from .env
    │   │
    │   ├── robot/                  # Robot implementations
    │   │   ├── unitree/            # Unitree robots
    │   │   │   ├── connection.py   # WebRTC connection layer
    │   │   │   ├── go2/            # Go2 specific
    │   │   │   │   ├── connection.py  # GO2Connection module
    │   │   │   │   └── blueprints/    # Pre-built module graphs
    │   │   │   ├── g1/             # G1 humanoid
    │   │   │   └── b1/             # B1 industrial
    │   │   └── drone/              # Drone support
    │   │
    │   ├── agents/                 # AI agent framework
    │   ├── mapping/                # SLAM, voxel grid, costmaps
    │   ├── navigation/             # Path planning (A*, wavefront)
    │   ├── perception/             # Vision, depth, object detection
    │   ├── web/                    # Web UI
    │   │   ├── websocket_vis/      # WebSocket server (port 7779)
    │   │   └── command-center-extension/  # React frontend
    │   │
    │   ├── models/                 # ML models (CLIP, YOLO, SAM2, VLMs)
    │   ├── msgs/                   # Message types (ROS-like)
    │   ├── protocol/               # RPC framework
    │   └── visualization/          # Rerun integration
    │
    ├── .venv/                      # Python 3.12 virtualenv
    │   └── .../unitree_webrtc_connect/  # WebRTC library (patched)
    │
    └── .env                        # Config (ROBOT_IP, API keys)
```

---

## 2. Algorithms & Models

### SLAM / Mapping

| Component | Algorithm | Library |
|-----------|-----------|---------|
| Visual SLAM | ZED SDK built-in (stereo + IMU fusion) | `pyzed.sl` |
| Voxel Mapping | Sparse VoxelBlockGrid (0.05m voxels, GPU) | `open3d` |
| Costmap | 2D occupancy grid projected from voxel map | Custom |

For the Go2 EDU (no ZED camera), localization comes from the robot's built-in odometry via WebRTC, and the lidar point cloud is used for mapping.

### Depth Estimation

| Sensor | Method | Resolution |
|--------|--------|------------|
| ZED Camera | Neural stereo depth (proprietary NN) | 1280x720 @15fps |
| RealSense | Structured-light stereo | 848x480 @15fps |
| Go2 built-in | LiDAR (no depth camera) | Point cloud |

No monocular depth models (DepthAnything/MiDaS/ZoeDepth) — relies on hardware sensors.

### Vision / Vision-Language Models

| Model | Purpose | Location |
|-------|---------|----------|
| CLIP (ViT-B/32) | Image-text embeddings, semantic matching | `models/embedding/clip.py` |
| MobileClip | Lightweight mobile embeddings | `models/embedding/mobileclip.py` |
| Moondream2 | On-device vision-language queries | `models/vl/moondream.py` |
| Florence-2 (Microsoft) | Image captioning, visual grounding | `models/vl/florence.py` |
| GPT-4o-mini | VLM via OpenAI API | `models/vl/openai.py` |
| Qwen2.5-VL-72B | VLM via API | `models/vl/qwen.py` |

### Object Detection

| Model | Purpose | Location |
|-------|---------|----------|
| YOLOv8+ | General object detection | `perception/detection/detectors/yolo.py` |
| YOLOe | Enhanced detection with prompts | `perception/detection/detectors/yoloe.py` |
| OSNet (torchreid) | Person re-identification | `perception/detection/reid/` |

### Segmentation & Tracking

| Model | Purpose | Location |
|-------|---------|----------|
| SAM2 + EdgeTAM | Video object segmentation & tracking | `models/segmentation/edge_tam.py` |
| Kalman filter | Object tracking across frames | `perception/object_tracker*.py` |

---

## 3. Module Wiring & Data Flow

### How Streams Connect

Modules declare typed `In[T]` and `Out[T]` fields. The blueprint system **auto-connects** them by matching name + type:

```python
# GO2Connection declares:
lidar: Out[PointCloud2]       # publishes lidar data

# VoxelGridMapper declares:
lidar: In[PointCloud2]        # subscribes to lidar data

# Same name ("lidar") + same type (PointCloud2) → auto-connected via LCMTransport
```

### Transport Types

| Stream | Transport | Why |
|--------|-----------|-----|
| `color_image` | pSHMTransport (shared memory) | High bandwidth video frames |
| `lidar`, `odom`, `cmd_vel` | LCMTransport | Serialized, type-safe messages |
| `gps_location` | pLCMTransport | Pickled Python objects |

### Go2 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Go2 Robot (WebRTC)                           │
│   Camera  ──►  video stream                                        │
│   LiDAR   ──►  lidar stream                                        │
│   IMU     ──►  odom stream                                         │
└──────┬──────────────┬──────────────┬────────────────────────────────┘
       │              │              │
       ▼              ▼              ▼
┌──────────────────────────────────────────┐
│         GO2Connection (Module)           │
│  Out: color_image  lidar  odom           │
│  In:  cmd_vel                            │
└───┬──────────┬────────┬──────────────────┘
    │          │        │
    │          │        ├──────────────────────────┐
    │          │        │                          │
    │          ▼        ▼                          ▼
    │   ┌─────────────────────┐          ┌──────────────────┐
    │   │  VoxelGridMapper    │          │ WebsocketVisModule│
    │   │  In: lidar          │          │ In: odom          │
    │   │  Out: global_map    │          │ In: global_costmap│
    │   └────────┬────────────┘          │ In: path          │
    │            │                       │                   │
    │            ▼                       │ Out: goal_request │
    │   ┌─────────────────────┐          │ Out: cmd_vel      │
    │   │    CostMapper       │          │ Out: explore_cmd  │
    │   │  In: global_map     │          └─┬──────────┬──────┘
    │   │  Out: global_costmap│───────────►│          │
    │   └─────────────────────┘   costmap  │          │
    │                                      │          │
    │   ┌─────────────────────────────┐    │          │
    │   │  ReplanningAStarPlanner     │◄───┘          │
    │   │  In: global_costmap         │  goal_request │
    │   │  In: goal_request           │               │
    │   │  In: odom                   │               │
    │   │  Out: cmd_vel ──────────────┼───────────────┘
    │   │  Out: path                  │        cmd_vel
    │   └─────────────────────────────┘
    │
    ▼
┌──────────────────┐
│  RerunBridge     │  (native visualization)
│  In: color_image │
│  In: lidar, odom │
└──────────────────┘
```

### The Pipeline Step by Step

1. **Robot → GO2Connection**: WebRTC subscriptions push lidar/odom/video as RxPY observables
2. **GO2Connection → VoxelGridMapper**: Lidar point clouds build a 3D voxel map (Open3D, 0.05m voxels)
3. **VoxelGridMapper → CostMapper**: Voxel grid projected to 2D occupancy grid
4. **CostMapper → A\* Planner**: Costmap + goal → planned path + velocity commands
5. **A\* Planner → GO2Connection**: Twist velocity commands sent back to robot via WebRTC
6. **Everything → WebsocketVisModule**: Odom, costmap, path streamed to browser at `localhost:7779`
7. **Browser → WebsocketVisModule → Planner**: Click events become goal_request, keyboard becomes cmd_vel

### Blueprint Definition

```python
# The smart Go2 blueprint wires everything together:
unitree_go2 = autoconnect(
    unitree_go2_basic,                    # GO2Connection + WebUI + Rerun
    voxel_mapper(voxel_size=0.1),         # LiDAR → 3D voxel grid
    cost_mapper(),                        # Voxel grid → 2D costmap
    replanning_a_star_planner(),          # Costmap + goals → path + cmd_vel
    wavefront_frontier_explorer(),        # Autonomous frontier exploration
    PatrollingModule.blueprint(),         # Patrol waypoints
)
```

The `autoconnect()` function handles all the wiring — it matches `Out[T]` to `In[T]` by name and type across all modules.

---

## 4. OpenClaw + Unitree Integration

### Architecture

```
┌─────────────────────────────────────────────┐
│           Agent Layer (choose one)           │
│  OpenClaw  │  Claude Code  │  Other Agents   │
└──────────────────┬──────────────────────────┘
                   │  MCP Protocol (HTTP)
                   │  localhost:9990/mcp
                   ▼
┌─────────────────────────────────────────────┐
│              DimOS Framework                 │
│  Skills, Tools, Streams, Module Graphs       │
└──────────────────┬──────────────────────────┘
                   │  WebRTC / ROS / SDK
                   ▼
┌─────────────────────────────────────────────┐
│        Unitree Go2 / G1 / B1 Robot          │
└─────────────────────────────────────────────┘
```

### How It Works

OpenClaw is an **AI agent framework** (like Claude Code) that controls robots through DimOS. The integration happens via:

1. **MCP Server** (port 9990) — DimOS exposes robot skills as MCP tools that any agent can discover and call over HTTP
2. **AGENTS.md** — Documentation that tells agents how to use DimOS's CLI and MCP interfaces
3. **Skills** — Robot capabilities (move, observe, navigate) are wrapped as callable skills

### DimOS is the Middleware

DimOS is agent-agnostic and robot-agnostic:

- **Agent side**: OpenClaw, Claude Code, or any MCP-compatible agent
- **Robot side**: Unitree Go2/G1/B1, drones, XArm, Piper manipulators
- **DimOS handles**: Perception, mapping, navigation, and exposes it all as callable skills

### Manipulation Support

DimOS has built-in support for manipulation hardware:

| Manipulator | DOF | Location |
|-------------|-----|----------|
| XArm 7/6 | 6-7 DOF | `hardware/manipulators/xarm/` |
| Piper (AgileX) | 6 DOF | `hardware/manipulators/piper/` |

Gripper control is available via `read_gripper_position()` / `write_gripper_position()` in the manipulator spec.
