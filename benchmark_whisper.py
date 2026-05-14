#!/usr/bin/env python3
"""
Benchmark openai-whisper vs mlx-whisper on a synthetic ~5-min audio file.

Usage:
    python3 benchmark_whisper.py [--audio path/to/file.wav]

Without --audio, generates a sample using macOS `say`.
"""

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

MODEL = "small"
MLX_REPO = "mlx-community/whisper-small-mlx"

# ~650 words → ~5 min at 130 wpm
SAMPLE_TEXT = (
    "Artificial intelligence is reshaping the way we interact with technology. "
    "From voice assistants that understand natural language to systems that can "
    "diagnose diseases from medical images, the applications are vast and growing. "
    "Machine learning models are trained on enormous datasets, allowing them to "
    "recognise patterns that would be invisible to the human eye. Deep neural "
    "networks, inspired loosely by the structure of the brain, have proven "
    "especially powerful for tasks involving images, audio, and text. "
    "The field advances rapidly, with new architectures and training techniques "
    "published every month. Researchers debate how far these systems can go and "
    "what their long-term impact on society will be. Some see a future of "
    "abundance where intelligent tools handle routine work, freeing humans to "
    "focus on creativity and connection. Others raise concerns about job "
    "displacement, privacy, and the concentration of power in the hands of a "
    "few large organisations. Navigating these trade-offs thoughtfully is one "
    "of the defining challenges of our era. Open research, diverse teams, and "
    "strong governance frameworks all have a role to play in ensuring these "
    "powerful tools benefit everyone. "
) * 5  # repeat 5× to reach ~5 minutes


def generate_audio(output_wav: Path) -> None:
    output_aiff = output_wav.with_suffix(".aiff")

    if output_wav.exists():
        print(f"[audio] Reusing existing {output_wav}")
        return

    print("[audio] Generating ~5-min sample with macOS `say` ...")
    subprocess.run(
        ["say", "-o", str(output_aiff), SAMPLE_TEXT],
        check=True,
    )

    if shutil.which("ffmpeg"):
        print("[audio] Converting AIFF → WAV with ffmpeg ...")
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(output_aiff), str(output_wav)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        output_aiff.unlink(missing_ok=True)
    else:
        print("[audio] ffmpeg not found — using AIFF directly (renaming to .wav)")
        output_aiff.rename(output_wav)


def bench_openai(audio: str) -> dict:
    print("\n[openai-whisper] Loading model ...")
    t_load = time.perf_counter()
    import whisper
    model = whisper.load_model(MODEL)
    load_time = time.perf_counter() - t_load

    print("[openai-whisper] Transcribing ...")
    t_transcribe = time.perf_counter()
    result = model.transcribe(audio, language="en", fp16=False)
    transcribe_time = time.perf_counter() - t_transcribe

    text = result["text"].strip()
    return {
        "backend": "openai-whisper",
        "load_s": load_time,
        "transcribe_s": transcribe_time,
        "total_s": load_time + transcribe_time,
        "words": len(text.split()),
        "preview": text[:80],
    }


def bench_mlx(audio: str) -> dict:
    try:
        import mlx_whisper  # noqa: F401
    except ImportError:
        print(
            "\n[mlx-whisper] Not installed. Run:\n"
            "    pip install mlx-whisper\n"
            "then re-run this script."
        )
        sys.exit(1)

    print("\n[mlx-whisper] Loading model + transcribing (lazy load) ...")
    # mlx_whisper loads the model on the first transcribe call, so we time the whole thing
    t_start = time.perf_counter()
    result = mlx_whisper.transcribe(audio, path_or_hf_repo=MLX_REPO, language="en")
    total_time = time.perf_counter() - t_start

    text = result["text"].strip()
    return {
        "backend": "mlx-whisper",
        "load_s": None,  # not separable
        "transcribe_s": None,
        "total_s": total_time,
        "words": len(text.split()),
        "preview": text[:80],
    }


def print_report(results: list[dict]) -> None:
    print("\n" + "=" * 72)
    print(f"{'Backend':<18} {'Load (s)':>10} {'Transcribe (s)':>16} {'Total (s)':>10} {'Words':>7}")
    print("-" * 72)
    for r in results:
        load = f"{r['load_s']:.1f}" if r["load_s"] is not None else "  (combined)"
        transcribe = f"{r['transcribe_s']:.1f}" if r["transcribe_s"] is not None else "  (combined)"
        print(f"{r['backend']:<18} {load:>10} {transcribe:>16} {r['total_s']:>10.1f} {r['words']:>7}")
    print("=" * 72)

    if len(results) == 2:
        speedup = results[0]["total_s"] / results[1]["total_s"]
        faster = results[1]["backend"] if speedup > 1 else results[0]["backend"]
        ratio = max(speedup, 1 / speedup)
        print(f"\nResult: {faster} is {ratio:.1f}x faster (total wall-clock)\n")

    for r in results:
        print(f"[{r['backend']}] preview: \"{r['preview']}\"")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", help="Path to an existing audio file to use instead of generating one")
    args = parser.parse_args()

    if args.audio:
        audio_path = args.audio
    else:
        wav = Path("sample_benchmark.wav")
        generate_audio(wav)
        audio_path = str(wav)

    results = []
    results.append(bench_openai(audio_path))
    results.append(bench_mlx(audio_path))
    print_report(results)


def bench_mlx_only(audio_path: str) -> None:
    result = bench_mlx(audio_path)
    print(f"\nmlx-whisper total (cached model): {result['total_s']:.1f}s | words: {result['words']}")
    print(f"preview: \"{result['preview']}\"")


if __name__ == "__main__":
    main()
