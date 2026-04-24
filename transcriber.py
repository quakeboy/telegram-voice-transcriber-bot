import logging
import time
import tempfile
from pathlib import Path
from typing import Optional
import whisper

logger = logging.getLogger("transcriber")


class Transcriber:
    def __init__(
        self,
        model_name: str,
        language: str,
        max_attempts: int,
        initial_backoff: int,
        timeout_seconds: int
    ):
        self.model_name = model_name
        self.language = language
        self.max_attempts = max_attempts
        self.initial_backoff = initial_backoff
        self.timeout_seconds = timeout_seconds

        try:
            self.model = whisper.load_model(model_name)
            logger.info(f"Whisper model '{model_name}' loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model '{model_name}': {e}")
            raise

    def transcribe_with_retry(self, audio_filepath: str) -> Optional[str]:
        """Transcribe audio with exponential backoff retry. Returns transcribed text or None."""
        backoff = self.initial_backoff

        for attempt in range(1, self.max_attempts + 1):
            try:
                logger.debug(f"Transcription attempt {attempt}/{self.max_attempts} for {Path(audio_filepath).name}")
                result = self.model.transcribe(
                    audio_filepath,
                    language=self.language,
                    fp16=False
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
