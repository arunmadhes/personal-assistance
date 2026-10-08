# Irish Project Checklist

Last updated: 2026-04-22

This file is the working handoff note for future sessions. It captures the current architecture, known strengths, active issues, and the improvement checklist we can keep updating as work is completed.

## Current Architecture

### Entry Point

- `main.py`
  - Starts the Qt application.
  - Instantiates `IrishUI`.

### UI Layer

- `irish_ui.py`
  - Main PySide6 desktop application.
  - Owns:
    - multi-tab chat UI
    - task panel
    - voice button flow
    - market window / market desk views
    - token streaming display
    - speech playback triggering
  - Current architectural note:
    - This file is still doing both UI work and some business/service work.
    - It now routes requests through `services/agent_service.py`.
    - Market card/watchlist/chart payload fetching now routes through `services/market_service.py`.
    - Reusable market widgets now live in `ui/market_widgets.py`.
    - Market panel builder methods now live in `ui/market_panel.py`.
  - Current size:
    - about 1520 lines

### Core Orchestration Layer

- `agent.py`
  - Main rule-based orchestration and routing layer.
  - Handles:
    - message normalization
    - typo correction
    - intent clarification
    - command clarification
    - pending-action resolution
    - mode switching
    - direct-save flow
    - planner dispatch
    - intent routing to specialized agents
    - task lifecycle updates through `agent_manager`
  - Current architectural note:
    - Strong orchestrator already.
    - Still too large and should eventually be split into smaller modules.
  - Current size:
    - about 462 lines

### Specialized Agents

- `agents/ai_agent.py`
  - Builds conversational prompt
  - pulls recent memory
  - calls `ask_ai(...)`
  - stores final response in memory

- `agents/market_agent.py`
  - handles market questions, watchlist actions, journal actions, risk calculations
  - fetches quote snapshots
  - builds market reasoning prompt
  - stores market interactions in memory

- `agents/device_agent.py`
  - device command handling

- `agents/file_agent.py`
  - file save / output handling

- `agents/search_agent.py`
  - information search flow

- `agents/system_agent.py`
  - system command execution flow

### Memory Layer

- `memory.py`
  - Loads and saves conversation memory
  - Stores:
    - user
    - assistant
    - timestamp
    - mode
    - intent
    - source
  - Also stores learned command resolutions
  - Current architectural note:
    - Memory exists and is already in use.
    - Request memory is now loaded at the brain layer and passed downward.
    - Some specialized flows still need deeper service-level consolidation.

### AI Routing Layer

- `ai_router.py`
  - Switches between offline and online AI modes
  - fallback behavior when provider fails

- `offline_llm.py`
  - offline model path / local inference behavior

- `online_llm.py`
  - API provider-based online inference
  - currently supports configured providers

### Voice Layer

- `voice_input.py`
  - speech-to-text with Vosk
  - Current issue:
    - hardcoded model path
    - blocking listen loop without timeout/cancel path

- `voice_output.py`
  - queued text-to-speech playback

- `wake_word.py`
  - wake word detection with `openwakeword`
  - Current issue:
    - downloads models at import time

### Planning / Task Layer

- `planner.py`
  - creates multi-step plans

- `planner_executor.py`
  - executes plan steps

- `agent_manager.py`
  - task creation / update / shared context tracking

- `conversation_state.py`
  - pending clarification / confirmation state

### Market / Trading Layer

- `live_market_data.py`
  - live quotes / series fetches

- `market_data.py`
  - symbol extraction, timeframe extraction, market prompt building

- `watchlist.py`
  - watchlist persistence / summary

- `trade_journal.py`
  - trade journal entry and summary logic

- `indicators.py`
  - indicator calculations

## What Is Working Well

- [x] Qt desktop app bootstraps cleanly from `main.py`
- [x] Multi-tab chat UI exists
- [x] Streaming token updates are implemented
- [x] Task tracking panel exists
- [x] Intent routing exists
- [x] Clarification flow exists
- [x] Planning flow exists
- [x] Voice input/output exists
- [x] Market desk / watchlist / chart support exists
- [x] Memory storage exists
- [x] Memory is already used by `agents/ai_agent.py`
- [x] Market interactions are also stored in memory

## Confirmed Issues / Gaps

- [x] Replace hardcoded Vosk path in `voice_input.py`
- [x] Add timeout or cancellation support to `voice_input.listen()`
- [x] Stop relying on import-time wake-word model download in `wake_word.py`
- [x] Fix `memory.py` project root/data path handling
- [x] Remove or suppress the `openwakeword` TFLite warning by aligning `wake_word.py` with the installed runtime
- [x] Centralize memory/context ownership at the top-level brain layer
- [x] Stop having UI call `process_command(...)` directly
- [x] Stop having UI fetch market data directly
- [ ] Split `agent.py` into smaller architecture modules
- [x] Split `irish_ui.py` into smaller UI/service modules
- [ ] Add structured app/session context for future autonomous features

