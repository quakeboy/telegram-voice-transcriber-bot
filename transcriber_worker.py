#!/usr/bin/env python3
"""
Subprocess worker for transcription.
Runs as a separate process to allow memory release after transcription.

Expected stdin: JSON {"audio_path": "...", "model": "small-q8", "language": "en"}
Returns to stdout: JSON {"text": "...", "token_count": 42}
On error to stderr: JSON {"error": "..."}
"""

import sys
import json
import logging
import time
from pathlib import Path
from typing import Optional
import mlx_whisper
import tiktoken

from logger_config import setup_logger

logger = None

_MLX_REPOS = {
    "tiny":   "mlx-community/whisper-tiny-mlx",
    "base":   "mlx-community/whisper-base-mlx",
    "small":  "mlx-community/whisper-small-mlx",
    "small-q8":  "mlx-community/whisper-small.en-mlx-8bit",
    "medium": "mlx-community/whisper-medium-mlx",
    "large":  "mlx-community/whisper-large-mlx",
    "turbo":  "mlx-community/whisper-large-v3-turbo",
}


def transcribe_with_retry(
    audio_filepath: str,
    model_name: str,
    language: str,
    max_attempts: int = 3,
    initial_backoff: int = 1
) -> Optional[str]:
    """Transcribe audio with exponential backoff retry. Returns transcribed text or None."""
    if model_name not in _MLX_REPOS:
        raise ValueError(f"Unknown model '{model_name}'. Choose from: {', '.join(_MLX_REPOS)}")

    hf_repo = _MLX_REPOS[model_name]
    logger.info(f"Loading Whisper model '{model_name}' ({hf_repo})")
    backoff = initial_backoff

    for attempt in range(1, max_attempts + 1):
        try:
            logger.debug(f"Transcription attempt {attempt}/{max_attempts} for {Path(audio_filepath).name}")
            result = mlx_whisper.transcribe(
                audio_filepath,
                path_or_hf_repo=hf_repo,
                language=language,
            )
            logger.info(f"Transcription successful for {Path(audio_filepath).name}")
            return result["text"].strip()

        except Exception as e:
            if attempt < max_attempts:
                logger.warning(f"Transcription attempt {attempt}/{max_attempts} failed: {e}")
                logger.debug(f"Retrying in {backoff} seconds...")
                time.sleep(backoff)
                backoff *= 2
            else:
                logger.error(f"Transcription failed after {max_attempts} attempts: {e}")
                raise

    return None


def main():
    global logger

    try:
        request = json.loads(sys.stdin.read())
        audio_path = request["audio_path"]
        model = request["model"]
        language = request.get("language", "en")
        max_attempts = request.get("max_attempts", 3)
        initial_backoff = request.get("initial_backoff_seconds", 1)

        # Setup logging for worker
        workspace = str(Path(audio_path).parent.parent)  # go up from audio_fifo to workspace
        log_folder = str(Path(workspace) / "logs")
        logger = setup_logger(log_folder, "INFO", log_name="transcriber_worker")

        transcribed_text = transcribe_with_retry(
            audio_path,
            model_name=model,
            language=language,
            max_attempts=max_attempts,
            initial_backoff=initial_backoff
        )

        if transcribed_text:
            tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")
            token_count = len(tokenizer.encode(transcribed_text))
            result = {
                "text": transcribed_text,
                "token_count": token_count
            }
            print(json.dumps(result))
            sys.exit(0)
        else:
            error_msg = "Transcription returned empty result"
            logger.error(error_msg)
            print(json.dumps({"error": error_msg}), file=sys.stderr)
            sys.exit(1)

    except json.JSONDecodeError as e:
        error_msg = f"Invalid JSON in stdin: {e}"
        print(json.dumps({"error": error_msg}), file=sys.stderr)
        sys.exit(1)
    except KeyError as e:
        error_msg = f"Missing required field in request: {e}"
        print(json.dumps({"error": error_msg}), file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        error_msg = str(e)
        if logger:
            logger.error(error_msg)
        print(json.dumps({"error": error_msg}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
