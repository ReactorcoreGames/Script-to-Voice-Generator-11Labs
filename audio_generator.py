"""
Audio generation using ElevenLabs V3 TTS API and FFMPEG conversion utilities.
"""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


# ── Voice ID parsing ──────────────────────────────────────────────────────────

def parse_voice_id_from_display(display_string: str) -> str:
    """Extract voice_id from display string like 'George - Warm Storyteller  [JBFqnCBsd6RMkjVDRZzb]'.
    Returns the display_string unchanged if no bracket-wrapped ID is found.
    ElevenLabs voice IDs are alphanumeric (letters + digits), matched by \\w+.
    """
    match = re.search(r'\[(\w+)\]', display_string)
    return match.group(1) if match else display_string


# ── Yell impact helper ────────────────────────────────────────────────────────

def is_yell_line(spoken_text: str) -> bool:
    """
    Check if a spoken text line qualifies for the Yell Impact speed adjustment.

    Qualifies when:
    - The entire text is a single word (no spaces) before trailing punctuation
    - The trailing punctuation characters contain at least one !
    - Patterns like AAARGH!, YES!!, NO?!, HELP?!?, REALLY!!! all qualify
    - Lines ending with ? only, or multi-word lines, do NOT qualify
    """
    text = spoken_text.strip()
    if not text:
        return False

    match = re.match(r'^([^?!\s]+)([?!]+)$', text)
    if not match:
        return False

    punct_part = match.group(2)
    return '!' in punct_part


# ── Silence filter builder ────────────────────────────────────────────────────

def _build_silence_filter(mode: str) -> str:
    """
    Build the FFMPEG filter string(s) for Stage 0 silence trimming.
    Returns empty string when mode is "off" (caller skips the filter entirely).

    mode values: "off" / "beginning" / "end" / "beginning_end" / "all"

    End trim uses an areverse sandwich (reverse → silenceremove start → reverse)
    rather than silenceremove stop_periods. The stop_periods approach is a
    streaming filter that can prematurely terminate on any natural amplitude dip
    (falling intonation, trailing fricatives, breathy tails). The areverse
    approach trims only the true tail and is immune to mid-clip dips.
    """
    if mode == "off":
        return ""

    trim_start = mode in ("beginning", "beginning_end", "all")
    trim_end   = mode in ("end", "beginning_end")
    trim_all   = mode == "all"

    START_FILTER = (
        "silenceremove="
        "start_periods=1:"
        "start_silence=0.02:"
        "start_threshold=-35dB:"
        "stop_periods=0"
    )
    # End trim: reverse, strip leading silence (= original trailing silence), reverse back.
    END_FILTER = (
        "areverse,"
        "silenceremove="
        "start_periods=1:"
        "start_silence=0.02:"
        "start_threshold=-35dB:"
        "stop_periods=0,"
        "areverse"
    )
    # "all" mode: strip mid-clip silence via stop_periods=-1 after start trim.
    ALL_MID_FILTER = (
        "silenceremove="
        "start_periods=0:"
        "stop_periods=-1:"
        "stop_silence=0.1:"
        "stop_threshold=-80dB"
    )

    filters = []
    if trim_start:
        filters.append(START_FILTER)
    if trim_end:
        filters.append(END_FILTER)
    elif trim_all:
        filters.append(ALL_MID_FILTER)
        filters.append(END_FILTER)

    return ",".join(filters)


# ── AudioGenerator class ──────────────────────────────────────────────────────

