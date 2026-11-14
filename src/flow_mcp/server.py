#!/usr/bin/env python3
"""Google Flow MCP Server & OpenAPI Bridge.

Supports:
1. Claude Desktop / Claude Code / Antigravity (`stdio` transport)
2. ChatGPT MCP Connectors (`sse` / `streamable-http` transport)
3. ChatGPT Custom GPT Actions (`openapi` FastAPI REST server with `/openapi.json`)
"""

from __future__ import annotations

import argparse
import os
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from flow_mcp.engine import (
    DEFAULT_DIRECTOR_MODEL,
    DEFAULT_IMAGE_MODEL,
    DEFAULT_VIDEO_MODEL,
    generate_flow_video,
    generate_frame_image,
    generate_storyboard_plan,
)

mcp = FastMCP(
    "google-flow-mcp",
    instructions=(
        "Google Flow AI Filmmaking & Creative Studio MCP Server. "
        "Use `flow_storyboard_director` to plan shots, `flow_generate_frame` (Nano Banana 2.1 / Whisk fusion) "
        "to generate or fuse reference frames, and `flow_text_to_video`, `flow_frames_to_video`, "
        "`flow_reference_to_video`, or `flow_extend_or_edit_video` (Gemini Omni 1.2 Flash) to produce video."
    ),
)


