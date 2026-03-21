# CLAUDE.md — Script to Voice Generator

A GUI desktop app that converts formatted script files into fully voiced audio using **ElevenLabs V3 TTS** (cloud API). Written in Python with tkinter/ttkbootstrap. Made by Reactorcore.

---

## Running the app

```
python app.py
```

Requirements: `pip install -r requirements.txt` (ttkbootstrap, requests). FFMPEG must be on system PATH. An ElevenLabs API key must be configured in Tab 4.

Build to exe: `build_exe.bat` (uses PyInstaller).

---

## File structure

| File | Purpose |
|------|---------|
| `app.py` | Entry point — calls `gui.main()` |
| `gui.py` | `ScriptToVoiceGUI` class + `main()`. Assembles GUI from mixin classes |
| `gui_tab1.py` | Tab 1 builder — script loading, parse log |
| `gui_tab2.py` | Tab 2 builder — per-speaker voice/effect panels, SFX section |
| `gui_tab2_state.py` | `Tab2StateMixin` — state/event methods for Tab 2 (extracted to keep file sizes manageable) |
| `gui_tab3.py` | Tab 3 builder — generation summary, project name, output folder |
| `gui_tab4.py` | Tab 4 builder — ElevenLabs API key, generation options, silence trim, pause settings, contextual modifiers, inner thoughts |
| `gui_handlers.py` | Button click handlers (open script, reload, continue, help, test voice, API key save, usage stats, etc.) |
| `gui_generation.py` | `GenerationMixin` — background generation thread, progress, cancel |
| `gui_theme.py` | ttkbootstrap theme application helpers |
| `script_parser.py` | Parses `.txt`/`.md` script files into `ParseResult` |
| `audio_generator.py` | ElevenLabs V3 API calls, FFMPEG audio effect chains, yell impact, peak normalize |
| `audio_merger.py` | Merges clips into final audio with smart punctuation-based pauses |
| `file_manager.py` | Filename builders, folder creation, reference sheet dispatch |
| `reference_writer.py` | Writes `project_reference.txt` — speaker profiles, line list, generation summary |
| `character_profiles.py` | Load/save/update `character_profiles.json` |
| `config_manager.py` | Load/save/validate `config.json`, pause values, inner thoughts filter, silence trim, API key, generation options |
| `config.py` | Constants: theme colors, effect filter chains, ElevenLabs constants, defaults |
| `data_models.py` | Dataclasses: `ParsedLine`, `SpeakerProfile`, `ParseResult`, etc. |

### Persistent data files (auto-created on first launch)

- `config.json` — UI state, ElevenLabs API key, pause durations, contextual modifiers, inner thoughts settings, silence trim settings, generation options
- `character_profiles.json` — Per-speaker voice/effect profiles, auto-saved on every change

### Output structure

```
output_folder/
├── clips_clean/       ← Raw TTS clips (no effects) — .mp3 (ElevenLabs returns MP3 directly)
├── clips_effect/      ← Effects-processed + peak-normalized mp3s
├── sfx/               ← FFMPEG-processed SFX copies (mp3, only created when effects are active)
├── !project_merged_pure.mp3
├── !project_merged_loudnorm.mp3
└── project_reference.txt
```

### Other folders

- `output_test/` — Test voice preview clips (written by Test Voice button in Tab 2)
- `!dev/` — Planning documents and implementation decisions log

### `!docs/` folder

User-facing documentation and resources, organized into three subfolders:

**`!docs/guides/`** — In-depth guides shipped with the app:

| File | Contents |
|------|----------|
| `Script_Writing_Guide.md` | How to write scripts that work well with TTS: pacing with punctuation and pauses, using audio tags, using effects as character design, sound channels, inner thoughts, and AI-assisted script writing workflow |
| `Audio_Effects_Guide.md` | Full reference for all effects (Radio, Reverb, Distortion, Telephone, Robot Voice, Cheap Mic, Pitch Shift, and more): what each preset level sounds like, recommended character type combinations, the FFMPEG processing pipeline order, Yell Impact explained, troubleshooting |

**`!docs/example_scripts/`** — Ready-to-load `.md` script files demonstrating different use cases.

**`!docs/prompt_templates/`** — AI prompt templates for generating scripts with a language model.

---

## Architecture

