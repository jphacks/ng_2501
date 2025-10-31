from __future__ import annotations

import argparse
from pathlib import Path

try:
    from .pipeline import FastAIPipeline, PipelineConfig
except ImportError:
    import sys
    from pathlib import Path as _Path

    sys.path.append(str(_Path(__file__).resolve().parent.parent))
    from fast_ai_agent.pipeline import FastAIPipeline, PipelineConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Manim animation code via Gemini pipeline")
    parser.add_argument("--topic", required=True, help="Primary (Japanese) request for the animation")
    parser.add_argument("--video-id", default="preview", help="Temporary video id used for output script name")
    parser.add_argument("--enhance-prompt", default="", help="Additional instruction appended to the request")
    parser.add_argument("--env-file", default=None, help="Optional path to .env that defines GEMINI_API_KEY")
    parser.add_argument("--translator-model", default="gemini-2.5-flash-lite")
    parser.add_argument("--generator-model", default="gemini-2.5-pro")
    parser.add_argument("--patch-model", default="gemini-2.5-flash")
    parser.add_argument("--max-patch-attempts", type=int, default=3)
    parser.add_argument("--resolution", default="640x360")
    parser.add_argument("--fps", type=int, default=24)
    parser.add_argument("--quality", default="l", choices=("l", "m", "h", "k"))
    parser.add_argument("--no-translate", action="store_true", help="Skip Japanese -> English translation stage")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    translator_model = None if args.no_translate else args.translator_model
    config = PipelineConfig(
        translator_model=translator_model,
        generator_model=args.generator_model,
        patch_model=args.patch_model,
        max_patch_attempts=args.max_patch_attempts,
        resolution=args.resolution,
        fps=args.fps,
        quality=args.quality,
    )
    base_dir = Path(__file__).resolve().parent
    pipeline = FastAIPipeline(base_dir, env_path=args.env_file, config=config)
    status = pipeline.generate_video(args.video_id, args.topic, args.enhance_prompt)
    print(status)


if __name__ == "__main__":
    main()