@mcp.tool()
def flow_generate_frame(
    prompt: str,
    reference_images: Optional[List[str]] = None,
    aspect_ratio: str = "16:9",
    image_size: str = "2K",
    model: str = DEFAULT_IMAGE_MODEL,
    previous_interaction_id: Optional[str] = None,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a starting frame, ending keyframe, or Whisk-style reference fusion image.

    Args:
        prompt: Detailed visual description of the frame or edit instruction.
        reference_images: Optional list of up to 14 local image paths or Gemini File URIs to fuse (product, style, character, lighting).
        aspect_ratio: Aspect ratio ('16:9', '9:16', '1:1', '4:3', '3:4'). Default '16:9'.
        image_size: Output resolution ('1K', '2K', '4K'). Default '2K'.
        model: Gemini image model ('gemini-nano-banana-2.1', 'gemini-3-pro-image', or 'gemini-3.1-flash-lite-image').
        previous_interaction_id: Optional interaction ID from a prior turn for conversational editing.
        output_path: Optional custom local file path for saving the PNG image.
    """
    return generate_frame_image(
        prompt=prompt,
        reference_images=reference_images,
        aspect_ratio=aspect_ratio,
        image_size=image_size,
        model=model,
        previous_interaction_id=previous_interaction_id,
        output_path=output_path,
    )


@mcp.tool()
def flow_text_to_video(
    prompt: str,
    aspect_ratio: str = "16:9",
    duration: int = 10,
    resolution: str = "720p",
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a commercial or cinematic video from a text prompt using Google Flow (Gemini Omni 1.2 Flash).

    Args:
        prompt: Detailed scene, camera motion, lighting, and sound design prompt. Use '[0-5s] ... [5-10s] ...' for timed shots, or 'In a single continuous shot' for unbroken camera movement.
        aspect_ratio: '16:9' (landscape) or '9:16' (vertical/reels). Default '16:9'.
        duration: Video length in seconds (integer from 3 to 15, default 10).
        resolution: Output resolution ('360p', '720p', '1080p', '4k'). Default '720p'.
        output_path: Optional local file path to save the generated MP4.
    """
    return generate_flow_video(
        prompt=prompt,
        aspect_ratio=aspect_ratio,
        duration=duration,
        resolution=resolution,
        output_path=output_path,
    )


@mcp.tool()
def flow_frames_to_video(
    prompt: str,
    first_frame: str,
    last_frame: Optional[str] = None,
    aspect_ratio: str = "16:9",
    duration: int = 10,
    resolution: str = "720p",
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Animate a starting image frame or interpolate smoothly between a starting frame and an ending frame.

    Args:
        prompt: Description of the camera motion, action, transition, and sound design.
        first_frame: Local file path or Gemini File URI for the starting frame.
        last_frame: Optional local file path or Gemini File URI for the ending frame (pass the same path as first_frame for a seamless loop).
        aspect_ratio: '16:9' or '9:16'. Default '16:9'.
        duration: Duration in seconds (3 to 15s for first-frame only; 3 to 10s when both first_frame and last_frame are provided).
        resolution: '360p', '720p', '1080p', or '4k'. Default '720p'.
        output_path: Optional local file path to save the generated MP4.
    """
    return generate_flow_video(
        prompt=prompt,
        first_frame=first_frame,
        last_frame=last_frame,
        aspect_ratio=aspect_ratio,
        duration=duration,
        resolution=resolution,
        output_path=output_path,
    )


@mcp.tool()
def flow_reference_to_video(
    prompt: str,
    reference_images: Optional[List[str]] = None,
    reference_videos: Optional[List[str]] = None,
    aspect_ratio: str = "16:9",
    duration: int = 10,
    resolution: str = "720p",
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate a new video guided by reference images (product, character, style) and/or reference motion videos (Flow Ingredients / R2V).

    Args:
        prompt: Natural-language prompt describing how the reference images/videos should be combined in the scene.
        reference_images: Up to 6 local image paths or Gemini File URIs.
        reference_videos: Up to 3 reference video paths (~3s clips) for 3s-10s outputs, or max 1 for 11s-15s outputs.
        aspect_ratio: '16:9' or '9:16'. Default '16:9'.
        duration: Duration in seconds (3 to 15, default 10).
        resolution: '360p', '720p', '1080p', or '4k'. Default '720p'.
        output_path: Optional local file path to save the generated MP4.
    """
    return generate_flow_video(
        prompt=prompt,
        reference_images=reference_images,
        reference_videos=reference_videos,
        aspect_ratio=aspect_ratio,
        duration=duration,
        resolution=resolution,
        output_path=output_path,
    )


@mcp.tool()
def flow_extend_or_edit_video(
    prompt: str,
    mode: str = "extend",
    source_video: Optional[str] = None,
    previous_interaction_id: Optional[str] = None,
    reference_images: Optional[List[str]] = None,
    duration: int = 10,
    aspect_ratio: str = "16:9",
    resolution: str = "720p",
    strip_audio: bool = False,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Extend a video scene (by 3s-10s, up to 30s cumulative) or edit an existing video's style, lighting, or objects.

    Args:
        prompt: For 'extend', describe how the action and audio continue. For 'edit', state the change simply and end with 'Keep everything else the same.'
        mode: 'extend' (continue the scene) or 'edit' (modify existing video).
        source_video: Local video path or Gemini File URI to extend or edit (optional if previous_interaction_id is used).
        previous_interaction_id: Optional interaction ID from a previous generation for turn-by-turn editing or extension without re-uploading.
        reference_images: Optional list of up to 6 reference images to introduce into the extended or edited scene.
        duration: Duration in seconds (3 to 10s for extensions; 3 to 15s for edits).
        aspect_ratio: '16:9' or '9:16'.
        resolution: '360p', '720p', '1080p', or '4k'.
        strip_audio: Set True when editing if you want Gemini Omni Flash to regenerate all audio from scratch instead of keeping original audio.
        output_path: Optional local file path to save the resulting MP4.
    """
    clean_mode = mode.strip().lower()
    if clean_mode not in {"extend", "edit"}:
        raise ValueError("mode must be 'extend' or 'edit'.")

    return generate_flow_video(
        prompt=prompt,
        extend_video=source_video if clean_mode == "extend" else None,
        edit_video=source_video if clean_mode == "edit" else None,
        previous_interaction_id=previous_interaction_id,
        reference_images=reference_images,
        duration=duration,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        strip_audio=strip_audio,
        output_path=output_path,
    )


@mcp.tool()
def flow_storyboard_director(
    concept: str,
    num_shots: int = 3,
    reference_images: Optional[List[str]] = None,
    aspect_ratio: str = "16:9",
    model: str = DEFAULT_DIRECTOR_MODEL,
) -> Dict[str, Any]:
    """AI Creative Director that turns a brief or product photo into structured Google Flow frame + video prompts.

    Args:
        concept: Brand campaign concept, product description, or creative brief.
        num_shots: Number of shots to plan in the storyboard (default 3).
        reference_images: Optional product or moodboard image paths to analyze.
        aspect_ratio: Target aspect ratio ('16:9' or '9:16').
        model: Reasoning model to use (default 'gemini-4-hydrogen').
    """
    return generate_storyboard_plan(
        concept=concept,
        num_shots=num_shots,
        reference_images=reference_images,
        aspect_ratio=aspect_ratio,
        model=model,
    )


# ---------------------------------------------------------------------------
# FastAPI OpenAPI Server for ChatGPT Custom GPT Actions
# ---------------------------------------------------------------------------

def create_openapi_app():
    """Builds a FastAPI application exposing all Flow tools as REST endpoints for ChatGPT Actions."""
    from fastapi import FastAPI, HTTPException

    app = FastAPI(
        title="Google Flow Studio API (ChatGPT & Claude Bridge)",
        version="0.1.0",
        description=(
            "OpenAPI bridge for ChatGPT Custom GPT Actions and REST clients to trigger "
            "Google Flow video generation (Gemini Omni 1.2 Flash) and image frame fusion (Nano Banana 2.1)."
        ),
    )

    class FrameRequest(BaseModel):
        prompt: str = Field(..., description="Visual description of the frame to generate or edit.")
        reference_images: Optional[List[str]] = Field(None, description="Optional list of local paths or Gemini File URIs.")
        aspect_ratio: str = Field("16:9", description="Aspect ratio (16:9, 9:16, 1:1).")
        image_size: str = Field("2K", description="Resolution size (1K, 2K, 4K).")
        previous_interaction_id: Optional[str] = Field(None, description="Previous interaction ID for multi-turn edits.")

    class TextToVideoRequest(BaseModel):
        prompt: str = Field(..., description="Scene, camera movement, and sound design prompt.")
        aspect_ratio: str = Field("16:9", description="16:9 or 9:16.")
        duration: int = Field(10, ge=3, le=15, description="Duration in seconds (3-15).")
        resolution: str = Field("720p", description="360p, 720p, 1080p, or 4k.")

    class FramesToVideoRequest(BaseModel):
        prompt: str = Field(..., description="Camera motion and transition prompt.")
        first_frame: str = Field(..., description="Path or File URI for starting frame.")
        last_frame: Optional[str] = Field(None, description="Optional path or File URI for ending frame (3-10s max).")
        aspect_ratio: str = Field("16:9", description="16:9 or 9:16.")
        duration: int = Field(10, ge=3, le=15, description="Duration in seconds.")
        resolution: str = Field("720p", description="360p, 720p, 1080p, or 4k.")

    class StoryboardRequest(BaseModel):
        concept: str = Field(..., description="Campaign idea or creative brief.")
        num_shots: int = Field(3, ge=1, le=10, description="Number of storyboard shots.")
        aspect_ratio: str = Field("16:9", description="Target aspect ratio.")

    @app.post("/flow/generate-frame", operation_id="flowGenerateFrame")
    def api_generate_frame(req: FrameRequest):
        try:
            return flow_generate_frame(
                prompt=req.prompt,
                reference_images=req.reference_images,
                aspect_ratio=req.aspect_ratio,
                image_size=req.image_size,
                previous_interaction_id=req.previous_interaction_id,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/flow/text-to-video", operation_id="flowTextToVideo")
    def api_text_to_video(req: TextToVideoRequest):
        try:
            return flow_text_to_video(
                prompt=req.prompt,
                aspect_ratio=req.aspect_ratio,
                duration=req.duration,
                resolution=req.resolution,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/flow/frames-to-video", operation_id="flowFramesToVideo")
    def api_frames_to_video(req: FramesToVideoRequest):
        try:
            return flow_frames_to_video(
                prompt=req.prompt,
                first_frame=req.first_frame,
                last_frame=req.last_frame,
                aspect_ratio=req.aspect_ratio,
                duration=req.duration,
                resolution=req.resolution,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/flow/storyboard", operation_id="flowStoryboardDirector")
    def api_storyboard(req: StoryboardRequest):
        try:
            return flow_storyboard_director(
                concept=req.concept,
                num_shots=req.num_shots,
                aspect_ratio=req.aspect_ratio,
            )
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    return app


def main():
    parser = argparse.ArgumentParser(
        description="Run the Google Flow MCP Server (stdio, sse, streamable-http, or openapi)."
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http", "openapi"],
        default="stdio",
        help="Transport protocol: 'stdio' (Claude Desktop/Code), 'sse' or 'streamable-http' (ChatGPT MCP), or 'openapi' (ChatGPT Custom GPT Actions).",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("FLOW_HOST", "127.0.0.1"),
        help="Host for HTTP/SSE/OpenAPI modes (default: 127.0.0.1).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("FLOW_PORT", "8000")),
        help="Port for HTTP/SSE/OpenAPI modes (default: 8000).",
    )
    args = parser.parse_args()

    if args.transport == "openapi":
        import uvicorn

        app = create_openapi_app()
        uvicorn.run(app, host=args.host, port=args.port)
    elif args.transport in ("sse", "streamable-http"):
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport=args.transport)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