`ScriptToVoiceGUI` inherits from six mixin classes:

```
ScriptToVoiceGUI(Tab1Builder, Tab2Builder, Tab2StateMixin, Tab3Builder, Tab4Builder, GUIHandlers, GenerationMixin)
```

The GUI class holds all shared state (tkinter vars, config_manager, char_profiles, audio_gen, parse_result, etc.).

### Tab flow

1. **Tab 1 — Load Script**: User picks a `.txt`/`.md` file → `script_parser.py` parses it → errors shown in log → `Continue →` advances to Tab 2
2. **Tab 2 — Voice Settings**: Dynamic speaker panels (one per detected speaker ID). Voice list is fetched from ElevenLabs API on startup. Auto-saves to `character_profiles.json` on every change.
3. **Tab 3 — Generate**: User sets project name + output folder → clicks Generate All → background thread runs the full pipeline
4. **Tab 4 — Settings**: ElevenLabs API key entry, generation options, silence trim, pause durations, contextual modifiers, inner thoughts effect presets

### Startup sequence

1. `ConfigManager` loads `config.json`
2. `AudioGenerator` is initialized; `set_api_key()` is called with the stored key
3. If key is present: `_load_voices_async()` is called (100ms defer) → fetches voices from ElevenLabs API → populates Tab 2 comboboxes
4. If key is absent: `_show_no_api_key_status()` is called → status bar prompts user to set key in Tab 4

### Generation pipeline

1. `script_parser.py` → `ParseResult` (list of `ParsedLine` objects)
2. Per dialogue line: `audio_generator.py` → ElevenLabs V3 API call → MP3 bytes → `clips_clean/`
3. Per dialogue line: `audio_generator.py` → FFMPEG effects pipeline → `clips_effect/`
4. Per dialogue line: `audio_generator.py` → peak normalize effect clip in-place
5. SFX files → FFMPEG effects (optional) → `sfx/`
6. `audio_merger.py` → stitch clips with silence segments → `merged_pure.mp3` + `merged_loudnorm.mp3`
7. `reference_writer.py` → write `project_reference.txt`

### Thread safety

Generation runs in `threading.Thread(daemon=True)`. All UI updates from the thread go through `root.after(0, callback)`. Generation settings are gathered into a plain dict on the main thread before the thread starts — the background thread never touches tkinter vars directly.

Voice loading (`_load_voices_async`) also runs in a background thread. Usage stats fetch (`on_get_usage_stats`) also runs in a background thread.

---

## Script format (key rules)

- Dialogue: `SpeakerID: Text` — speaker IDs max 20 chars, alphanumeric + spaces/hyphens/underscores (no `< > : " / \ | ? *`)
- Headings: `#` or `##` — not voiced, first `#` sets title
- Comments: `//` (inline or full line), `/* ... */` (multi-line)
- Pauses: `(1.5s)` or `(pause 2.0)` or `(0.8)` — any float in parens
- Sound effects: `{play filename.mp3, c1, loop}` / `{stop c1}` / `{stop all}`
- `[brackets]` in dialogue are **ElevenLabs V3 audio tags** — passed through to the API as-is for emotional/delivery direction. NOT stripped. NOT shown in reference sheet text.
- `//` after dialogue text starts inline comment (stripped) — requires whitespace before `//` so URLs are not accidentally stripped
- Inner thoughts: `((text))` wrapping an entire dialogue — detected and marked `is_inner_thought=True`; cannot be mixed with regular dialogue on the same line
- **Bold/italic NOT converted to SSML** — ElevenLabs V3 is not SSML-based. `**bold**`, `_italic_`, and `~~strikethrough~~` markers are all stripped from TTS text by the parser.

---

## Key constants (config.py)