class AudioGenerator:
    """Handles audio generation via ElevenLabs V3 API and FFMPEG post-processing."""

    def __init__(self):
        self._api_key = None          # set by set_api_key()
        self._el_client = None        # elevenlabs.ElevenLabs instance
        self.available_voices = []    # list of display strings
        self._voice_map = {}          # display_string -> voice_id

    def set_api_key(self, api_key: str):
        """Store API key and (re)create ElevenLabs client."""
        self._api_key = api_key.strip() if api_key else ""
        if self._api_key:
            try:
                from elevenlabs import ElevenLabs
                self._el_client = ElevenLabs(api_key=self._api_key)
            except Exception as e:
                print(f"Warning: could not create ElevenLabs client: {e}")
                self._el_client = None
        else:
            self._el_client = None

    def fetch_voices(self) -> tuple:
        """
        Call GET /v1/voices with stored API key.
        Returns (display_strings: list, error_message: str | None).
        Display format: "Name - Description  [voice_id]"
        Falls back to requests if elevenlabs SDK is unavailable.
        """
        if not self._api_key:
            return [], "No API key set."

        try:
            import requests
            response = requests.get(
                "https://api.elevenlabs.io/v1/voices",
                headers={"xi-api-key": self._api_key},
                timeout=15,
            )
            if response.status_code == 401:
                return [], "Invalid API key. Check your key in Tab 4 Settings."
            response.raise_for_status()

            data = response.json()
            voices_raw = data.get("voices", [])

            display_strings = []
            self._voice_map = {}

            for v in voices_raw:
                vid = v.get("voice_id", "")
                name = v.get("name", "Unknown")
                desc = v.get("description") or ""
                if desc:
                    display = f"{name} - {desc}  [{vid}]"
                else:
                    display = f"{name}  [{vid}]"
                display_strings.append(display)
                self._voice_map[display] = vid

            self.available_voices = display_strings
            return display_strings, None

        except Exception as e:
            return [], str(e)

    def get_subscription_info(self) -> tuple:
        """
        Call GET /v1/user/subscription.
        Returns (info_dict: dict | None, error: str | None).
        info_dict keys: tier, character_count, character_limit, status, next_reset_unix
        """
        if not self._api_key:
            return None, "No API key set."

        try:
            import requests
            response = requests.get(
                "https://api.elevenlabs.io/v1/user/subscription",
                headers={"xi-api-key": self._api_key},
                timeout=15,
            )
            if response.status_code == 401:
                return None, "Invalid API key."
            response.raise_for_status()

            data = response.json()
            info = {
                "tier": data.get("tier", "unknown"),
                "character_count": data.get("character_count", 0),
                "character_limit": data.get("character_limit", 0),
                "status": data.get("status", "unknown"),
                "next_reset_unix": data.get("next_character_count_reset_unix"),
            }
            return info, None

        except Exception as e:
            return None, str(e)

    def generate_audio(self, text: str, output_path: str, voice_id: str,
                       speed_float: float = 1.0,
                       stability: float = 0.5,
                       similarity_boost: float = 0.75,
                       previous_request_ids: list = None,
                       next_text: str = None,
                       apply_text_normalization: str = "auto",
                       seed: int = None) -> tuple:
        """
        Generate audio via ElevenLabs V3 TTS and save to output_path (MP3).

        [brackets] in text are audio tags and are NOT stripped — they pass through to the API.
        Output is MP3 directly from the API — no WAV temp file needed.

        Returns:
            tuple: (success: bool, error_message: str | None, request_id: str | None)
        """
        if not self._api_key:
            return False, "No ElevenLabs API key set. Add your key in Tab 4 Settings.", None

        try:
            import requests

            safe_speed = max(0.7, min(1.2, float(speed_float)))
            safe_stability = max(0.0, min(1.0, float(stability)))
            safe_similarity = max(0.0, min(1.0, float(similarity_boost)))

            body = {
                "text": text,
                "model_id": "eleven_v3",
                "voice_settings": {
                    "stability": safe_stability,
                    "similarity_boost": safe_similarity,
                    "style": 0.0,
                    "speed": safe_speed,
                },
                "apply_text_normalization": apply_text_normalization,
            }

            # previous_request_ids / next_text are not supported by eleven_v3
            # (API returns 400 unsupported_model if included)

            if next_text is not None:
                body["next_text"] = next_text

            if seed is not None:
                body["seed"] = int(seed)

            response = requests.post(
                f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                params={"output_format": "mp3_44100_128"},
                headers={
                    "xi-api-key": self._api_key,
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=120,
            )

            if response.status_code == 401:
                return False, "Invalid API key. Check your key in Tab 4 Settings.", None
            if response.status_code == 422:
                try:
                    detail = response.json().get("detail", response.text)
                except Exception:
                    detail = response.text
                return False, f"ElevenLabs API validation error: {detail}", None
            if not response.ok:
                return False, f"ElevenLabs API error {response.status_code}: {response.text[:200]}", None

            # Extract request-id for continuity chaining
            request_id = (response.headers.get("request-id")
                          or response.headers.get("x-request-id"))

            # Write MP3 directly to output path
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(response.content)

            return True, None, request_id

        except Exception as e:
            return False, f"ElevenLabs TTS error: {e}", None

    def _get_subprocess_startupinfo(self):
        """Get subprocess startup info to hide console windows on Windows."""
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            return startupinfo
        return None

    def apply_volume_adjustment(self, input_path, output_path, volume_percent):
        """
        Apply volume adjustment to an audio file using FFMPEG.
        Supports in-place operation (input_path == output_path) via a temp file.

        Returns:
            tuple: (success: bool, error_message: str or None)
        """
        try:
            volume_multiplier = volume_percent / 100.0
            in_place = str(input_path) == str(output_path)
            if in_place:
                suffix = Path(str(output_path)).suffix or ".mp3"
                fd, tmp_path = tempfile.mkstemp(suffix=suffix)
                os.close(fd)
                actual_output = tmp_path
            else:
                actual_output = str(output_path)

            try:
                subprocess.run([
                    "ffmpeg", "-i", str(input_path),
                    "-af", f"volume={volume_multiplier}",
                    "-y", actual_output
                ], check=True, capture_output=True,
                    startupinfo=self._get_subprocess_startupinfo())
                if in_place:
                    os.replace(tmp_path, str(output_path))
            except subprocess.CalledProcessError:
                if in_place:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass
                raise

            return True, None
        except subprocess.CalledProcessError as e:
            return False, f"Failed to adjust volume: {str(e)}"
        except FileNotFoundError:
            return False, ("FFMPEG not found in PATH. Please install FFMPEG.\n\n"
                           "You can use: https://reactorcore.itch.io/ffmpeg-to-path-installer")

    def apply_audio_effects(self, input_path, output_path, effect_settings,
                            volume_percent=100, is_inner_thought=False,
                            config_manager=None, is_sfx=False,
                            silence_trim_mode="beginning_end",
                            silence_start_db=-65, silence_stop_db=-65):  # kept for call-site compat, ignored
        """
        Apply audio effects to an audio file using FFMPEG. Does NOT apply volume.
        Volume is applied separately after peak normalization so relative levels are preserved.

        Pipeline (voice clips):
        0. Silence removal (configurable — default "beginning_end")
        2. Frequency-based effects (radio, telephone, cheap_mic, underwater, megaphone, worn_tape, intercom)
        3. Ring modulation / pitch-based effects (robot_voice, alien)
        3.5. FFMPEG pitch shift (pitch_multiplier — rubberband multiplier float)
        4. Spatial/echo effects (reverb, cave)
        5. Distortion
        5.5. Inner thoughts filter
        7. Soft limiting
        8.5. FMSU (optional destructive pass)
        9. Reverse (optional)

        Volume is applied after peak normalization via apply_volume_adjustment().

        Returns:
            tuple: (success: bool, error_message: str or None)
        """
        from config import AUDIO_EFFECTS, INNER_THOUGHTS_FILTER, FMSU_FILTER

        if config_manager is not None:
            inner_thoughts_filter = config_manager.get_inner_thoughts_filter()
        else:
            inner_thoughts_filter = INNER_THOUGHTS_FILTER

        try:
            filters = []

            if not is_sfx:
                # STAGE 0: Silence removal (configurable)
                silence_filter = _build_silence_filter(silence_trim_mode)
                if silence_filter:
                    filters.append(silence_filter)

            # STAGE 2: Frequency-based effects
            for effect_name in ["radio", "telephone", "cheap_mic",
                                 "underwater", "megaphone", "worn_tape", "intercom"]:
                if effect_name in effect_settings and effect_settings[effect_name] != "off":
                    level = effect_settings[effect_name]
                    if effect_name in AUDIO_EFFECTS:
                        effect_filter = AUDIO_EFFECTS[effect_name]["presets"].get(level, "")
                        if effect_filter:
                            filters.append(effect_filter)

            # STAGE 3: Ring modulation / pitch-based character effects
            for effect_name in ["robot_voice", "alien"]:
                if effect_name in effect_settings and effect_settings[effect_name] != "off":
                    level = effect_settings[effect_name]
                    if effect_name in AUDIO_EFFECTS:
                        effect_filter = AUDIO_EFFECTS[effect_name]["presets"].get(level, "")
                        if effect_filter:
                            filters.append(effect_filter)

            # STAGE 3.5: Pitch shift via rubberband (true pitch/tempo independence)
            # Per-speaker: float multiplier (0.5–2.0). SFX panel: string preset key.
            ps_val = effect_settings.get("pitch_shift", 1.0)
            try:
                ps_multiplier = float(ps_val)
                if ps_multiplier != 1.0:
                    filters.append(f"rubberband=pitch={ps_multiplier:.4f}")
            except (TypeError, ValueError):
                # String preset from SFX panel
                if ps_val and ps_val != "off":
                    preset_filter = AUDIO_EFFECTS.get("pitch_shift", {}).get("presets", {}).get(ps_val, "")
                    if preset_filter:
                        filters.append(preset_filter)

            # STAGE 4: Spatial/echo effects
            for effect_name in ["reverb", "cave"]:
                if effect_name in effect_settings and effect_settings[effect_name] != "off":
                    level = effect_settings[effect_name]
                    if effect_name in AUDIO_EFFECTS:
                        effect_filter = AUDIO_EFFECTS[effect_name]["presets"].get(level, "")
                        if effect_filter:
                            filters.append(effect_filter)

            # STAGE 5: Distortion (needs loud signal to clip properly)
            if "distortion" in effect_settings and effect_settings["distortion"] != "off":
                level = effect_settings["distortion"]
                if "distortion" in AUDIO_EFFECTS:
                    effect_filter = AUDIO_EFFECTS["distortion"]["presets"].get(level, "")
                    if effect_filter:
                        filters.append(effect_filter)

            # STAGE 5.5: Inner thoughts filter
            if is_inner_thought:
                filters.append(inner_thoughts_filter)

            # STAGE 7: Soft limiting
            filters.append("alimiter=level=1:attack=1:release=100")

            # STAGE 8.5: FMSU — destructive corruption pass
            if effect_settings.get("fmsu", False):
                filters.append(FMSU_FILTER)
                filters.append("alimiter=level=1:attack=7:release=100")

            # STAGE 9: Reverse
            if effect_settings.get("reverse", False):
                filters.append("areverse")

            filter_chain = ",".join(filters)

            # Intercom static noise: uses filter_complex to mix noise into voice
            intercom_level = effect_settings.get("intercom", "off")
            intercom_noise_params = {
                "mild":   (0.08, "anoisesrc=amplitude=0.10:color=brown,highpass=f=300,lowpass=f=3500,acrusher=bits=6:mode=log:aa=0"),
                "medium": (0.20, "anoisesrc=amplitude=0.22:color=brown,highpass=f=200,lowpass=f=3000,acrusher=bits=4:mode=log:aa=0"),
                "strong": (0.28, "anoisesrc=amplitude=0.28:color=brown,highpass=f=150,lowpass=f=2800,acrusher=bits=3:mode=log:aa=0"),
            }.get(intercom_level)

            if intercom_noise_params is not None:
                _, noise_filter = intercom_noise_params
                complex_graph = (
                    f"[0:a]{filter_chain},alimiter=level=1:attack=1:release=100[voice];"
                    f"{noise_filter}[noise];"
                    f"[voice][noise]amix=inputs=2:weights=1 1:normalize=0:duration=shortest"
                )
                subprocess.run([
                    "ffmpeg", "-i", str(input_path),
                    "-filter_complex", complex_graph,
                    "-y", str(output_path)
                ], check=True, capture_output=True, text=True,
                    startupinfo=self._get_subprocess_startupinfo())
            else:
                subprocess.run([
                    "ffmpeg", "-i", str(input_path),
                    "-af", filter_chain,
                    "-y", str(output_path)
                ], check=True, capture_output=True, text=True,
                    startupinfo=self._get_subprocess_startupinfo())

            return True, None

        except subprocess.CalledProcessError as e:
            stderr_output = e.stderr if e.stderr else str(e)
            error_msg = (f"Failed to apply audio effects.\n\n"
                         f"FFMPEG Error:\n{stderr_output}\n\n"
                         f"This should not happen with the safety pipeline.\n"
                         f"Please report this error with your effect settings.")
            return False, error_msg
        except FileNotFoundError:
            return False, ("FFMPEG not found in PATH. Please install FFMPEG.\n\n"
                           "You can use: https://reactorcore.itch.io/ffmpeg-to-path-installer")

    def apply_peak_normalize(self, input_path, output_path):
        """
        Peak-normalize an audio file (input → output).

        Two-pass: measure peak via volumedetect, then apply linear gain so the
        loudest sample reaches exactly 0 dBFS. Dynamics are fully preserved.

        Returns:
            tuple: (success: bool, error_message: str or None)
        """
        import re as _re
        startupinfo = self._get_subprocess_startupinfo()
        try:
            result = subprocess.run([
                "ffmpeg", "-i", str(input_path),
                "-af", "volumedetect",
                "-f", "null", "-"
            ], capture_output=True, text=True, startupinfo=startupinfo)

            match = _re.search(r"max_volume:\s*([-\d.]+)\s*dB", result.stderr)
            if not match:
                return False, "Peak normalize failed: could not read max_volume from ffmpeg output."

            max_volume_db = float(match.group(1))
            if max_volume_db >= 0.0:
                import shutil
                if str(input_path) != str(output_path):
                    shutil.copy2(str(input_path), str(output_path))
                return True, None

            gain_db = -max_volume_db

            in_place = str(input_path) == str(output_path)
            if in_place:
                suffix = Path(str(output_path)).suffix or ".mp3"
                fd, tmp_path = tempfile.mkstemp(suffix=suffix)
                os.close(fd)
                actual_output = tmp_path
            else:
                actual_output = str(output_path)

            try:
                subprocess.run([
                    "ffmpeg", "-i", str(input_path),
                    "-af", f"volume={gain_db}dB",
                    "-y", actual_output
                ], check=True, capture_output=True, text=True, startupinfo=startupinfo)

                if in_place:
                    os.replace(tmp_path, str(output_path))
            except subprocess.CalledProcessError:
                if in_place:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass
                raise

            return True, None

        except subprocess.CalledProcessError as e:
            return False, f"Peak normalize failed: {e.stderr}"
        except FileNotFoundError:
            return False, ("FFMPEG not found in PATH. Please install FFMPEG.\n\n"
                           "You can use: https://reactorcore.itch.io/ffmpeg-to-path-installer")
