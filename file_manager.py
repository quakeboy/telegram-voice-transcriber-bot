import os
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta
import yaml

logger = logging.getLogger("transcriber")


class FileManager:
    def __init__(self, workspace: str, max_audio_files: int, verbose_cleanup: bool = False, timezone_offset_hours: int = 0):
        self.workspace = Path(workspace)
        self.audio_folder = self.workspace / "audio_fifo"
        self.transcription_folder = self.workspace / "transcriptions"
        self.max_audio_files = max_audio_files
        self.verbose_cleanup = verbose_cleanup
        self.local_tz = timezone(timedelta(hours=timezone_offset_hours))

        self.audio_folder.mkdir(parents=True, exist_ok=True)
        self.transcription_folder.mkdir(parents=True, exist_ok=True)

    def _to_local(self, timestamp: datetime) -> datetime:
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return timestamp.astimezone(self.local_tz)

    def save_audio(
        self,
        audio_data: bytes,
        timestamp: datetime,
        sender_username: str
    ) -> str:
        """Save audio file and cleanup old files if needed. Returns audio filepath."""
        local_ts = self._to_local(timestamp)
        filename = local_ts.strftime("%Y-%m-%d-%H-%M-%S") + f"_{sender_username}.ogg"
        filepath = self.audio_folder / filename

        with open(filepath, "wb") as f:
            f.write(audio_data)

        self._cleanup_old_audio_files()
        return str(filepath)

    def _cleanup_old_audio_files(self):
        """Remove oldest audio files if count exceeds max."""
        audio_files = sorted(
            self.audio_folder.glob("*.ogg"),
            key=lambda f: f.stat().st_ctime
        )

        while len(audio_files) > self.max_audio_files:
            oldest = audio_files.pop(0)
            oldest.unlink()
            msg = f"Deleted old audio file: {oldest.name}"
            if self.verbose_cleanup:
                logger.info(msg)
            else:
                logger.debug(msg)

    def save_transcription(
        self,
        timestamp: datetime,
        transcribed_text: str,
        metadata: dict
    ):
        """Save transcription as a single .md file with YAML frontmatter."""
        local_ts = self._to_local(timestamp)
        base_name = local_ts.strftime("%Y-%m-%d-%H-%M-%S")
        md_file = self.transcription_folder / f"{base_name}.md"

        frontmatter = yaml.dump(metadata, default_flow_style=False).strip()
        with open(md_file, "w") as f:
            f.write(f"---\n{frontmatter}\n---\n\n{transcribed_text}\n")

        logger.info(f"Transcription complete: {base_name}")

    def get_audio_file_path(self, filename: str) -> str:
        """Return full path to audio file."""
        return str(self.audio_folder / filename)
