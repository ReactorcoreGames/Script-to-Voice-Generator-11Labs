
![11labs stvg promo](https://github.com/user-attachments/assets/aa52afe2-9fc5-4fa1-958c-1c657011a31b)

# Script to Voice Generator — ElevenLabs V3 TTS

Welcome to any script writing author out there!

Convert formatted script files into fully voiced audio using **ElevenLabs V3 TTS** — a high-quality cloud text-to-speech engine with hundreds of voices and expressive audio tag support.

**Get it here** - https://reactorcore.itch.io/script-to-voice-generator-elevenlabs-v3

**Made by Reactorcore** — https://linktr.ee/reactorcore

---

<img width="1920" height="1020" alt="stvg 11labs screenshot (1)" src="https://github.com/user-attachments/assets/812f0640-fb17-47ba-880e-399dc1f5c6a2" />

<img width="1920" height="1020" alt="stvg 11labs screenshot (2)" src="https://github.com/user-attachments/assets/00aefc94-2eb3-40df-823b-5ccdebc91912" />

## What It Does

Script to Voice Generator reads a formatted `.txt` or `.md` script file and:

- Converts each dialogue line to speech using ElevenLabs V3 TTS (any voice from your ElevenLabs account).
- Saves individual clips for each line — both clean (TTS only) and effects-processed.
- Merges all clips into a single audio file, with smart pauses based on punctuation.
- Produces both a raw merge and a loudness-normalized merge.
- Generates a reference sheet listing every clip filename and its spoken text.

Multiple speakers are supported. Each speaker gets their own voice, pitch, speed,
stability, similarity, and audio effects settings, stored in `character_profiles.json` so
they're remembered between sessions.

---

## System Requirements

- **Windows 11** — built and tested on Windows 11.
- **Windows 10** — untested, use at your own risk.
- **Linux / macOS** — the compiled `.exe` is Windows-only. No Linux or macOS build is available.
- **Internet connection** — required for TTS generation (ElevenLabs is a cloud API).

---

## What You Need

**ElevenLabs API key** — Required for TTS generation.

1. Go to [elevenlabs.io](https://elevenlabs.io) and create an account.
2. Open the **Settings** tab (Tab 4) in the app.
3. Follow the instructions to create and paste your API key.

Free accounts get a limited monthly character quota. Paid plans increase it.

**FFMPEG** — Required for audio effects and merging.

- Automatic installer (recommended): https://reactorcore.itch.io/ffmpeg-to-path-installer
- Manual install: https://ffmpeg.org/download.html — add to system PATH after installing.

**Python 3.x** — Required to run from source (not needed if using the compiled .exe).
Use `build_exe.bat` to build to a single .exe in one click.

### A note on ElevenLabs pricing

ElevenLabs is a **cloud API service** — you pay per character of text generated. It is not cheap. The free tier gives you roughly **~10 minutes of TTS audio per month**, and the $5/month Starter tier bumps that to only **~30 minutes**. This is a real constraint.

That said, the quality genuinely justifies the cost for the right use case. V3 is expressive in a way no local model comes close to. The recommendation is to use it **sparingly and intentionally** — write tight scripts, use audio tags to get the performance right, and turn up the expressiveness settings. When you need a final, high-quality render, it delivers.

Check ElevenLabs pricing: https://elevenlabs.io/pricing/api
Read about ElevenLabs V3: https://elevenlabs.io/blog/eleven-v3

**Caution:** Track your credits in Tab 4 of the program and be aware that even testing the voices in Tab 2 will drain your credits too.

---

## Quick Start

### 1. Set your API key (Tab 4)

Launch the app and go to **Tab 4 — Settings**. Follow the instructions in the
**ElevenLabs API** section to paste your key and save it. Voices will load automatically.

### 2. Write or prepare a script file

Scripts are `.txt` or `.md` files. Each spoken line uses the format:

```
SpeakerID: Dialogue text goes here.
```

Example:

```
# My Short Film

Alex: Hey, are you okay?
Jordan: Yeah, I'm fine. [sighs] Just tired.
(1.0s)
Alex: You sure? You look pale.
Jordan: I said I'm fine.
```

See **Script Format** below for full syntax details.

### 3. Load the script (Tab 1)

1. Launch the program and click **Open Script File**.
2. The parser checks for formatting errors and lists them in the log.
3. Fix any errors in your text editor and click **Reload Script**.
4. When the parse log shows no errors, click **Continue →**.

### 4. Configure voices (Tab 2)

Each detected speaker gets a panel with:

- **Voice** — Choose from any voice in your ElevenLabs account. Voices are fetched automatically when the app loads with a valid API key.
- **Speed** — Speaking rate from 0.7× to 1.2× (ElevenLabs native speed parameter).
- **Stability** — Voice consistency (0.0–1.0). Higher = more consistent but less expressive. Default 0.5.
- **Similarity** — How closely the output matches the target voice (0.0–1.0). Default 0.75.
- **Pitch** — Multiplier from ×0.5 to ×2.0 (FFMPEG rubberband pitch shift). Default ×1.0 = no shift.
- **Level** — 5–100% relative volume. 100% = full normalized output (default). Reduce to make a speaker quieter in the mix.
- **Yell Impact** — Slows down single-word exclamatory lines (e.g. `YES!`). Makes such lines sound more deliberate and impactful. Set per speaker.
- **Audio Effects** — Radio, Reverb, Distortion, Telephone, Robot Voice, Cheap Mic,
  Underwater, Megaphone, Worn Tape, Intercom, Alien Voice, Cave, and Pitch Shift.
  Most effects have Off / Mild / Medium / Strong levels.

Use **Test Voice** to generate a quick preview clip and hear the settings immediately.

Settings auto-save to `character_profiles.json` on every change, so known speakers
are recalled automatically next session.

### 5. Generate (Tab 3)

1. Enter a **Project Name** (used as a filename prefix, 20 chars max).
2. Choose an **Output Folder**.
3. Click **Generate All** and confirm.

The generation log shows progress. When done, all files appear in the output folder:

```
output_folder/
├── clips_clean/          ← Raw TTS clips (no FFMPEG effects)
│   └── project_0001_Speaker_line-text.mp3
├── clips_effect/         ← Effects-processed clips (peak-normalized)
│   └── project_0001_Speaker_line-text.mp3
├── sfx/                  ← Processed SFX copies (only if SFX effects active)
├── !project_merged_pure.mp3        ← Merged audio, no normalization
├── !project_merged_loudnorm.mp3    ← Merged audio, loudness-normalized
└── project_reference.txt           ← Line-by-line reference sheet
```

---

## Script Format

### Dialogue lines

```
SpeakerID: Spoken text goes here.
```

- SpeakerID must be 20 characters or fewer. Allowed: letters, numbers, spaces, hyphens, underscores.
- All text after the first colon is spoken. Additional colons in the line are fine.
- Lines over 4000 characters throw a parse error.

### Audio tags (ElevenLabs V3)

```
Alex: I can't believe this. [sighs heavily]
Jordan: [whispering] Don't move.
```

`[brackets]` on a dialogue line are **passed through to ElevenLabs V3 as audio direction tags**. They influence how the voice is delivered — emotion, pace, action. They are not spoken as words and do not appear in the reference sheet text.

### Headings

```
# Scene title
## Sub-scene
```

Treated as metadata. Sets the script title. Not voiced.

### Comments

```
// This is a comment
/* Multi-line
   comment */
```

Not voiced. Useful for stage directions, notes, or commented-out lines.

### Pauses

```
(1.5s)
(pause 2.0)
(0.8)
```

Any line that is only parentheses containing a number inserts a silent pause in the
merged audio. The number is in seconds.

### Sound effects

```
{play filename.mp3, c1, loop}
{stop c1}
{stop all}
{play explosion.wav, c2, once}
```

Sound effect events are placed in the merge timeline at the correct position.
Sound effect files must exist in the SFX folder specified in Tab 2.

**Note:** If a sound effect is the very last item in your script, it needs a pause after it to actually be heard in the merged audio.
Add a `(pause)` line equal to or longer than the sound effect's duration immediately after the `{play}` line. Without it, the base audio ends at the same moment the SFX starts, and the SFX gets cut off.

Like this:

```
Rei: Signing off.
{play cloth.wav, c1, once}
(2.0s)
```

**Supported formats** — Any audio format FFMPEG can read: `.mp3`, `.wav`, `.ogg`, `.flac`, `.aac`, `.m4a`, and others.
The filename in your script must match the actual file exactly (including extension).

### Inner thoughts

```
SpeakerID: (( This line is an inner thought. ))
```

Wrapping dialogue in double parentheses marks it as an inner thought. Inner thought lines are voiced with a special filtering effect configured in Tab 4 (Dissociated, Whisper, or Dreamlike presets, or Custom). The filter runs on top of all the speaker's regular effects.

### Inline notation

- `[brackets]` on a dialogue line are **audio direction tags** — passed to ElevenLabs V3 to influence delivery. Not spoken, not shown in reference text.
- `**bold**`, `_italic_`, and `~~strikethrough~~` markers are stripped before TTS (ElevenLabs V3 does not interpret these).
- `//` after dialogue text starts an inline comment; everything after it is stripped. A space before `//` is required (so URLs are not accidentally stripped).

---

## Settings Tab (Tab 4)

**ElevenLabs API** — Enter your API key here. Voices load automatically once a valid key is saved. Use "Get Usage Stats" to check your monthly character usage.

**Generation Options** — Clip continuity (chains each clip's request ID for more natural voice flow), text normalization (auto-expands numbers/dates), and optional seed for best-effort deterministic output.

**Silence Trim** — Controls how leading/trailing silence is removed from each TTS clip.
Default: trim beginning and end. Options: Off, Beginning only, End only, Beginning + End, All silence.

**Merged Audio Pauses** — Adjust the pause duration added after each punctuation type
(period, comma, exclamation, question, hyphen, ellipsis, etc.).

**Contextual Modifiers** — Fine-tune how pause lengths are modified by context:
speaker changes, short lines, long lines, inner thought padding, same-speaker reduction, first/last line padding.

**Inner Thoughts Effect** — Choose from Whisper, Dreamlike, Dissociated presets
or configure custom highpass/lowpass/echo parameters for the inner thought audio filter.

---

## Audio Effects Reference

| Effect | Description |
|--------|-------------|
| Radio Filter | Walkie-talkie / comms radio effect. Bandpass + phaser + compression. |
| Reverb | Spatial depth. Configurable echo chains. |
| Distortion | Aggressive, gritty clipping and bit crushing. |
| Telephone | Lo-fi compressed sound. Narrow bandpass + bit crushing. |
| Robot Voice | Ring modulator for mechanical / robotic character. |
| Cheap Mic | Degraded quality, poor recording simulation. |
| Underwater | Muffled, wet, submerged sound. Lowpass + flanger. |
| Megaphone | Projected bullhorn. Treble-boosted, punchy, bandpassed. |
| Worn Tape | VHS/cassette degradation. Wow-flutter, lo-fi analog warble. |
| Intercom | Hallway speaker box. Flat, compressed, confined. Adds crackling static noise. |
| Alien Voice | Non-human vocal quality. Three variants: Insectoid, Dimensional, Warble. |
| Cave | Physical stone space reverb. Three variants: Tunnel, Cave, Abyss. |
| Pitch Shift | FFMPEG rubberband pitch shift. Multiplier ×0.5–×2.0. Works independently of speed. |

Most effects have Off / Mild / Medium / Strong presets. Alien and Cave use named variants instead. Effects are combinable.

---

## Tips

- **Voices from your account** — Any voice in your ElevenLabs library is available in Tab 2. Use the **Test Voice** button to audition before committing to a full run.

- **Audio tags for expression** — ElevenLabs V3 responds to `[brackets]` in dialogue as delivery directions. Try `[whispering]`, `[laughing]`, `[sighs]`, `[shouting]` — the voice adjusts its delivery.

- **Stability and Similarity** — If a voice sounds inconsistent across clips, raise Stability. If it sounds too generic, raise Similarity. These are the primary ElevenLabs quality dials per speaker.

- **Pitch for pitch shifting** — The pitch slider in Tab 2 uses FFMPEG rubberband pitch shifting. It is independent of speaking speed.

- **Clip continuity** — Leave "Use clip continuity" on in Tab 4 Generation Options. It chains each generated clip's request ID to the next, producing more natural voice flow across consecutive lines from the same speaker.

- **Test each voice** before generating everything. The Test Voice button in Tab 2 saves a preview clip and opens it immediately.

- **Cheap Mic** at Mild is a subtle effect that adds a hint of realism. Worth trying as a default.

- **Prompt templates** — The `!docs/prompt_templates/` folder has templates for using AI chatbots to write scripts or generate voice line banks. Open them in any text editor.

---

## Included Docs (`!docs/`)

### Guides

| File | Contents |
|------|----------|
| `!docs/guides/Script_Writing_Guide.md` | Writing for TTS, pacing with punctuation and pauses, using effects as character design, AI-assisted workflow |
| `!docs/guides/Audio_Effects_Guide.md` | Full reference for all effects, preset levels, FFMPEG pipeline, Yell Impact, troubleshooting |

### Example Scripts

Ready-to-load `.md` script files — open any of them in Tab 1 to see the format in action.

| File | What it demonstrates |
|------|----------------------|
| `example_tiny.md` | Minimal 2-line script |
| `example_small.md` | Short 2-character scene with SFX, pause, and comments |
| `example_full_drama.md` | Full multi-character drama with SFX channels, inner thoughts, and scene structure |
| `example_monologue.md` | Single narrator, no character interaction |
| `example_meditation.md` | Atmospheric piece with long pauses and inner thought lines |
| `example_oneliners.md` | Voice bank format — one character, many independent lines by category |
| `example_game_scenes.md` | Multi-scene game dialogue with tactical characters, SFX, and inner thoughts |

### Prompt Templates

Fill-in-the-blank prompts for generating scripts with an AI chatbot. Copy, fill in characters/scenario, paste to a chatbot, save the output as a `.md` file, load in Tab 1.

| File | Use case |
|------|----------|
| `cohesive_script.md` | Continuous scene — characters talk to each other |
| `separate_voice_lines.md` | Voice bank — independent lines per category |
| `game_scene_pack.md` | Single game scene with character roles, SFX, and inner thoughts |
| `narrator_monologue.md` | Single narrator — story, documentary, speech, essay |
| `podcast_interview.md` | Two-person host/guest conversation |
| `ambient_narration.md` | Slow, atmospheric, mood-driven spoken word |

---

## Troubleshooting

**No voices in Tab 2** — Check that your API key is entered and saved in Tab 4. The app fetches voices from ElevenLabs on startup. If the key is invalid or missing, the voice list will be empty.

**FFMPEG not found** — Install FFMPEG and make sure it is in your system PATH.
Use the automatic installer at https://reactorcore.itch.io/ffmpeg-to-path-installer
then restart the program.

**Parse errors on load** — The parse log in Tab 1 lists every error with line numbers.
Fix them in your text editor and click Reload Script.

**Voice too quiet** — The post-effects normalization pass ensures consistent loudness.
If a speaker still sounds quiet relative to others, their Level slider may be below 100%.

**Missing voice lines in output** — Check the generation log in Tab 3 for per-line
errors. An API error or FFMPEG issue on a specific line will be noted.

**Test Voice not opening** — The file is saved to `output_test/` in the program folder.
Open it manually if the auto-open fails.

**Generation fails / API errors** — Check Tab 4's Usage Stats to see if you've hit your
monthly character quota. Upgrade your ElevenLabs plan if needed. Check that your API key
is correct and has the necessary permissions ("Unrestricted" is simplest).

---

## Credits

- **ElevenLabs V3 TTS** — Cloud TTS engine
- **ttkbootstrap** — Modern themed tkinter UI
- **FFMPEG** — Audio processing and merging
- **Script to Voice Generator** — By Reactorcore

---

## Links

Check out everything else I do:

https://linktr.ee/reactorcore
