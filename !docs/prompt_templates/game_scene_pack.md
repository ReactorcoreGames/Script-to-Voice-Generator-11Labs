# Game Scene Pack Template

Use this when you want **a complete single game scene** — characters with distinct
roles, a clear dramatic situation, SFX placeholders, and inner thoughts. Designed to
produce output that loads straight into Script to Voice Generator as a ready scene.

One scene per file. If your game has multiple scenes, use this template once per scene
and keep them in separate files — this lets you configure voice and audio effects
per-scene in Tab 2.

**Tips:**
- Define each character's role in the scene clearly — not just who they are, but what
  they want in this specific moment. Characters with conflicting goals produce more
  interesting dialogue naturally.
- Name your SpeakerIDs to match whatever your game engine expects, or plan a batch
  rename workflow after generation (e.g. with Advanced Renamer).
- Include `// SFX: description` placeholders in the prompt output and swap them for
  real `{play filename.ext, cN, once}` commands once you have your audio assets.
- Inner thoughts `((like this))` are excellent for game protagonists — the player
  hears what the character is really thinking while they say something else out loud.
- Interrupted lines with `--` at the end of one line and `--` at the start of the next
  create realistic cutoff dialogue between characters.

---
<!-- Everything below this line is the prompt. Select from the next line downward. -->

I need you to write a single game scene for a text-to-speech audio pipeline. The
output will be synthesized by a voice engine, so all dialogue must read naturally
when spoken aloud.

---

**SCENE CONTEXT:**
[Describe the setting, the situation, and what brings these characters together.
What is the dramatic situation? What is at stake in this scene?]

**CHARACTERS:**
[List each character:
- SpeakerID: Role, personality, how they speak, what they want in this scene.
  Alphanumeric, spaces, hyphens, and underscores allowed. Max 20 characters.]

**SCENE LENGTH:**
[Roughly how many spoken lines, or describe the intended feel — short and sharp,
slow and tense, escalating confrontation, etc. Aim for under 100 spoken lines.]

**TONE:**
[The overall feel of the scene: tense, darkly comic, emotional, urgent, mysterious, etc.]

---

**FORMAT RULES:**

Write every spoken line as:
```
SpeakerID: Dialogue text.
```

- Same SpeakerID every time that character speaks. Alphanumeric, spaces, hyphens, and underscores allowed. Max 20 characters.
- One line per speech. Never wrap a single speech across multiple text lines.
- Keep lines under 4000 characters (shorter is almost always better).
- End every line with a period, question mark, or exclamation mark.
- For pauses, write `(1.5)` on its own line. The number is seconds.
- For inner thoughts, write `((Thought text here.))` on its own line — no speaker ID.
  These are voiced with a separate quiet audio effect.
- For interrupted speech, end the line with `--` and begin the interrupting line
  with `--` to create a natural cutoff.
- For stage directions and scene notes, write `// Direction here` on its own line.
  Not voiced.
- For SFX placeholders, write `// SFX: [description of sound]` on its own line.
  I will replace these with actual sound commands after generation.
- For scene headers or section markers, write `## Header text` on its own line.
  Not voiced, used for organization only.

**IMPORTANT — Writing for ElevenLabs V3 TTS:**

Use `[audio tags]` in brackets to shape delivery — passed directly to the voice engine:
- `[whispering]`, `[shouting]`, `[tense]`, `[sighs]`, `[urgently]`
- Place at the start of a line or inline before the relevant words

Ellipses `...` produce a natural pause in speech. Em-dashes and commas affect pacing.
`**bold**`, `_italic_`, and `~~strikethrough~~` are stripped silently — use punctuation,
word choice, and `[audio tags]` to shape emphasis instead.