## Recommended Improvement Order

### Phase 1: Stability and Portability

- [x] Add config/env-based voice model path resolution
- [x] Add non-blocking or timed voice listening behavior
- [x] Fix memory data path ownership
- [x] Make wake-word setup safer and less fragile

### Phase 2: Brain Layer

- [x] Create `brain.py` or equivalent top-level decision layer
- [x] Define structured input object for requests
- [x] Load recent memory once in the brain layer
- [x] Pass context downward instead of each agent fetching its own memory independently
- [x] Add strategy decisions before routing

### Phase 3: Service Extraction

- [x] Create `services/agent_service.py`
- [x] Create `services/market_service.py`
- [x] Move non-UI execution logic out of `irish_ui.py`
- [x] Keep UI focused on rendering, user actions, and signals

### Phase 4: File Refactor

- [ ] Split `agent.py` into smaller modules such as:
  - `brain.py`
  - `router.py`
  - `executor.py`
  - `clarifications.py`
  - `memory_context.py`
- [ ] Split `irish_ui.py` into smaller modules such as:
  - `ui/main_window.py`
  - `ui/chat_panel.py`
  - `ui/market_panel.py`
  - `ui/chart_widget.py`

### Phase 5: Controlled Autonomy

- [ ] Add background jobs first, not full autonomy first
- [ ] Introduce cancellable market monitoring jobs
- [ ] Add scheduled refreshes/reminders
- [ ] Add explicit state/logging for autonomous behaviors
- [ ] Only then consider a broader autonomous loop

## Suggested Future Target Architecture

### UI

- `main.py`
- `ui/main_window.py`
- `ui/chat_panel.py`
- `ui/market_panel.py`
- `ui/chart_widget.py`

### Services

- `services/agent_service.py`
- `services/market_service.py`
- `services/voice_service.py`

### Core

- `core/brain.py`
- `core/router.py`
- `core/executor.py`
- `core/clarifications.py`
- `core/context.py`

### Existing Supporting Modules

- `memory.py`
- `agent_manager.py`
- `planner.py`
- `planner_executor.py`
- `live_market_data.py`
- `market_data.py`
- `watchlist.py`
- `trade_journal.py`

## Session Status

### Completed Today

- [x] Scanned the current project folder and confirmed there is no dependency manifest (`requirements.txt` or `pyproject.toml`) yet
- [x] Derived the active runtime dependency set from source imports
- [x] Installed missing Python modules required by the current codebase:
  `python-dotenv`, `openai`, `sounddevice`, `vosk`, `pyttsx3`, `openwakeword`, `ultralytics`, `opencv-python`
- [x] Ran a repo-wide module import smoke test and confirmed the main app modules now import successfully
- [x] Ran an offscreen Qt application startup smoke test and confirmed the UI boots successfully (`APP_SMOKE_OK exit=0`)
- [x] Fixed a startup blocker in `voice_output.py` by making TTS engine initialization lazy/fault-tolerant instead of crashing at import time
- [x] Scanned current folder and compared the codebase against the pasted review
- [x] Confirmed which suggestions are already partially implemented
- [x] Identified the highest-value next improvements
- [x] Created this persistent checklist/handoff note in the project folder
- [x] Completed Phase 1 stability fixes for voice path/config, voice timeout, wake-word startup safety, and memory path handling
- [x] Added `brain.py` and a structured request/context flow from UI -> agent router -> AI agent
- [x] Added pre-routing strategy decisions and introduced `services/agent_service.py` so the UI no longer calls `process_command(...)` directly
- [x] Added `services/market_service.py` so market card/watchlist/chart payload building no longer lives in `irish_ui.py`
- [x] Extracted market popup/chart widget classes into `ui/market_widgets.py` to start breaking up `irish_ui.py`
- [x] Extracted market panel builder methods into `ui/market_panel.py` so the main window owns less market-specific UI code
- [x] Fixed a `QLineEdit` import regression after the UI extraction
- [x] Fixed misrouting for normal informational prompts like “give some sample example for cte”

- [x] Updated `wake_word.py` to auto-select an installed inference runtime and avoid the TFLite warning path
- [x] Extracted chat/task UI lifecycle logic into `ui/chat_panel.py` so `irish_ui.py` is more focused
- [x] Extracted request-context helpers into `agent_request.py` and clarification heuristics into `agent_clarifications.py`
- [x] Extracted pending-action handling into `agent_pending.py` and intent dispatch into `agent_dispatch.py`

### Next Recommended Work Item

- [ ] Continue Phase 4:
  - begin breaking `agent.py` into smaller routing modules
  - reduce `agent.py` wrapper/helper duplication by calling extracted modules directly
  - consider moving planning/direct-save flows into focused modules

## How To Use This File In A New Chat

When starting a new conversation, refer to this file first and say:

"Continue from `PROJECT_CHECKLIST.md` and start with the next unchecked item."

That should make it easy to resume from the exact point where we left off.
