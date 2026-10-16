# Architecture Specification 🏛️

This document outlines the software engineering principles, design patterns, and internal data flows used in the **Fifine AmpliGame D6 Controller**.

---

## 1. High-Level System Flow

```
[ Physical Fifine D6 Pad ]
           ▲
           │ USB HID Reports (16-byte input, raw RGB image framing)
           ▼
     [ D6Engine ]  <-------------------------->  [ OBSClient ] (WebSocket RFC 4455)
           │
           ├──> [ StorageManager ]  -----> Atomic Filesystem Writes (os.replace)
           │
           ├──> [ ActionRegistry ]  -----> Command Pattern (80+ Action Handlers)
           │
           └──> [ Modular HTTP Router ]
                        ▲
                        │ REST JSON API & Server-Sent Updates
                        ▼
            [ Web Studio Pro UI ] (HTML5 / Vanilla CSS / ES Modules)
```

---

## 2. Design Patterns Utilized

### 2.1 Command Pattern (`src/actions/`)
All executable actions implement the `ActionCommand` abstract base class:

```python
class ActionCommand(ABC):
    @abstractmethod
    def execute(self, action: ActionModel, slot: Optional[int] = None, engine: Any = None) -> bool:
        pass
```

- **Registry Resolution ($O(1)$):**
  Actions are resolved instantly by action UUID or key type via `ActionRegistry.resolve(action_key)`.
- **Extensibility:**
  New actions (such as smart lighting, Twitch triggers, or custom shell scripts) can be added as isolated classes without modifying the core event loop.

### 2.2 Atomic Storage & Persistence (`src/models/storage.py`)
To prevent the notorious profile corruption common in the official vendor application:
1. Data is written to a temporary file (`tempfile.mkstemp`) on the exact same physical mount point.
2. The file descriptor is flushed and physically committed to disk using `os.fsync`.
3. If an existing profile file exists, it is copied to `.json.bak`.
4. The temporary file replaces the target atomically using `os.replace` (a POSIX atomic operation).

### 2.3 Image Dirty-Checking
Transmitting uncompressed bitmaps over USB for 15 individual LCD displays at 60 Hz causes excessive USB traffic. 
- The engine computes a content hash of each slot's visual representation (text, background, accent line, icon path).
- If the computed hash matches the cache, the USB transmission is skipped entirely.

---

## 3. Directory Structure

```text
fifine-ampligame-d6/
├── README.md               # User documentation, quickstart & feature overview
├── LICENSE                 # MIT Open Source License
├── requirements.txt        # Minimal Python dependencies (Pillow, hidapi)
├── run_cli.py              # Root CLI entrypoint
├── start_studio.sh         # One-click launch shell script
├── src/
│   ├── ampligame_d6.py     # Main CLI orchestrator
│   ├── d6_engine.py        # USB HID display driver & event dispatcher
│   ├── d6_studio_server.py # Lightweight HTTP REST daemon
│   ├── obs_client.py       # OBS Studio v5 WebSocket client
│   ├── fifine_guardian.py  # Health watchdog & reconnection monitor
│   ├── actions/            # Command Pattern action implementations
│   ├── models/             # Strongly typed dataclasses & atomic storage
│   ├── server/             # REST route handlers
│   └── studio/             # Web Studio frontend assets (HTML, CSS, ES modules)
├── sdk/
│   └── StreamDock/         # Embedded Python USB HID transport layer
├── docs/
│   ├── ARCHITECTURE.md     # Technical and structural documentation
│   └── PROGRESS.md         # Reverse engineering journey and timeline
└── tests/
    └── test_architecture.py# Automated verification test suite
```
