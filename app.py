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


APP_NAME = "SchlauWutzie K.I. – Video Studio V21.2 FINAL"
IN_W, IN_H = 720, 1280
OUT_W, OUT_H = 1080, 1920
FPS = 30


def resource_path(relative_path: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / relative_path


DEFAULT_IMAGE = resource_path("assets/schlawutzie.png")


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
    """V21.2: Referenzgetreue, transparente K.I.-Premium-Animation."""

    frame = background.convert("RGBA")
    hud = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(hud, "RGBA")

    cx = IN_W // 2
    cy = IN_H - 165
    activity = max(0.0, min(1.0, float(amplitude)))

    # Sehr dezente horizontale Führungslinie.
    d.line(
        (108, cy + 98, IN_W - 108, cy + 98),
        fill=(70, 170, 235, 22),
        width=1,
    )

    # Sprachreaktiver K.I.-Core.
    pulse = 1.0 + 0.10 * activity + 0.018 * math.sin(t * 3.0)
    core_r = int(46 * pulse)

    # Konzentrische Ringe wie im Referenzbild.
    for i in range(7):
        rr = core_r + 8 + i * 12
        alpha = 32 + int(activity * 45)

        d.ellipse(
            (cx - rr, cy - rr, cx + rr, cy + rr),
            outline=(54, 181, 247, alpha),
            width=2,
        )

        angle = (t * (15 + i * 1.6) + i * 38) % 360

        d.arc(
            (cx - rr, cy - rr, cx + rr, cy + rr),
            angle,
            angle + 75,
            fill=(255, 195, 82, 85 + int(30 * activity)),
            width=2,
        )

        d.arc(
            (cx - rr, cy - rr, cx + rr, cy + rr),
            angle + 178,
            angle + 228,
            fill=(77, 207, 255, 75 + int(24 * activity)),
            width=2,
        )

    # Kleine neuronale Orbitpunkte.
    nodes = []
    for i in range(16):
        angle = i * math.tau / 16 - t * (0.18 + i * 0.004)
        rr = core_r + 34 + 17 * math.sin(t * 0.9 + i * 0.6)

        x = cx + math.cos(angle) * rr
        y = cy + math.sin(angle) * rr * 0.72
        nodes.append((x, y))

        dot = 2.0 + 1.8 * activity
        d.ellipse(
            (x - dot, y - dot, x + dot, y + dot),
            fill=(255, 208, 103, 145 + int(activity * 60)),
        )

    for i in range(0, len(nodes), 2):
        x1, y1 = nodes[i]
        x2, y2 = nodes[(i + 3) % len(nodes)]
        d.line(
            (x1, y1, x2, y2),
            fill=(77, 193, 250, 55 + int(activity * 35)),
            width=1,
        )

    # Zentrales Gehirn-/K.I.-Symbol.
    brain_w, brain_h = 50, 58

    d.ellipse(
        (
            cx - brain_w // 2,
            cy - brain_h // 2,
            cx + brain_w // 2,
            cy + brain_h // 2,
        ),
        outline=(235, 244, 255, 225),
        width=2,
    )

    d.arc(
        (
            cx - brain_w // 2,
            cy - brain_h // 2,
            cx + 1,
            cy + brain_h // 2,
        ),
        90,
        270,
        fill=(255, 202, 91, 245),
        width=2,
    )

    d.arc(
        (
            cx - 1,
            cy - brain_h // 2,
            cx + brain_w // 2,
            cy + brain_h // 2,
        ),
        270,
        90,
        fill=(74, 202, 255, 245),
        width=2,
    )

    d.line(
        (cx, cy - 25, cx, cy + 25),
        fill=(255, 255, 255, 120),
        width=1,
    )

    # Kleine Synapsen im Core.
    for i in range(9):
        a = i * math.tau / 9 + t * 0.12
        rr = 14 + 4 * math.sin(t + i)
        x = cx + math.cos(a) * rr
        y = cy + math.sin(a) * rr * 0.72

        d.ellipse(
            (x - 1.8, y - 1.8, x + 1.8, y + 1.8),
            fill=(255, 215, 120, 170 + int(40 * activity)),
        )

    # Sprechimpuls läuft vom Core nach außen.
    if activity > 0.045:
        phase = (t * 1.7) % 1.0
        travel = max(0.0, 1.0 - abs(phase - 0.25) / 0.25)
        rr = int(core_r + 10 + 80 * phase)

        d.ellipse(
            (cx - rr, cy - rr, cx + rr, cy + rr),
            outline=(
                100,
                221,
                255,
                max(15, int(175 * travel * activity)),
            ),
            width=2,
        )

    # Feine, sprachreaktive Waveform.
    x0 = 120
    x1 = IN_W - 120
    base_y = cy + 92

    upper = []
    lower = []

    for x in range(x0, x1 + 1, 3):
        u = (x - x0) / float(x1 - x0)
        envelope = 0.12 + 0.88 * (math.sin(math.pi * u) ** 0.60)

        wave = (
            0.58 * math.sin(u * 45 + t * 11.0)
            + 0.25 * math.sin(u * 93 - t * 5.5)
            + 0.11 * math.sin(u * 177 + t * 4.0)
        )

        scale = (2.0 + 41.0 * activity) * envelope

        upper.append((x, base_y - wave * scale))
        lower.append((x, base_y + wave * scale * 0.24))

    d.line(
        upper,
        fill=(93, 209, 255, 220),
        width=max(2, int(2 + 2 * activity)),
    )

    d.line(
        lower,
        fill=(255, 201, 91, 120),
        width=1,
    )

    # Gold/Cyan-Endmarker.
    d.line(
        (x0 - 18, base_y, x0, base_y),
        fill=(255, 200, 88, 170),
        width=2,
    )
    d.line(
        (x1, base_y, x1 + 18, base_y),
        fill=(77, 202, 255, 170),
        width=2,
    )

    # Referenzbeschriftung.
    small = font(11)
    medium = font(14, True)

    label_y = cy + 112

    d.line(
        (cx - 98, label_y, cx - 72, label_y),
        fill=(255, 196, 83, 130),
        width=1,
    )
    d.line(
        (cx + 72, label_y, cx + 98, label_y),
        fill=(77, 202, 255, 130),
        width=1,
    )

    d.text(
        (cx - 46, label_y - 8),
        "K.I. ONLINE",
        font=medium,
        fill=(247, 238, 216, 210),
    )

    d.text(
        (cx - 100, label_y + 20),
        "ANALYSE · DENKEN · VERKNÜPFEN",
        font=small,
        fill=(215, 225, 233, 165),
    )

    for i in range(5):
        xx = cx - 28 + i * 14
        yy = label_y + 48
        alpha = 105 + int(70 * activity) if i < 3 else 60

        d.ellipse(
            (xx - 1.5, yy - 1.5, xx + 1.5, yy + 1.5),
            fill=(255, 197, 87, alpha)
            if i % 2 == 0
            else (77, 204, 255, alpha),
        )

    # Premium Glow, bewusst dezent.
    glow = hud.filter(ImageFilter.GaussianBlur(8))
    glow2 = hud.filter(ImageFilter.GaussianBlur(2.4))

    return Image.alpha_composite(
        Image.alpha_composite(
            Image.alpha_composite(frame, glow),
            glow2,
        ),
        hud,
    ).convert("RGB")


# ---------------------------------------------------------------------------
# MP4 rendering
# ---------------------------------------------------------------------------

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
            initialfile="SchlauWutzie_V20_FINAL.mp4",
        )

        if not output:
            return

        self.busy = True
        self.progress["value"] = 0

        self.set_status(
            "MP4 wird gerendert …"
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

            render_video(
                self.background_path,
                self.audio_path,
                output,
                progress,
            )

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
            "MP4 fertig."
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
