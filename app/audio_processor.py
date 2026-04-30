import os
import re
import shutil
import subprocess
import sys
from typing import Optional

from .config import OUTPUT_DIR, UPLOAD_DIR
from .database import Job, SessionLocal


def process_audio(
    job_id: str,
    file_name: str,
    output_format: str = "wav",
    split_mode: str = "ai_split",
    high_quality: bool = False,
    source_outputs_job_id: Optional[str] = None
):
    input_path = os.path.join(UPLOAD_DIR, file_name)
    job_output_dir = os.path.join(OUTPUT_DIR, job_id)
    os.makedirs(job_output_dir, exist_ok=True)
    ffmpeg_binary = shutil.which("ffmpeg")

    db = SessionLocal()

    try:
        if source_outputs_job_id:
            source_output_dir = os.path.join(OUTPUT_DIR, source_outputs_job_id)
            if not _copy_cached_outputs(source_output_dir, job_output_dir):
                return False, "Keşlənmiş çıxış faylları tapılmadı."
        else:
            if split_mode != "ai_split":
                return False, "Hazırda yalnız AI Split dəstəklənir."

            model_name = "htdemucs_ft" if high_quality else "htdemucs"
            command = [
                sys.executable,
                "-m",
                "app.demucs_runner",
                "--name",
                model_name,
                "--two-stems=vocals",
                "--device",
                "cpu",
                "--jobs",
                "4",
                "-o",
                job_output_dir,
                input_path,
            ]

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            output_lines = []
            if process.stdout is not None:
                for line in process.stdout:
                    clean_line = line.strip()
                    output_lines.append(clean_line)
                    print(f"Demucs: {clean_line}")
                    match = re.search(r"(\d+)%\|", line)
                    if match:
                        percent = int(match.group(1))
                        job = db.query(Job).filter(Job.id == job_id).first()
                        if job:
                            # Demucs may emit multiple progress bars; never move persisted progress backward.
                            job.progress = max(job.progress or 0.0, percent / 100.0)
                            db.commit()

            process.wait()

            if process.returncode != 0:
                return False, output_lines[-1] if output_lines else "Demucs emal zamanı xəta verdi."

            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.progress = max(job.progress or 0.0, 0.95)
                db.commit()

            if not _collect_demucs_outputs(job_output_dir):
                return False, "Demucs çıxış faylları tapılmadı."

        success, error = _ensure_requested_outputs(
            output_dir=job_output_dir,
            output_format=output_format.lower(),
            high_quality=high_quality,
            ffmpeg_binary=ffmpeg_binary
        )
        if not success:
            return False, error

        return True, None
    except Exception as exc:
        return False, str(exc)
    finally:
        db.close()


def _copy_cached_outputs(source_output_dir: str, target_output_dir: str) -> bool:
    copied = False
    for file_name in ("vocals.wav", "instrumental.wav", "vocals.mp3", "instrumental.mp3"):
        source_path = os.path.join(source_output_dir, file_name)
        if os.path.exists(source_path):
            shutil.copy2(source_path, os.path.join(target_output_dir, file_name))
            copied = True
    return copied


def _collect_demucs_outputs(job_output_dir: str) -> bool:
    found_vocals = False
    found_instrumental = False

    for root, _, files in os.walk(job_output_dir):
        if "vocals.wav" in files:
            target = os.path.join(job_output_dir, "vocals.wav")
            if os.path.exists(target):
                os.remove(target)
            shutil.move(os.path.join(root, "vocals.wav"), target)
            found_vocals = True
        if "no_vocals.wav" in files:
            target = os.path.join(job_output_dir, "instrumental.wav")
            if os.path.exists(target):
                os.remove(target)
            shutil.move(os.path.join(root, "no_vocals.wav"), target)
            found_instrumental = True

    return found_vocals and found_instrumental


def _ensure_requested_outputs(output_dir: str, output_format: str, high_quality: bool, ffmpeg_binary: Optional[str]):
    vocals_wav = os.path.join(output_dir, "vocals.wav")
    instrumental_wav = os.path.join(output_dir, "instrumental.wav")

    if not os.path.exists(vocals_wav) or not os.path.exists(instrumental_wav):
        return False, "Əsas WAV çıxışları tapılmadı."

    if output_format == "wav":
        return True, None

    if output_format != "mp3":
        return False, "Dəstəklənməyən export formatı."

    if not ffmpeg_binary:
        return False, "FFmpeg sistemdə tapılmadı."

    bitrate = "320k" if high_quality else "192k"
    for stem in ("vocals", "instrumental"):
        input_file = os.path.join(output_dir, f"{stem}.wav")
        output_file = os.path.join(output_dir, f"{stem}.mp3")
        if os.path.exists(output_file):
            continue

        command = [
            ffmpeg_binary,
            "-y",
            "-i",
            input_file,
            "-codec:a",
            "libmp3lame",
            "-b:a",
            bitrate,
            output_file,
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            return False, f"MP3 konvertasiya xətası: {result.stderr.strip()}"

    return True, None
