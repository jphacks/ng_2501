from __future__ import annotations

from pathlib import Path

from .pipeline import FastAIPipeline, PipelineConfig


class FastAIAgentService:
    """Wrapper that exposes the fast AI pipeline with a service-like interface."""

    def __init__(
        self,
        *,
        translator_model: str | None = "gemini-2.5-flash-lite",
        generator_model: str = "gemini-2.5-pro",
        patch_model: str = "gemini-2.5-flash",
        max_patch_attempts: int = 3,
    ) -> None:
        base_dir = Path(__file__).resolve().parent
        config = PipelineConfig(
            translator_model=translator_model,
            generator_model=generator_model,
            patch_model=patch_model,
            max_patch_attempts=max_patch_attempts,
        )
        self.pipeline = FastAIPipeline(base_dir, config=config)

    def generate_videos(self, video_id: str, content: str, enhance_prompt: str) -> str:
        return self.pipeline.generate_video(video_id, content, enhance_prompt)