- `MAX_SPEAKER_ID_LENGTH = 20`
- `MAX_PROJECT_NAME_LENGTH = 20`
- `MAX_LINE_CHARACTERS = 4000`
- `DEFAULT_VOICE = ""` (no default — fetched from ElevenLabs API at startup)
- `DEFAULT_VOLUME_PERCENT = 100`
- `EL_SPEED_MIN = 0.7`, `EL_SPEED_MAX = 1.2`, `EL_SPEED_DEFAULT = 1.0` — ElevenLabs native speed parameter
- `EL_SPEED_STEP = 0.05` — slider step
- `EL_STABILITY_MIN = 0.0`, `EL_STABILITY_MAX = 1.0`, `EL_STABILITY_DEFAULT = 0.5`
- `EL_SIMILARITY_MIN = 0.0`, `EL_SIMILARITY_MAX = 1.0`, `EL_SIMILARITY_DEFAULT = 0.75`
- `PITCH_MULTIPLIER_MIN = 0.5`, `PITCH_MULTIPLIER_MAX = 2.0`, `PITCH_MULTIPLIER_DEFAULT = 1.0` — FFMPEG rubberband pitch multiplier
- Output is always MP3 (ElevenLabs V3 returns MP3 directly — no WAV intermediate)
- Audio effects: `radio`, `reverb`, `distortion`, `telephone`, `robot_voice`, `cheap_mic`, `underwater`, `megaphone`, `worn_tape`, `intercom`, `alien`, `cave`, `pitch_shift`
  - Most have `off/mild/medium/strong` presets
  - `alien` uses named variants: `off/insectoid/dimensional/warble`
  - `cave` uses named variants: `off/tunnel/cave/abyss`
  - `pitch_shift` uses a float multiplier (not a preset string) for per-speaker use; SFX panel uses `off/mild/medium/strong` preset strings
- Boolean toggles: `fmsu` (brutal digital corruption), `reverse` (flip clip end-to-end) — on/off only
- Inner thoughts presets: `Whisper`, `Dreamlike`, `Dissociated`, `Custom`
- `FMSU_FILTER` — hardcoded filter string for the FMSU effect

### ElevenLabs API

- **Endpoint**: `POST /v1/text-to-speech/{voice_id}` with model `eleven_v3`
- **Voice list**: `GET /v1/voices` — fetched at startup, builds display strings as `"Name - Description  [voice_id]"`
- **Subscription info**: `GET /v1/user/subscription` — used by "Get Usage Stats" in Tab 4
- **HTTP library**: `requests` (no ElevenLabs SDK — lighter dependency)
- **Continuity**: `previous_request_ids` — up to 3 recent request IDs per speaker, tracked via `deque(maxlen=3)` in `gui_generation.py`
- **`generate_audio()` returns 3-tuple**: `(success: bool, error: str|None, request_id: str|None)`
- **API key storage**: `config.json` under `"elevenlabs_api_key"` key, managed by `ConfigManager`

### Per-speaker settings (generation dict keys)

- `voice_name` — ElevenLabs voice display string (name extracted at gather time)
- `voice_id` — raw ElevenLabs voice ID, extracted from display string bracket notation
- `speed_float` — ElevenLabs speed (0.7–1.2)
- `stability` — ElevenLabs stability (0.0–1.0)
- `similarity_boost` — ElevenLabs similarity boost (0.0–1.0)
- `pitch_multiplier` — FFMPEG rubberband pitch (0.5–2.0)
- `volume` — output level percent (5–100)
- `yell_impact` — negative int (0 to -80)
- `effects` — dict of effect name → preset string or float

---

## Key behaviors to know

