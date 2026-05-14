import logging
import time
from pathlib import Path
from typing import Optional
import mlx_whisper

logger = logging.getLogger("transcriber")

_MLX_REPOS = {
    "tiny":   "mlx-community/whisper-tiny-mlx",
    "base":   "mlx-community/whisper-base-mlx",
    "small":  "mlx-community/whisper-small-mlx",
    "medium": "mlx-community/whisper-medium-mlx",
    "large":  "mlx-community/whisper-large-mlx",
    "turbo":  "mlx-community/whisper-large-v3-turbo",
}


class Transcriber:
    def __init__(
        self,
        model_name: str,
        language: str,
        max_attempts: int,
        initial_backoff: int,
        timeout_seconds: int
    ):
        self.language = language
        self.max_attempts = max_attempts
        self.initial_backoff = initial_backoff
        self.timeout_seconds = timeout_seconds

        if model_name not in _MLX_REPOS:
            raise ValueError(f"Unknown model '{model_name}'. Choose from: {', '.join(_MLX_REPOS)}")
        self.hf_repo = _MLX_REPOS[model_name]
        logger.info(f"Whisper model '{model_name}' ({self.hf_repo}) will load on first transcription")

    def transcribe_with_retry(self, audio_filepath: str) -> Optional[str]:
        """Transcribe audio with exponential backoff retry. Returns transcribed text or None."""
        backoff = self.initial_backoff

        for attempt in range(1, self.max_attempts + 1):
            try:
                logger.debug(f"Transcription attempt {attempt}/{self.max_attempts} for {Path(audio_filepath).name}")
                result = mlx_whisper.transcribe(
                    audio_filepath,
                    path_or_hf_repo=self.hf_repo,
                    language=self.language,
                )
                return result["text"].strip()

            except Exception as e:
                if attempt < self.max_attempts:
                    logger.warning(f"Transcription attempt {attempt}/{self.max_attempts} failed: {e}")
                    logger.debug(f"Retrying in {backoff} seconds...")
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    logger.error(f"Transcription failed after {self.max_attempts} attempts: {e}")
                    return None

        return None
