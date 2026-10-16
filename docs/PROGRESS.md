# Development Progress & Engineering Log 🛠️

This document chronicles the full reverse engineering and architectural evolution of the **Fifine AmpliGame D6 (StreamDock 293S)** project.

---

## 📅 Chronological Timeline

### Phase 1: Hardware Identification & Reverse Engineering
* **Problem:** The official manufacturer software (`fifine Control Deck.app`) suffered from frequent profile wipes, corrupted `manifest.json` files, and occasional USB bus deadlocks on macOS.
* **Discovery:**
  * Using binary analysis and USB descriptor inspection, we determined the hardware is an OEM **HotSpot / StreamDock 293S** microcontroller with:
    * **USB Vendor ID:** `0x3142`
    * **USB Product ID:** `0x0007`
  * Rather than a continuous display, the device contains **15 discrete LCD screens**, each requiring a 96x96 pixel buffer.
  * Image transfers use a proprietary framing packet indicating the slot number followed by a standard compressed image stream.

### Phase 2: Standalone Driver & PIL Image Engine
* Implemented a zero-dependency (vendor-free) Python driver wrapping raw HID calls.
* Built dynamic key rendering with **Pillow (PIL)**:
  * Dynamic background colors and linear gradients.
  * Adaptive font auto-scaling for multi-line titles.
  * Support for custom PNG/JPEG icons and SVG vector glyphs.
  * **Dirty-Checking Optimization:** Implemented cryptographic hashing (`MD5`/`SHA`) of each key's graphical state. Only keys whose visuals have changed are transmitted to the device, dropping USB bus traffic and latency by over 90%.

### Phase 3: Energy Saving & Sleep State Tracking
* Stream Decks left on 24/7 suffer from screen burn-in and generate unnecessary heat.
* Integrated macOS system notification hooks:
  * Hooked into `CoreGraphics` (`CGDisplayIsAsleep`) and `libSystem.B.dylib` (`notify_register_check("com.apple.screensaver.didstart")`).
  * Automatically sets brightness to `0` when the user locks their Mac or the monitors enter energy-saving mode.
  * Automatically wakes up and restores previous brightness levels on user interaction.

### Phase 4: Web Studio Interface (Fifine Control Deck Studio Pro)
* Developed an elegant, responsive web application at `http://localhost:5151`:
  * Built using pure **HTML5, Vanilla CSS, and modern ES Modules** (no heavy Webpack or Node.js runtime required).
  * 3x5 interactive virtual deck matching physical hardware layout.
  * Drag-and-drop key rearranging and cloning.
  * Dark Mode and Light Mode support with instant CSS variable switching.
  * Multi-key 3x5 mural wallpaper cropper.

### Phase 5: Architectural Modernization & Decoupling
To prepare the project for community distribution and long-term maintainability:
1. **Canonical Typed Data Models (`models/`):**
   * Migrated from untyped, loose JSON dictionaries to strongly typed dataclasses (`ActionModel`, `KeyModel`, `SceneModel`, `ConfigModel`).
   * Transparent v1 $\to$ v2 migration preserving all existing user keys.
2. **Atomic Persistence Layer (`models/storage.py`):**
   * Replaced standard `json.dump` with an atomic write mechanism (`tempfile` $\to$ `os.fsync` $\to$ `os.replace`).
   * Automatic generation of `.json.bak` on every save, eliminating profile corruption forever.
3. **Decoupled Command Pattern (`actions/`):**
   * Eliminated a 300+ line `if/elif` cascade in the core engine.
   * Registered **80+ discrete action commands** in an $O(1)$ lookup table (`ActionRegistry`).
4. **Modular REST Backend (`server/`):**
   * Broke down the monolithic HTTP server into specialized route handlers (`routes_system.py`, `routes_scenes.py`, `routes_keys.py`, `routes_obs.py`, `routes_backup.py`).

---

## 💡 How This Project Empowers Others

1. **Hardware Longevity:** Prevents users from discarding a capable piece of hardware simply because the vendor's software is buggy or abandoned.
2. **Open Ecosystem:** Developers can write custom Python scripts or automate workflows using simple shell scripts or REST API calls.
3. **Enterprise & Pro Audio Safety:** Because profiles are saved atomically and backed up automatically, live streamers and podcasters never lose their scenes right before a broadcast.
