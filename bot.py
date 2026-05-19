#!/usr/bin/env python3
import asyncio
import json
import logging
import time
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional
import yaml
import tiktoken
from setproctitle import setproctitle

from logger_config import setup_logger
from telegram_handler import TelegramHandler
from file_manager import FileManager

logger = None
tokenizer = None


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
    global logger, tokenizer

    setproctitle("telegram-voice-transcriber")

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

    logger = setup_logger(log_folder, log_level, log_name="bot")
    tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")

    if not config["telegram"]["bot_token"] or config["telegram"]["bot_token"] == "YOUR_BOT_TOKEN_HERE":
        logger.error("Bot token not configured. Please set it in config.yaml")
        sys.exit(1)

    try:
        telegram_handler = TelegramHandler(
            bot_token=config["telegram"]["bot_token"],
            allowed_user_ids=config["telegram"].get("allowed_user_ids", [])
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

    async def subprocess_transcribe(
        audio_path: str,
        model: str,
        language: str,
        max_attempts: int,
        initial_backoff: int,
        timeout_seconds: int
    ) -> Optional[str]:
        """Transcribe audio via subprocess, with exponential backoff retry."""
        backoff = initial_backoff

        for attempt in range(1, max_attempts + 1):
            try:
                proc = await asyncio.create_subprocess_exec(
                    "python3", "transcriber_worker.py",
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=Path(__file__).parent
                )

                request = json.dumps({
                    "audio_path": audio_path,
                    "model": model,
                    "language": language,
                    "max_attempts": max_attempts,
                    "initial_backoff_seconds": initial_backoff
                })

                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(request.encode()),
                    timeout=timeout_seconds
                )

                if proc.returncode == 0:
                    result = json.loads(stdout)
                    logger.debug(f"Subprocess transcription successful: {result.get('token_count', 0)} tokens")
                    return result["text"]
                else:
                    error_data = json.loads(stderr) if stderr else {}
                    error_msg = error_data.get("error", "Unknown error")
                    raise Exception(error_msg)

            except asyncio.TimeoutError:
                error_msg = f"Subprocess transcription timed out after {timeout_seconds} seconds"
                if attempt < max_attempts:
                    logger.warning(f"Transcription attempt {attempt}/{max_attempts} timed out")
                    await asyncio.sleep(backoff)
                    backoff *= 2
                else:
                    logger.error(error_msg)
                    return None
            except Exception as e:
                if attempt < max_attempts:
                    logger.warning(f"Transcription attempt {attempt}/{max_attempts} failed: {e}")
                    logger.debug(f"Retrying in {backoff} seconds...")
                    await asyncio.sleep(backoff)
                    backoff *= 2
                else:
                    logger.error(f"Transcription failed after {max_attempts} attempts: {e}")
                    return None

        return None

    async def run_bot():
        while True:
            try:
                updates = await telegram_handler.get_voice_updates()

                for update in updates:
                    sender = update.get("username") or update.get("first_name", "Unknown")
                    logger.info(f"Received voice from {sender} (ID: {update['user_id']}), duration: {update['duration']}s")

                    audio_data = await telegram_handler.download_voice_file(update["voice_file_id"])
                    if audio_data is None:
                        logger.warning(f"Failed to download voice file for {sender}")
                        continue

                    audio_filepath = file_manager.save_audio(
                        audio_data=audio_data,
                        timestamp=update["timestamp"],
                        sender_username=update["username"]
                    )
                    logger.debug(f"Audio saved: {audio_filepath}")

                    received_time = datetime.fromtimestamp(update["timestamp"].timestamp()).strftime("%H:%M")
                    duration_seconds = int(update["duration"])
                    if duration_seconds >= 60:
                        minutes = duration_seconds // 60
                        seconds = duration_seconds % 60
                        duration_str = f"{minutes}m{seconds}s"
                    else:
                        duration_str = f"{duration_seconds}s"

                    status_message_id = await telegram_handler.send_message(
                        user_id=update["user_id"],
                        text=f"📥 Audio received ({duration_str}, {received_time})\nStarting transcription...",
                        reply_to_message_id=update["message_id"]
                    )

                    if status_message_id:
                        await telegram_handler.edit_message(
                            user_id=update["user_id"],
                            message_id=status_message_id,
                            text=f"⏳ Transcribing... ({duration_str}, {received_time})"
                        )

                    logger.info(f"Starting transcription subprocess for {sender} ({duration_str})")
                    transcribed_text = await subprocess_transcribe(
                        audio_filepath,
                        model=config["whisper"]["model"],
                        language=config["whisper"]["language"],
                        max_attempts=config["retry"]["max_attempts"],
                        initial_backoff=config["retry"]["initial_backoff_seconds"],
                        timeout_seconds=config["whisper"]["timeout_seconds"]
                    )

                    if transcribed_text:
                        token_count = len(tokenizer.encode(transcribed_text))
                        logger.info(f"Transcription complete for {sender}: {token_count} tokens, {len(transcribed_text)} chars")

                        metadata = {
                            "sender_name": update["first_name"],
                            "sender_username": update["username"],
                            "sender_user_id": update["user_id"],
                            "telegram_timestamp": str(update["timestamp"]),
                            "audio_duration_seconds": update["duration"],
                            "transcription_timestamp": str(time.time()),
                            "token_count": token_count,
                        }
                        file_manager.save_transcription(
                            timestamp=update["timestamp"],
                            transcribed_text=transcribed_text,
                            metadata=metadata
                        )
                        logger.debug(f"Saved transcription file for {sender}")

                        if status_message_id:
                            await telegram_handler.edit_message(
                                user_id=update["user_id"],
                                message_id=status_message_id,
                                text=f"✅ Transcription complete ({duration_str}, {received_time})"
                            )
                    else:
                        logger.warning(f"No transcription for {Path(audio_filepath).name}")
                        if status_message_id:
                            await telegram_handler.edit_message(
                                user_id=update["user_id"],
                                message_id=status_message_id,
                                text=f"❌ Transcription failed ({duration_str}, {received_time})\nRetried {config['retry']['max_attempts']} times. Please try again."
                            )
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