- **Voice loading**: Fetched from ElevenLabs API via `audio_gen.fetch_voices()`. Returns list of `"Name - Description  [voice_id]"` display strings. Called in background thread 100ms after startup.
- **No voices without API key**: If `config.json` has no API key, voice comboboxes will be empty and a status message prompts the user to set the key in Tab 4.
- **API key save flow**: Tab 4 Save Key → `on_save_api_key()` in `gui_handlers.py` → saves to `config_manager` → calls `audio_gen.set_api_key()` → triggers `_load_voices_async()` → repopulates Tab 2 comboboxes.
- **Clip continuity**: `gui_generation.py` maintains `request_id_history = {}` (speaker_id → `deque(maxlen=3)`). Each successful `generate_audio()` call returns a `request_id`; this is appended to the deque and the list of up to 3 IDs is passed as `previous_request_ids` to the next call for that speaker.
- **Pitch shift**: Per-speaker pitch is a float multiplier (0.5–2.0) stored as `int*100` in a `tk.IntVar`. Converted to float at gather-time (`/ 100.0`). Applied via `rubberband=pitch=<multiplier>` FFMPEG filter. `pitch_multiplier = 1.0` = no shift.
- **No SSML**: ElevenLabs V3 does not use SSML. Bold/italic/strikethrough are all stripped silently.
- **Audio tags**: `[brackets]` in dialogue pass through to the API unchanged. They are stripped from spoken text for the reference sheet only (via `_strip_brackets` called only in the reference writer, not the parser).
- **Yell Impact**: Applied only when the entire spoken text is a single word with `!` in trailing punctuation (e.g. `YES!`, `NO?!`). Formula: `yell_rate = max(0.7, min(1.2, speaking_rate * (1.0 + yell_impact/100.0)))` — clamped to ElevenLabs speed range.
- **Volume (Level slider)**: Range 5%–100%, step 5. 100% = full normalized output. Capped at 100 in the pipeline. Alimiter always fires before the final volume multiply.
- **Cheap Mic default**: New speakers default to `cheap_mic = "mild"` (subtle realism effect).
- **Inner thoughts**: Lines where `is_inner_thought=True` get an extra FFMPEG filter stage (Stage 5.5) from `config_manager.get_inner_thoughts_filter()`.
- **Clip filenames**: `[project]_[linenum]_[speaker]_[content].mp3`, total max 70 chars.
- **Merged filenames**: `![project]_merged_[variant].mp3` (leading `!` puts them at top of folder listing).
- **Cancel**: Cooperative — sets `_gen_cancel_requested = True`, checked between clips. Current clip always completes.
- **SFX checkbox behavior**: The SFX checkbox in Tab 2 controls whether effects are *applied* to a file — unchecked means "use this file as-is", not "omit from merged audio". All found SFX files are always included in the merge.
- **Silence trim**: Default: `"beginning_end"`. Threshold: -35 dB. End trim uses `areverse → silenceremove → areverse` (avoids `stop_periods` streaming bug that prematurely cuts expressive voice tails). The "all" mode additionally applies mid-clip silence removal at -80 dB.
- **Peak normalization**: Separate two-pass after effects. Measures max peak via `volumedetect`, then applies linear gain to bring peak to 0 dBFS. Dynamics preserved. Applied to `clips_effect/` files in-place.
- **No Tab 5 / Voice Blender**: This is the ElevenLabs version — there is no local voice blending. Tab 5 has been removed entirely.

---

## GUI color palette (Ruby Gem dark theme)

The active theme is a ruby gem dark scheme defined in `config.py` under `APP_THEME["colors"]`. **All GUI code must use these values — no hardcoded hex colors from the old blue palette.**

### Rules for new GUI code

- **Use `APP_THEME["colors"]["<key>"]`** for all widget colors. The dict is imported at the top of each tab file.
- **Muted description labels** (secondary text, helper hints): use hardcoded `"#C49090"` (muted rose).
- **Very muted / disabled / hint text** (placeholder labels, unavailable-feature notices): use `"#7A4A4A"` (dark muted rose).
- **"No items" placeholder labels** that the user needs to actually read: use `"#C49090"` (not `"#7A4A4A"`), and font size ≥ 10.
- **tk.Text widgets** (log boxes, summary display): `bg=colors["inputbg"]`, `fg=colors["inputfg"]`, `selectbackground=colors["selectbg"]`.
- **Semantic log tag colors** — these are intentional and must NOT be changed to ruby equivalents:
  - `"#FF6B6B"` — error/missing
  - `"#69DB7C"` — success/found
  - `"#FFD43B"` — warning/stale

### Do NOT use these old blue values
`#74C0FC`, `#60CDFF`, `#8AAAC8`, `#555F6B`, `#141824`, `#C8D8F0`, `#2A3A5C` — all are remnants of the old navy theme.

### Tab header pattern
Tabs 1–4 all use a scrollable canvas wrapper + 18pt bold title label + 10pt subtitle. Any new tab must follow the same structure.

---

## Docs

- [README.md](README.md) — User-facing quick start guide
- [!docs/guides/Script_Writing_Guide.md](!docs/guides/Script_Writing_Guide.md) — Writing for TTS, pacing, audio tags, AI workflow
- [!docs/guides/Audio_Effects_Guide.md](!docs/guides/Audio_Effects_Guide.md) — Effects reference, pipeline, troubleshooting
- `!dev/11labs context docs/` — Context info about ElevenLabs API (V3-specific info and general ElevenLabs TTS info)
