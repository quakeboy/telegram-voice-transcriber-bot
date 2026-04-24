#!/usr/bin/env python3
import asyncio
import logging
import time
import signal
import sys
from pathlib import Path
import yaml

from logger_config import setup_logger
from telegram_handler import TelegramHandler
from transcriber import Transcriber
from file_manager import FileManager

logger = None


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def validate_config(config: dict) -> bool:
    """Validate required config fields."""
    required = ["telegram.bot_token", "telegram.polling_interval_seconds"]
    for field in required:
        parts = field.split(".")
        val = config
        for part in parts:
            val = val.get(part)
            if val is None:
                logger.error(f"Missing required config field: {field}")
                return False
    return True


def main():
    global logger

    try:
        config = load_config()
    except FileNotFoundError:
        print("Error: config.yaml not found. Please create it from the template.")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing config.yaml: {e}")
        sys.exit(1)

    if not validate_config(config):
        sys.exit(1)

    workspace = config["paths"]["workspace"]
    log_folder = str(Path(workspace) / "logs")
    log_level = config["logging"]["level"]

    logger = setup_logger(log_folder, log_level)

    if not config["telegram"]["bot_token"] or config["telegram"]["bot_token"] == "YOUR_BOT_TOKEN_HERE":
        logger.error("Bot token not configured. Please set it in config.yaml")
        sys.exit(1)

    try:
        telegram_handler = TelegramHandler(
            bot_token=config["telegram"]["bot_token"],
            allowed_user_ids=config["telegram"].get("allowed_user_ids", [])
        )
        transcriber = Transcriber(
            model_name=config["whisper"]["model"],
            language=config["whisper"]["language"],
            max_attempts=config["retry"]["max_attempts"],
            initial_backoff=config["retry"]["initial_backoff_seconds"],
            timeout_seconds=config["whisper"]["timeout_seconds"]
        )
        file_manager = FileManager(
            workspace=workspace,
            max_audio_files=config["audio"]["max_files"],
            verbose_cleanup=config["logging"]["verbose_cleanup"],
            timezone_offset_hours=config["paths"].get("timezone_offset_hours", 0)
        )
    except Exception as e:
        logger.error(f"Failed to initialize components: {e}")
        sys.exit(1)

    polling_interval = config["telegram"]["polling_interval_seconds"]
    logger.info(f"Bot started, polling every {polling_interval} seconds...")

    async def run_bot():
        while True:
            try:
                updates = await telegram_handler.get_voice_updates()

                for update in updates:
                    audio_data = await telegram_handler.download_voice_file(update["voice_file_id"])
                    if audio_data is None:
                        continue

                    audio_filepath = file_manager.save_audio(
                        audio_data=audio_data,
                        timestamp=update["timestamp"],
                        sender_username=update["username"]
                    )

                    transcribed_text = transcriber.transcribe_with_retry(audio_filepath)

                    if transcribed_text:
                        metadata = {
                            "sender_name": update["first_name"],
                            "sender_username": update["username"],
                            "sender_user_id": update["user_id"],
                            "telegram_timestamp": str(update["timestamp"]),
                            "audio_duration_seconds": update["duration"],
                            "transcription_timestamp": str(time.time()),
                        }
                        file_manager.save_transcription(
                            timestamp=update["timestamp"],
                            transcribed_text=transcribed_text,
                            metadata=metadata
                        )
                    else:
                        logger.warning(f"No transcription for {Path(audio_filepath).name}")
                        if config["audio"]["delete_failed_audio"]:
                            Path(audio_filepath).unlink()
                            logger.info(f"Deleted failed audio file: {Path(audio_filepath).name}")

                await asyncio.sleep(polling_interval)

            except asyncio.CancelledError:
                logger.info("Bot shutting down...")
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
                await asyncio.sleep(polling_interval)

    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Bot interrupted by user")


if __name__ == "__main__":
    main()
