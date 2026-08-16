import asyncio
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageTk

try:
    from imageio_ffmpeg import get_ffmpeg_exe
except Exception:
    get_ffmpeg_exe = None

# Microsoft OneCore / Microsoft Stefan only. No voice fallback.
try:
    from winrt.windows.media.speechsynthesis import SpeechSynthesizer
    from winrt.windows.storage.streams import DataReader
    WINRT_TTS_AVAILABLE = True
except Exception:
    SpeechSynthesizer = None
    DataReader = None
    WINRT_TTS_AVAILABLE = False


APP_NAME = "SchlauWutzie K.I. – Video Studio V22.2 FINAL"
IN_W, IN_H = 720, 1280
OUT_W, OUT_H = 1080, 1920
FPS = 30


def resource_path(relative_path: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative_path


DEFAULT_IMAGE = resource_path("assets/schlawutzie.png")
INTRO_VIDEO = resource_path("assets/SchlauWutzie_KI_AI_Datacenter_Intro_V4_FINAL.mp4")


def ffmpeg_path() -> str:
    if get_ffmpeg_exe is not None:
        try:
            path = get_ffmpeg_exe()
            if path:
                return str(path)
        except Exception:
            pass

    path = shutil.which("ffmpeg")
    if path:
        return path

    raise RuntimeError(
        "FFmpeg wurde nicht gefunden. Bitte die V20-Abhängigkeiten korrekt installieren."
    )


def font(size: int, bold: bool = False):
    candidates = []

    if os.name == "nt":
        candidates.append(
            Path(os.environ.get("WINDIR", r"C:\Windows"))
            / "Fonts"
            / ("segoeuib.ttf" if bold else "segoeui.ttf")
        )

    candidates.append(
        Path(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            if bold
            else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        )
    )

    for path in candidates:
        try:
            if path.exists():
                return ImageFont.truetype(str(path), size=size)
        except Exception:
            pass

    return ImageFont.load_default()


def fit_cover(image: Image.Image, size):
    image = image.convert("RGB")
    tw, th = size
    sw, sh = image.size

    scale = max(tw / sw, th / sh)
    nw, nh = int(sw * scale), int(sh * scale)

    image = image.resize((nw, nh), Image.Resampling.LANCZOS)

    left = max(0, (nw - tw) // 2)
    top = max(0, (nh - th) // 2)

    return image.crop((left, top, left + tw, top + th))


def read_audio_pcm(wav_path: str):
    with wave.open(wav_path, "rb") as wf:
        rate = wf.getframerate()
        raw = wf.readframes(wf.getnframes())

    data = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

    if data.size == 0:
        data = np.zeros(1, dtype=np.float32)

    return rate, data


def audio_to_wav(source: str) -> str:
    ff = ffmpeg_path()

    fd, output_path = tempfile.mkstemp(
        prefix="schlawutzie_audio_", suffix=".wav"
    )
    os.close(fd)

    command = [
        ff,
        "-y",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-sample_fmt",
        "s16",
        output_path,
    ]

    result = subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if result.returncode != 0:
        try:
            os.remove(output_path)
        except OSError:
            pass

        raise RuntimeError(
            "Audio konnte nicht geladen werden.\n\n"
            + result.stderr.decode(errors="ignore")[-1800:]
        )

    return output_path


def amplitude_curve(wav_path: str, frame_count: int):
    rate, data = read_audio_pcm(wav_path)
    frame_count = max(1, int(frame_count))

    positions = np.linspace(
        0,
        len(data),
        frame_count,
        endpoint=False,
    ).astype(np.int64)

    window = max(1, int(rate * 0.035))
    amps = np.zeros(frame_count, dtype=np.float32)

    for i, pos in enumerate(positions):
        start = max(0, pos - window // 2)
        end = min(len(data), pos + window // 2)
        chunk = data[start:end]

        rms = (
            float(np.sqrt(np.mean(chunk * chunk)))
            if len(chunk)
            else 0.0
        )

        amps[i] = min(1.0, rms * 5.0)

    if frame_count >= 7:
        kernel = np.ones(7, dtype=np.float32) / 7.0
        amps = np.convolve(amps, kernel, mode="same")

    return len(data) / rate, amps


# ---------------------------------------------------------------------------
# Microsoft OneCore / StefanM
# ---------------------------------------------------------------------------

def _status_write(path: Path, text: str):
    try:
        temporary = Path(str(path) + ".tmp")
        temporary.write_text(text, encoding="utf-8")
        os.replace(temporary, path)
    except Exception:
        pass


def _all_voices():
    if not WINRT_TTS_AVAILABLE:
        return []

    value = getattr(SpeechSynthesizer, "all_voices", None)
    if value is None:
        value = getattr(SpeechSynthesizer, "AllVoices", None)

    if value is None:
        raise RuntimeError(
            "SpeechSynthesizer.AllVoices ist in PyWinRT nicht verfügbar."
        )

    voices = value() if callable(value) else value
    return list(voices)


def _is_stefan(name: str, voice_id: str, language: str) -> bool:
    text = f"{name} {voice_id}".lower()
    lang = str(language or "").lower().replace("_", "-")

    has_stefan = bool(
        re.search(r"(?<![a-z])stefan(?![a-z])", text)
    )

    return has_stefan and (
        "de-de" in text or lang in ("de", "de-de")
    )


def _find_stefan():
    matches = []
    all_names = []

    for voice in _all_voices():
        name = str(getattr(voice, "display_name", "") or "")
        voice_id = str(getattr(voice, "id", "") or "")
        language = str(getattr(voice, "language", "") or "")

        all_names.append(name or voice_id)

        if _is_stefan(name, voice_id, language):
            matches.append(
                (name, voice_id, language, voice)
            )

    matches.sort(
        key=lambda item: (
            item[0].lower(),
            item[1].lower(),
        )
    )

    return (
        matches[0] if matches else None,
        all_names,
    )


async def _tts_helper_async(
    text: str,
    output_path: str,
    status_path: str,
):
    if not WINRT_TTS_AVAILABLE:
        raise RuntimeError(
            "Windows OneCore TTS ist nicht verfügbar. "
            "PyWinRT SpeechSynthesis fehlt."
        )

    _status_write(
        Path(status_path),
        "Windows-OneCore wird geprüft …",
    )

    chosen, names = _find_stefan()

    if chosen is None:
        found = (
            ", ".join(names[:20])
            if names
            else "keine OneCore-Stimmen"
        )

        raise RuntimeError(
            "Microsoft Stefan wurde von Windows nicht gefunden.\n\n"
            "Es wird absichtlich keine Ersatzstimme verwendet.\n\n"
            f"Gefundene Stimmen: {found}"
        )

    name, voice_id, language, voice = chosen

    _status_write(
        Path(status_path),
        f"StefanM gefunden: {name} ({language})",
    )

    synthesizer = SpeechSynthesizer()

    try:
        synthesizer.voice = voice

        stream = await synthesizer.synthesize_text_to_stream_async(
            text
        )

        _status_write(
            Path(status_path),
            "StefanM-Audio wird gespeichert …",
        )

        reader = DataReader(
            stream.get_input_stream_at(0)
        )

        try:
            with open(output_path, "wb") as output:
                while True:
                    count = await reader.load_async(65536)

                    if not count:
                        break

                    data = bytearray(count)
                    reader.read_bytes(data)
                    output.write(data)
        finally:
            try:
                reader.close()
            except Exception:
                pass

    finally:
        try:
            synthesizer.close()
        except Exception:
            pass

    with wave.open(output_path, "rb") as wf:
        if wf.getnframes() < 1 or wf.getframerate() < 1:
            raise RuntimeError(
                "Die erzeugte StefanM-WAV ist leer oder ungültig."
            )

    _status_write(
        Path(status_path),
        "StefanM-Audio fertig.",
    )


def _tts_helper_entry(
    input_path: str,
    output_path: str,
    status_path: str,
):
    try:
        text = Path(input_path).read_text(
            encoding="utf-8"
        ).strip()

        if not text:
            raise RuntimeError(
                "Der zu sprechende Text ist leer."
            )

        asyncio.run(
            _tts_helper_async(
                text,
                output_path,
                status_path,
            )
        )

        return 0

    except Exception as exc:
        _status_write(
            Path(status_path),
            "FEHLER: " + str(exc),
        )
        return 1


if (
    __name__ == "__main__"
    and len(sys.argv) == 5
    and sys.argv[1] == "--tts-helper"
):
    raise SystemExit(
        _tts_helper_entry(
            sys.argv[2],
            sys.argv[3],
            sys.argv[4],
        )
    )


def synthesize_stefan(
    text: str,
    status_callback=None,
    timeout=120,
) -> str:
    if os.name != "nt":
        raise RuntimeError(
            "Microsoft OneCore / Stefan funktioniert nur unter Windows."
        )

    temporary_dir = Path(
        tempfile.mkdtemp(
            prefix="schlawutzie_tts_"
        )
    )

    input_path = temporary_dir / "input.txt"
    output_path = temporary_dir / "StefanM.wav"
    status_path = temporary_dir / "status.txt"

    input_path.write_text(
        text,
        encoding="utf-8",
    )

    _status_write(
        status_path,
        "StefanM-Hilfsprozess wird gestartet …",
    )

    command = [
        sys.executable,
        "--tts-helper",
        str(input_path),
        str(output_path),
        str(status_path),
    ]

    creationflags = getattr(
        subprocess,
        "CREATE_NO_WINDOW",
        0,
    )

    process = None
    start = time.monotonic()
    last_status = ""

    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )

        while True:
            if status_path.exists():
                try:
                    current = status_path.read_text(
                        encoding="utf-8"
                    ).strip()
                except Exception:
                    current = ""

                if current and current != last_status:
                    last_status = current

                    if status_callback:
                        status_callback(current)

            code = process.poll()

            if code is not None:
                if code != 0:
                    message = (
                        last_status
                        .removeprefix("FEHLER:")
                        .strip()
                        or "StefanM konnte nicht erzeugt werden."
                    )

                    raise RuntimeError(message)

                break

            if time.monotonic() - start >= timeout:
                try:
                    process.kill()
                except Exception:
                    pass

                raise RuntimeError(
                    f"StefanM wurde nach {timeout} Sekunden abgebrochen.\n"
                    f"Letzter Status: {last_status or 'unbekannt'}"
                )

            time.sleep(0.10)

        if (
            not output_path.exists()
            or output_path.stat().st_size < 100
        ):
            raise RuntimeError(
                "StefanM meldete Erfolg, aber keine gültige WAV "
                "wurde erzeugt."
            )

        fd, final_path = tempfile.mkstemp(
            prefix="StefanM_",
            suffix=".wav",
        )
        os.close(fd)

        shutil.copy2(
            output_path,
            final_path,
        )

        return final_path

    finally:
        if (
            process is not None
            and process.poll() is None
        ):
            try:
                process.kill()
            except Exception:
                pass

        shutil.rmtree(
            temporary_dir,
            ignore_errors=True,
        )


# ---------------------------------------------------------------------------
# Central transparent K.I. animation
# ---------------------------------------------------------------------------

def draw_neural_hud(
    background: Image.Image,
    amplitude: float,
    t: float,
) -> Image.Image:
    """
    V21.5:
    The supplied reference image remains the complete design.
    Only the two existing waveform/equalizer zones left and right of the
    K.I. core are animated to the voice. No second core, text or rings.
    """

    frame = background.convert("RGBA")
    d = ImageDraw.Draw(frame, "RGBA")

    activity = float(np.clip(amplitude, 0.0, 1.0))

    # Reference image is 941 x 1672. These positions are normalized so
    # the animation follows the artwork rather than drawing a new layout.
    W, H = frame.size
    sx = W / 941.0
    sy = H / 1672.0

    # Existing waveform band / baseline.
    base_y = int(1295 * sy)

    # Left and right waveform zones. The center K.I. core is intentionally
    # untouched.
    zones = [
        (int(78 * sx), int(365 * sx), -1),
        (int(576 * sx), int(865 * sx), 1),
    ]

    # Softly suppress ONLY the old static gold waveform pixels in the narrow
    # animated bands, so the new motion is visible without creating a second
    # interface.
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay, "RGBA")

    for x0, x1, _side in zones:
        od.rectangle(
            (x0, base_y - int(70 * sy),
             x1, base_y + int(72 * sy)),
            fill=(0, 0, 0, 42),
        )

    frame = Image.alpha_composite(frame, overlay)
    d = ImageDraw.Draw(frame, "RGBA")

    # Build an audio-reactive equalizer. It occupies the same two visual
    # waveform regions as the reference artwork.
    bars_per_side = 38

    for x0, x1, side in zones:
        span = max(1, x1 - x0)
        step = span / bars_per_side

        for i in range(bars_per_side):
            cx = int(x0 + (i + 0.5) * step)

            # A smooth pseudo-spectrum: central bars taller, edges shorter,
            # with motion derived from the actual voice amplitude.
            u = (i + 0.5) / bars_per_side
            envelope = 0.24 + 0.76 * math.sin(math.pi * u) ** 0.65

            wave_a = 0.55 * math.sin(
                i * 1.71 + t * 10.0
            )
            wave_b = 0.30 * math.sin(
                i * 3.17 - t * 6.4
            )
            wave_c = 0.15 * math.sin(
                i * 5.61 + t * 3.8
            )

            variation = 0.50 + 0.50 * (
                wave_a + wave_b + wave_c
            )

            height = (
                5
                + 74
                * activity
                * envelope
                * max(0.12, min(1.0, variation))
            )

            # Keep the bars visibly moving even on ordinary speech.
            height += (
                4
                * math.sin(
                    t * 5.0
                    + i * 0.35
                )
                * (0.2 + activity)
            )

            height = max(3.0, height)

            # Thin premium bars.
            half_w = max(1, int(1.3 * sx))

            # Gold core line with cyan edge, matching the reference.
            d.rectangle(
                (
                    cx - half_w,
                    int(base_y - height),
                    cx + half_w,
                    int(base_y + height * 0.12),
                ),
                fill=(255, 202, 93, 205),
            )

            # Tiny cyan highlight on every few bars.
            if i % 3 == 0:
                d.line(
                    (
                        cx,
                        int(base_y - height * 0.82),
                        cx,
                        int(base_y + height * 0.08),
                    ),
                    fill=(92, 213, 255, 190),
                    width=1,
                )

            # Small peak point for stronger speech moments.
            if activity > 0.38 and i % 4 == 0:
                peak_y = int(base_y - height)
                d.ellipse(
                    (
                        cx - 2,
                        peak_y - 2,
                        cx + 2,
                        peak_y + 2,
                    ),
                    fill=(255, 232, 169, 220),
                )

    # Voice-reactive glow ONLY in the two animated zones.
    glow = frame.filter(ImageFilter.GaussianBlur(6))
    frame = Image.blend(
        frame,
        glow,
        0.10 + 0.14 * activity,
    )

    return frame.convert("RGB")


# ---------------------------------------------------------------------------
# MP4 rendering
# ---------------------------------------------------------------------------
def prepend_intro(intro_path: str, main_path: str, output_path: str):
    """
    Prepend the fixed 8-second cinematic intro to the finished V21.5 video.
    The intro and main video are normalized to the same 1080x1920 H.264/AAC
    profile and concatenated without re-encoding where possible.
    """
    ff = ffmpeg_path()

    intro_file = Path(intro_path)
    main_file = Path(main_path)

    if not intro_file.exists():
        raise RuntimeError(
            "Das Schlauwutzie K.I.-Intro wurde nicht gefunden:\n"
            + str(intro_file)
        )

    if not main_file.exists():
        raise RuntimeError(
            "Das Hauptvideo wurde nicht gefunden:\n"
            + str(main_file)
        )

    # Normalize to a stable intermediate format before concat.
    temp_dir = Path(tempfile.mkdtemp(prefix="schlawutzie_intro_"))
    intro_norm = temp_dir / "intro.mp4"
    main_norm = temp_dir / "main.mp4"
    concat_list = temp_dir / "concat.txt"

    try:
        normalize = [
            ff, "-y",
            "-i", str(intro_file),
            "-vf", f"scale={OUT_W}:{OUT_H}:flags=lanczos,format=yuv420p,setsar=1",
            "-r", str(FPS),
            "-c:v", "libx264",
            "-profile:v", "baseline",
            "-level", "4.0",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "160k",
            "-ar", "44100",
            "-ac", "2",
            "-movflags", "+faststart",
            str(intro_norm),
        ]
        result = subprocess.run(
            normalize,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "Das Intro konnte nicht vorbereitet werden.\n\n"
                + result.stderr.decode(errors="ignore")[-2500:]
            )

        normalize_main = [
            ff, "-y",
            "-i", str(main_file),
            "-vf", f"scale={OUT_W}:{OUT_H}:flags=lanczos,format=yuv420p,setsar=1",
            "-r", str(FPS),
            "-c:v", "libx264",
            "-profile:v", "baseline",
            "-level", "4.0",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "44100",
            "-ac", "2",
            "-movflags", "+faststart",
            str(main_norm),
        ]
        result = subprocess.run(
            normalize_main,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "Das Hauptvideo konnte nicht für das Intro vorbereitet werden.\n\n"
                + result.stderr.decode(errors="ignore")[-2500:]
            )

        concat_list.write_text(
            "file '" + str(intro_norm).replace("'", "'\\''") + "'\n"
            "file '" + str(main_norm).replace("'", "'\\''") + "'\n",
            encoding="utf-8",
        )

        concat_cmd = [
            ff, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
            "-movflags", "+faststart",
            str(output_path),
        ]
        result = subprocess.run(
            concat_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode != 0:
            raise RuntimeError(
                "Intro und Hauptvideo konnten nicht verbunden werden.\n\n"
                + result.stderr.decode(errors="ignore")[-3000:]
            )

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def render_video(
    background_path: str,
    audio_path: str,
    output_path: str,
    progress=None,
):
    background = fit_cover(
        Image.open(background_path),
        (IN_W, IN_H),
    )

    rate, data = read_audio_pcm(audio_path)

    duration = (
        len(data) / rate
        if rate
        else 0.0
    )

    frame_count = max(
        1,
        int(math.ceil(duration * FPS)),
    )

    _, amplitudes = amplitude_curve(
        audio_path,
        frame_count,
    )

    workdir = Path(
        tempfile.mkdtemp(
            prefix="schlawutzie_frames_"
        )
    )

    try:
        pattern = str(
            workdir / "frame_%06d.jpg"
        )

        for index in range(frame_count):
            frame = draw_neural_hud(
                background,
                float(amplitudes[index]),
                index / FPS,
            )

            frame.save(
                pattern % (index + 1),
                "JPEG",
                quality=88,
                optimize=True,
            )

            if progress and (
                index % 10 == 0
                or index == frame_count - 1
            ):
                progress(
                    index + 1,
                    frame_count,
                )

        ff = ffmpeg_path()

        command = [
            ff,
            "-y",
            "-framerate",
            str(FPS),
            "-i",
            pattern,
            "-i",
            str(audio_path),
            "-vf",
            f"scale={OUT_W}:{OUT_H}:flags=lanczos",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output_path),
        ]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if result.returncode != 0:
            raise RuntimeError(
                "MP4-Export fehlgeschlagen.\n\n"
                + result.stderr.decode(
                    errors="ignore"
                )[-3000:]
            )

    finally:
        shutil.rmtree(
            workdir,
            ignore_errors=True,
        )


# ---------------------------------------------------------------------------
# V22 Deutsche Auto-Untertitel – whisper.cpp
# ---------------------------------------------------------------------------

def _v22_ass_time(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    whole = int(secs)
    centis = int(round((secs - whole) * 100))
    if centis >= 100:
        whole += 1
        centis = 0
    if whole >= 60:
        minutes += 1
        whole = 0
    if minutes >= 60:
        hours += 1
        minutes = 0
    return f"{hours}:{minutes:02d}:{whole:02d}.{centis:02d}"


def _v22_escape_ass(text: str) -> str:
    return (
        str(text or "")
        .replace("\r", " ")
        .replace("\n", " ")
        .replace("{", "(")
        .replace("}", ")")
        .strip()
    )


def _v22_parse_ts(value: str) -> float:
    parts = str(value or "").strip().replace(",", ".").split(":")
    if len(parts) != 3:
        raise ValueError(f"Ungültiger Zeitstempel: {value!r}")
    return (
        int(parts[0]) * 3600
        + int(parts[1]) * 60
        + float(parts[2])
    )


def _v22_group_words(words, max_words=7, max_chars=40, max_duration=2.7):
    groups = []
    current = []

    def flush():
        nonlocal current
        if current:
            groups.append(current)
            current = []

    for token, start, end in words:
        token = _v22_escape_ass(token)
        if not token:
            continue

        item = (token, float(start), float(end))

        if not current:
            current.append(item)
            continue

        candidate = (
            " ".join(x[0] for x in current)
            + " "
            + token
        ).strip()

        duration = end - current[0][1]
        sentence_break = current[-1][0].endswith(
            (".", "!", "?", ":", ";")
        )

        if (
            len(current) >= max_words
            or len(candidate) > max_chars
            or duration > max_duration
            or sentence_break
        ):
            flush()

        current.append(item)

    flush()
    return groups


def _v22_whisper_cli() -> Path:
    path = resource_path(
        "whisper_runtime/whisper-cli.exe"
    )
    if not path.exists():
        raise RuntimeError(
            "V22: whisper-cli.exe fehlt im Programm."
        )
    return path


def _v22_whisper_model() -> Path:
    path = resource_path(
        "whisper_models/ggml-small-q5_1.bin"
    )
    if not path.exists():
        raise RuntimeError(
            "V22: deutsches Whisper-Sprachmodell fehlt."
        )
    return path


def transcribe_german_to_ass(
    audio_path: str,
    status_callback=None,
    source_text: str = "",
) -> str:
    """
    V22: whisper.cpp + ggml-small-q5_1.
    Uses true word-sized timestamp segments via -ml 1 + -sow.
    """
    source = Path(audio_path)
    if not source.exists():
        raise RuntimeError(
            "Audio für Auto-Untertitel nicht gefunden."
        )

    cli = _v22_whisper_cli()
    model = _v22_whisper_model()

    work = Path(
        tempfile.mkdtemp(
            prefix="schlawutzie_v22_whisper_"
        )
    )
    base = work / "result"
    json_path = Path(
        str(base) + ".json"
    )

    if status_callback:
        status_callback(
            "V22: Deutsche Sprachspur wird analysiert …"
        )

    prompt = re.sub(
        r"\s+",
        " ",
        str(source_text or ""),
    ).strip()[:2500]

    cmd = [
        str(cli),
        "-m", str(model),
        "-f", str(source),
        "-l", "de",
        "-t", str(max(4, min(8, (os.cpu_count() or 4) - 1))),
        "-p", "1",
        "-ml", "1",
        "-sow",
        "-wt", "0.01",
        "-bs", "5",
        "-bo", "5",
        "-oj",
        "-of", str(base),
        "-np",
        "-nf",
    ]

    if prompt:
        cmd += ["--prompt", prompt]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=20 * 60,
        )
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(work, ignore_errors=True)
        raise RuntimeError(
            "V22: Auto-Untertitel nach 20 Minuten abgebrochen."
        ) from exc

    if result.returncode != 0:
        err = result.stderr.decode(
            errors="ignore"
        ).strip()
        shutil.rmtree(work, ignore_errors=True)
        raise RuntimeError(
            "V22: whisper.cpp konnte das Audio nicht verarbeiten.\n\n"
            + (err[-4000:] or f"Exit-Code {result.returncode}")
        )

    if not json_path.exists():
        shutil.rmtree(work, ignore_errors=True)
        raise RuntimeError(
            "V22: whisper.cpp hat keine JSON-Zeitstempel erzeugt."
        )

    try:
        import json

        data = json.loads(
            json_path.read_text(
                encoding="utf-8"
            )
        )

        words = []

        for seg in data.get("transcription", []):
            if not isinstance(seg, dict):
                continue

            text = str(
                seg.get("text", "")
                or ""
            ).strip()

            ts = seg.get(
                "timestamps",
                {},
            )

            if not text:
                continue

            try:
                start = _v22_parse_ts(ts.get("from"))
                end = _v22_parse_ts(ts.get("to"))
            except Exception:
                continue

            words.append(
                (
                    text,
                    start,
                    max(start + 0.05, end),
                )
            )

    except Exception as exc:
        shutil.rmtree(work, ignore_errors=True)
        raise RuntimeError(
            "V22: Die Whisper-Zeitstempel konnten nicht gelesen werden.\n\n"
            + str(exc)
        ) from exc

    shutil.rmtree(work, ignore_errors=True)

    if not words:
        raise RuntimeError(
            "V22: Keine deutschen Wörter erkannt."
        )

    groups = _v22_group_words(words)

    ass_dir = Path(
        tempfile.mkdtemp(
            prefix="schlawutzie_v22_ass_"
        )
    )
    ass_path = ass_dir / "deutsche_untertitel.ass"

    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "WrapStyle: 2",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: TikTok,Segoe UI,52,&H0000FFFF,&H00FFFFFF,&H00000000,&H99000000,"
        "-1,0,0,0,100,100,0,0,3,2,1,2,80,80,620,1",
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    for group in groups:
        start = group[0][1]
        end = max(
            group[-1][2],
            start + 0.25,
        )

        parts = []
        for token, word_start, word_end in group:
            k = max(
                1,
                int(
                    round(
                        (word_end - word_start)
                        * 100
                    )
                ),
            )
            parts.append(
                "{\\k"
                + str(k)
                + "}"
                + token
            )

        lines.append(
            "Dialogue: 0,"
            + _v22_ass_time(start)
            + ","
            + _v22_ass_time(end)
            + ",TikTok,,0,0,390,,"
            + " ".join(parts)
        )

    ass_path.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    if status_callback:
        status_callback(
            f"V22: {len(groups)} synchronisierte Untertitelblöcke erzeugt."
        )

    return str(ass_path)


def burn_ass_subtitles(
    input_video: str,
    ass_path: str,
    output_video: str,
):
    ff = ffmpeg_path()

    p = str(Path(ass_path).resolve())
    p = p.replace("\\", "/")
    p = p.replace(":", r"\:")
    p = p.replace("'", r"\'")

    cmd = [
        ff,
        "-y",
        "-i",
        str(input_video),
        "-vf",
        f"subtitles='{p}'",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        str(output_video),
    ]

    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if result.returncode != 0:
        raise RuntimeError(
            "V22: Untertitel konnten nicht in die MP4 eingebrannt werden.\n\n"
            + result.stderr.decode(errors="ignore")[-4000:]
        )


def _v22_subtitle_helper_entry(
    audio_path: str,
    output_ass: str,
    status_path: str,
    prompt_path: str,
):
    try:
        prompt = ""
        if Path(prompt_path).exists():
            prompt = Path(
                prompt_path
            ).read_text(
                encoding="utf-8"
            )

        def status_callback(message):
            _status_write(
                Path(status_path),
                message,
            )

        ass_path = transcribe_german_to_ass(
            audio_path,
            status_callback=status_callback,
            source_text=prompt,
        )

        shutil.copy2(
            ass_path,
            output_ass,
        )

        _status_write(
            Path(status_path),
            "V22: Deutsche Auto-Untertitel fertig.",
        )

        return 0

    except Exception as exc:
        _status_write(
            Path(status_path),
            "FEHLER: "
            + f"{type(exc).__name__}: {exc}",
        )
        return 1


if (
    __name__ == "__main__"
    and len(sys.argv) == 6
    and sys.argv[1] == "--v22-subtitle-helper"
):
    raise SystemExit(
        _v22_subtitle_helper_entry(
            sys.argv[2],
            sys.argv[3],
            sys.argv[4],
            sys.argv[5],
        )
    )


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

try:
    import winsound
except Exception:
    winsound = None


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title(APP_NAME)
        self.geometry("1120x820")
        self.minsize(980, 700)
        self.configure(bg="#101114")

        self.background_path = None
        self.audio_path = None
        self.generated_audio = None
        self.subtitle_path = None
        self.subtitle_process = None
        self.subtitle_temp_dir = None

        self.busy = False
        self.preview_frames = []
        self.preview_index = 0

        self._build_ui()
        self._load_default_image()

    def _build_ui(self):
        style = ttk.Style(self)

        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "TButton",
            padding=8,
        )

        style.configure(
            "TLabel",
            background="#101114",
            foreground="#e9eef2",
        )

        style.configure(
            "Header.TLabel",
            background="#101114",
            foreground="#f3f4f6",
            font=("Segoe UI", 17, "bold"),
        )

        root = ttk.Frame(
            self,
            padding=18,
        )

        root.pack(
            fill="both",
            expand=True,
        )

        ttk.Label(
            root,
            text=APP_NAME,
            style="Header.TLabel",
        ).pack(anchor="w")

        ttk.Label(
            root,
            text="1080 × 1920 • 9:16 • interne Rendergröße 720 × 1280",
        ).pack(
            anchor="w",
            pady=(2, 12),
        )

        body = ttk.Frame(root)
        body.pack(
            fill="both",
            expand=True,
        )

        left = ttk.Frame(body)
        left.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 16),
        )

        right = ttk.Frame(body)
        right.pack(
            side="right",
            fill="y",
        )

        ttk.Label(
            left,
            text="Text – einfach per Copy & Paste aus Browser, Word, Notepad usw.",
        ).pack(anchor="w")

        self.text_box = tk.Text(
            left,
            height=15,
            wrap="word",
            bg="#181a1f",
            fg="#f2f2f2",
            insertbackground="white",
            relief="flat",
            padx=12,
            pady=12,
            undo=True,
        )

        self.text_box.pack(
            fill="x",
            pady=(6, 6),
        )

        self.text_box.insert(
            "1.0",
            "Hier deinen Text einfügen …",
        )

        text_buttons = ttk.Frame(left)
        text_buttons.pack(
            anchor="w",
            pady=(0, 12),
        )

        ttk.Button(
            text_buttons,
            text="EINFÜGEN",
            command=self.paste_text,
        ).pack(
            side="left",
            padx=(0, 6),
        )

        ttk.Button(
            text_buttons,
            text="KOPIEREN",
            command=self.copy_text,
        ).pack(
            side="left",
            padx=(0, 6),
        )

        ttk.Button(
            text_buttons,
            text="ALLES LÖSCHEN",
            command=lambda: self.text_box.delete(
                "1.0",
                "end",
            ),
        ).pack(side="left")

        ttk.Label(
            left,
            text="Hintergrundbild",
        ).pack(anchor="w")

        self.image_label = ttk.Label(
            left,
            text="Noch kein Bild geladen.",
        )

        self.image_label.pack(
            anchor="w",
            pady=4,
        )

        ttk.Button(
            left,
            text="BILD LADEN",
            command=self.load_image,
        ).pack(
            anchor="w",
            pady=(0, 12),
        )

        ttk.Label(
            left,
            text="Audio",
        ).pack(anchor="w")

        self.audio_label = ttk.Label(
            left,
            text="Kein Audio geladen.",
        )

        self.audio_label.pack(
            anchor="w",
            pady=4,
        )

        audio_buttons = ttk.Frame(left)
        audio_buttons.pack(
            anchor="w",
            pady=(0, 10),
        )

        ttk.Button(
            audio_buttons,
            text="STEFANM ERZEUGEN",
            command=self.generate_voice,
        ).pack(
            side="left",
            padx=(0, 8),
        )

        ttk.Button(
            audio_buttons,
            text="WAV/MP3 LADEN",
            command=self.load_audio,
        ).pack(side="left")

        ttk.Button(
            audio_buttons,
            text="DEUTSCHE AUTO-UNTERTITEL",
            command=self.generate_subtitles,
        ).pack(
            side="left",
            padx=(0, 8),
        )

        self.subtitle_status = ttk.Label(
            left,
            text="Auto-Untertitel: noch nicht erzeugt.",
        )
        self.subtitle_status.pack(
            anchor="w",
            pady=(0, 6),
        )

        self.voice_status = ttk.Label(
            left,
            text="Microsoft OneCore / Microsoft Stefan • kein TTS-Fallback",
        )

        self.voice_status.pack(
            anchor="w",
            pady=(0, 12),
        )

        action_buttons = ttk.Frame(left)
        action_buttons.pack(
            anchor="w",
            pady=(4, 0),
        )

        ttk.Button(
            action_buttons,
            text="VORSCHAU",
            command=self.preview,
        ).pack(
            side="left",
            padx=(0, 8),
        )

        ttk.Button(
            action_buttons,
            text="MP4 SPEICHERN",
            command=self.export,
        ).pack(side="left")

        self.progress = ttk.Progressbar(
            left,
            mode="determinate",
        )

        self.progress.pack(
            fill="x",
            pady=(14, 4),
        )

        self.status = ttk.Label(
            left,
            text="Bereit.",
        )

        self.status.pack(
            anchor="w",
        )

        ttk.Label(
            right,
            text="Vorschau",
        ).pack(anchor="w")

        self.preview_canvas = tk.Canvas(
            right,
            width=360,
            height=640,
            bg="black",
            highlightthickness=0,
        )

        self.preview_canvas.pack(
            pady=6,
        )

        self.preview_photo = None

    def _load_default_image(self):
        if DEFAULT_IMAGE.exists():
            self.background_path = str(
                DEFAULT_IMAGE
            )

            self.image_label.config(
                text="Standardbild: assets/schlawutzie.png"
            )

            self.show_static_preview()

        else:
            self.image_label.config(
                text="WARNUNG: assets/schlawutzie.png fehlt."
            )

    def set_status(self, text):
        self.status.config(text=text)
        self.update_idletasks()

    def copy_text(self):
        try:
            selected = self.text_box.get(
                "sel.first",
                "sel.last",
            )
        except tk.TclError:
            selected = self.text_box.get(
                "1.0",
                "end-1c",
            )

        self.clipboard_clear()
        self.clipboard_append(selected)
        self.update()

        self.set_status(
            "Text in die Zwischenablage kopiert."
        )

    def paste_text(self):
        try:
            text = self.clipboard_get()
        except tk.TclError:
            messagebox.showwarning(
                "EINFÜGEN",
                "Die Zwischenablage enthält keinen lesbaren Text.",
            )
            return

        try:
            self.text_box.delete(
                "sel.first",
                "sel.last",
            )
        except tk.TclError:
            pass

        self.text_box.insert(
            "insert",
            text,
        )

        self.set_status(
            "Text aus der Zwischenablage eingefügt."
        )

    def load_image(self):
        path = filedialog.askopenfilename(
            filetypes=[
                (
                    "Bilder",
                    "*.png *.jpg *.jpeg *.webp",
                ),
                (
                    "Alle Dateien",
                    "*.*",
                ),
            ]
        )

        if not path:
            return

        self.background_path = path
        self.image_label.config(
            text=os.path.basename(path)
        )

        self.show_static_preview()

    def load_audio(self):
        path = filedialog.askopenfilename(
            filetypes=[
                (
                    "Audio",
                    "*.wav *.mp3 *.m4a *.aac *.flac *.ogg",
                ),
                (
                    "Alle Dateien",
                    "*.*",
                ),
            ]
        )

        if not path:
            return

        try:
            self.audio_path = audio_to_wav(path)

            self.audio_label.config(
                text=f"Audio: {os.path.basename(path)}"
            )

            self.set_status(
                "Audio geladen."
            )

        except Exception as exc:
            messagebox.showerror(
                "Audio",
                str(exc),
            )


    def generate_subtitles(self):
        if self.busy:
            return

        if not self.audio_path:
            messagebox.showwarning(
                "Audio fehlt",
                "Bitte zuerst StefanM erzeugen oder WAV/MP3 laden.",
            )
            return

        self.busy = True
        self.subtitle_status.config(
            text="Auto-Untertitel: Synchronisierung läuft …"
        )
        self.set_status(
            "V22: deutsche Auto-Untertitel werden erzeugt …"
        )

        temp_dir = Path(
            tempfile.mkdtemp(
                prefix="schlawutzie_v22_subtitle_job_"
            )
        )
        self.subtitle_temp_dir = temp_dir

        input_path = temp_dir / "audio.wav"
        output_path = temp_dir / "deutsche_untertitel.ass"
        status_path = temp_dir / "status.txt"
        prompt_path = temp_dir / "prompt.txt"

        try:
            shutil.copy2(
                self.audio_path,
                input_path,
            )
            prompt_path.write_text(
                self.text_box.get(
                    "1.0",
                    "end-1c",
                ).strip(),
                encoding="utf-8",
            )
        except Exception as exc:
            self._subtitle_error(str(exc))
            return

        command = [
            sys.executable,
            "--v22-subtitle-helper",
            str(input_path),
            str(output_path),
            str(status_path),
            str(prompt_path),
        ]

        self.subtitle_process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(
                subprocess,
                "CREATE_NO_WINDOW",
                0,
            ),
        )

        self._poll_v22_subtitles(
            output_path,
            status_path,
        )

    def _poll_v22_subtitles(
        self,
        output_path: Path,
        status_path: Path,
    ):
        process = self.subtitle_process

        if process is None:
            self._subtitle_error(
                "Der V22-Untertitelprozess ist nicht verfügbar."
            )
            return

        if status_path.exists():
            try:
                status = status_path.read_text(
                    encoding="utf-8"
                ).strip()
            except Exception:
                status = ""

            if status:
                self.set_status(status)

        code = process.poll()

        if code is None:
            self.after(
                250,
                lambda: self._poll_v22_subtitles(
                    output_path,
                    status_path,
                ),
            )
            return

        self.subtitle_process = None

        if (
            code == 0
            and output_path.exists()
            and output_path.stat().st_size > 100
        ):
            self._subtitle_done(
                str(output_path)
            )
            return

        status = ""
        if status_path.exists():
            try:
                status = status_path.read_text(
                    encoding="utf-8"
                ).strip()
            except Exception:
                pass

        self._subtitle_error(
            status
            or f"V22-Untertitelprozess beendet mit Exit-Code {code}."
        )

    def _subtitle_done(self, path):
        self.busy = False

        fd, stable_path = tempfile.mkstemp(
            prefix="schlawutzie_v22_",
            suffix=".ass",
        )
        os.close(fd)

        shutil.copy2(
            path,
            stable_path,
        )
        self.subtitle_path = stable_path

        self.subtitle_status.config(
            text="Auto-Untertitel: Deutsch • synchron • fertig.",
        )
        self.set_status(
            "V22: deutsche Auto-Untertitel fertig."
        )

        if self.subtitle_temp_dir is not None:
            shutil.rmtree(
                self.subtitle_temp_dir,
                ignore_errors=True,
            )
            self.subtitle_temp_dir = None

    def _subtitle_error(self, message):
        self.busy = False
        self.subtitle_path = None

        self.subtitle_status.config(
            text="Auto-Untertitel: Fehler.",
        )
        self.set_status(
            "V22: Auto-Untertitel fehlgeschlagen."
        )

        if self.subtitle_temp_dir is not None:
            shutil.rmtree(
                self.subtitle_temp_dir,
                ignore_errors=True,
            )
            self.subtitle_temp_dir = None

        messagebox.showerror(
            "Deutsche Auto-Untertitel",
            message,
        )

    def generate_voice(self):
        if self.busy:
            return

        text = self.text_box.get(
            "1.0",
            "end",
        ).strip()

        if (
            not text
            or text == "Hier deinen Text einfügen …"
        ):
            messagebox.showwarning(
                "Text fehlt",
                "Bitte zuerst Text eingeben oder per Copy & Paste einfügen.",
            )
            return

        self.busy = True

        self.set_status(
            "StefanM wird erzeugt …"
        )

        threading.Thread(
            target=self._voice_worker,
            args=(text,),
            daemon=True,
        ).start()

    def _voice_worker(self, text):
        try:
            def status_callback(message):
                self.after(
                    0,
                    lambda m=message: self.set_status(m),
                )

            path = synthesize_stefan(
                text,
                status_callback=status_callback,
            )

            self.after(
                0,
                lambda: self._voice_done(path),
            )

        except Exception as exc:
            self.after(
                0,
                lambda: self._voice_error(str(exc)),
            )

    def _voice_done(self, path):
        self.busy = False

        self.generated_audio = path
        self.audio_path = path

        self.audio_label.config(
            text="Audio: StefanM.wav"
        )

        self.set_status(
            "StefanM-Audio fertig."
        )

    def _voice_error(self, message):
        self.busy = False

        self.set_status(
            "StefanM nicht verfügbar."
        )

        messagebox.showerror(
            "StefanM",
            message,
        )

    def show_static_preview(self):
        if not self.background_path:
            return

        image = fit_cover(
            Image.open(self.background_path),
            (360, 640),
        )

        self.preview_photo = ImageTk.PhotoImage(
            image
        )

        self.preview_canvas.delete("all")

        self.preview_canvas.create_image(
            180,
            320,
            image=self.preview_photo,
        )

    def preview(self):
        if not self.background_path:
            messagebox.showwarning(
                "Bild fehlt",
                "Bitte zuerst ein Hintergrundbild laden.",
            )
            return

        if not self.audio_path:
            messagebox.showwarning(
                "Audio fehlt",
                "Bitte StefanM erzeugen oder WAV/MP3 laden.",
            )
            return

        self.set_status(
            "Vorschau wird vorbereitet …"
        )

        threading.Thread(
            target=self._preview_worker,
            daemon=True,
        ).start()

    def _preview_worker(self):
        try:
            bg = fit_cover(
                Image.open(self.background_path),
                (IN_W, IN_H),
            )

            rate, data = read_audio_pcm(
                self.audio_path
            )

            duration = min(
                8.0,
                len(data) / rate
                if rate
                else 0,
            )

            count = max(
                1,
                int(duration * FPS),
            )

            _, amps = amplitude_curve(
                self.audio_path,
                count,
            )

            frames = []

            for i in range(count):
                frame = draw_neural_hud(
                    bg,
                    float(amps[i]),
                    i / FPS,
                )

                frames.append(
                    frame.resize(
                        (360, 640),
                        Image.Resampling.LANCZOS,
                    )
                )

            self.after(
                0,
                lambda: self._start_preview(frames),
            )

        except Exception as exc:
            self.after(
                0,
                lambda: messagebox.showerror(
                    "Vorschau",
                    str(exc),
                ),
            )

    def _start_preview(self, frames):
        self.preview_frames = frames
        self.preview_index = 0

        if winsound and self.audio_path:
            try:
                winsound.PlaySound(
                    self.audio_path,
                    winsound.SND_FILENAME
                    | winsound.SND_ASYNC,
                )
            except Exception:
                pass

        self.set_status(
            "Vorschau läuft …"
        )

        self._animate_preview()

    def _animate_preview(self):
        if not self.preview_frames:
            return

        frame = self.preview_frames[
            self.preview_index
        ]

        self.preview_photo = ImageTk.PhotoImage(
            frame
        )

        self.preview_canvas.delete("all")

        self.preview_canvas.create_image(
            180,
            320,
            image=self.preview_photo,
        )

        self.preview_index += 1

        if (
            self.preview_index
            < len(self.preview_frames)
        ):
            self.after(
                1000 // FPS,
                self._animate_preview,
            )
        else:
            if winsound:
                try:
                    winsound.PlaySound(None, 0)
                except Exception:
                    pass

            self.set_status(
                "Vorschau fertig."
            )

    def export(self):
        if self.busy:
            return

        if not self.background_path:
            messagebox.showwarning(
                "Bild fehlt",
                "Bitte zuerst ein Hintergrundbild laden.",
            )
            return

        if not self.audio_path:
            messagebox.showwarning(
                "Audio fehlt",
                "Bitte StefanM erzeugen oder WAV/MP3 laden.",
            )
            return

        output = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[
                ("MP4", "*.mp4"),
            ],
            initialfile="SchlauWutzie_V22_2_FINAL.mp4",
        )

        if not output:
            return

        self.busy = True
        self.progress["value"] = 0

        self.set_status(
            "V22.1: Intro + Hauptvideo + Untertitel werden gerendert …"
        )

        threading.Thread(
            target=self._export_worker,
            args=(output,),
            daemon=True,
        ).start()

    def _export_worker(self, output):
        try:
            def progress(done, total):
                value = (
                    100.0
                    * done
                    / max(1, total)
                )

                self.after(
                    0,
                    lambda v=value:
                        self.progress.configure(
                            value=v
                        ),
                )

            # Render the proven V21.5 main video first.
            temp_main = Path(
                tempfile.mkstemp(
                    prefix="schlawutzie_v21_5_main_",
                    suffix=".mp4",
                )[1]
            )
            try:
                render_video(
                    self.background_path,
                    self.audio_path,
                    str(temp_main),
                    progress,
                )

                final_main = temp_main
                temp_files = [temp_main]

                # IMPORTANT: Whether subtitles were generated beforehand with
                # the button or generated automatically during export, they
                # MUST be burned into the main video before the intro is added.
                # The previous V22 accidentally skipped this when
                # self.subtitle_path already existed.
                ass_path = self.subtitle_path

                if not ass_path:
                    self.set_status(
                        "V22: deutsche Auto-Untertitel werden synchron erzeugt …"
                    )

                    source_text = self.text_box.get(
                        "1.0",
                        "end-1c",
                    ).strip()

                    ass_path = transcribe_german_to_ass(
                        self.audio_path,
                        status_callback=self.set_status,
                        source_text=source_text,
                    )

                self.set_status(
                    "V22: Untertitel werden in das Hauptvideo eingebrannt …"
                )

                subtitled = Path(
                    tempfile.mkstemp(
                        prefix="schlawutzie_v22_subtitled_",
                        suffix=".mp4",
                    )[1]
                )

                burn_ass_subtitles(
                    str(temp_main),
                    str(ass_path),
                    str(subtitled),
                )

                final_main = subtitled
                temp_files.append(subtitled)

                # Intro is kept clean; subtitles belong only to the spoken main video.
                prepend_intro(
                    str(INTRO_VIDEO),
                    str(final_main),
                    output,
                )

                for temp_file in temp_files:
                    try:
                        if temp_file.exists():
                            temp_file.unlink()
                    except OSError:
                        pass
            finally:
                try:
                    if temp_main.exists():
                        temp_main.unlink()
                except OSError:
                    pass

            output_path = Path(output)

            if (
                not output_path.exists()
                or output_path.stat().st_size < 1024
            ):
                raise RuntimeError(
                    "Die MP4-Datei wurde nicht korrekt erzeugt."
                )

            self.after(
                0,
                lambda: self._export_done(output),
            )

        except Exception as exc:
            self.after(
                0,
                lambda: self._export_error(
                    str(exc)
                ),
            )

    def _export_done(self, output):
        self.busy = False
        self.progress["value"] = 100

        self.set_status(
            "V22.1: Intro + Hauptvideo + Untertitel fertig."
        )

        messagebox.showinfo(
            "Fertig",
            f"MP4 gespeichert:\n{output}",
        )

    def _export_error(self, message):
        self.busy = False

        self.set_status(
            "Export fehlgeschlagen."
        )

        messagebox.showerror(
            "MP4-Export",
            message,
        )


if __name__ == "__main__":
    App().mainloop()
