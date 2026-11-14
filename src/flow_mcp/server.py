#!/usr/bin/env python3
"""Google Flow MCP Server & OpenAPI Bridge.

Works in TWO ways:
1. ZERO API KEY (Default when GEMINI_API_KEY is not set):
   Uses your logged-in Google email & Google AI Ultra / Pro credits directly on
   `https://labs.google/fx/tools/flow` via a persistent Chrome browser profile!
2. GEMINI API ENGINE (Optional when GEMINI_API_KEY is set):
   Calls `gemini-omni-1.2-flash` and `gemini-nano-banana-2.1` directly via the SDK.
"""

from __future__ import annotations

import argparse
import os
from typing import Any, Dict, List, Optional

try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP  # type: ignore
from pydantic import BaseModel, Field

from flow_mcp.browser_engine import (
    generate_image_via_flow_browser,
    generate_video_via_flow_browser,
    login_and_verify_flow_session,
)
from flow_mcp.engine import (
    DEFAULT_DIRECTOR_MODEL,
    DEFAULT_IMAGE_MODEL,
    DEFAULT_VIDEO_MODEL,
    generate_flow_video,
    generate_frame_image,
    generate_storyboard_plan,
    get_api_key,
)

mcp = FastMCP(
    "google-flow",
    instructions=(
        "Google Flow AI Filmmaking & Creative Studio MCP Server. "
        "Supports BOTH zero-API-key browser mode (using the user's logged-in Google email and Google Flow "
        "subscription credits at labs.google/fx/tools/flow) AND optional Gemini API mode. "
        "If the user has not logged into the Flow browser profile yet, call `flow_browser_login` once."
    ),
)


def _has_real_api_key() -> bool:
    key = get_api_key()
    if not key:
        return False
    placeholders = {"your_gemini_api_key", "your_api_key_here", "none", ""}
    return key.strip().lower() not in placeholders


@mcp.tool()
def flow_browser_login(wait_seconds: int = 120) -> Dict[str, Any]:
    """Open Google Flow (`https://labs.google/fx/tools/flow`) in a visible Chrome window to sign in with your Google email and use your Flow subscription credits (NO API key required).

    Args:
        wait_seconds: Seconds to wait for you to sign in before returning status (default 120).
    """
    return login_and_verify_flow_session(wait_seconds=wait_seconds)


@mcp.tool()
def flow_text_to_video(
    prompt: str,
    aspect_ratio: str = "16:9",
    duration: int = 10,
    resolution: str = "720p",
    output_path: Optional[str] = None,
    use_browser_credits: bool = True,
) -> Dict[str, Any]:
    """Generate a video from a text prompt using Google Flow.
    By default (`use_browser_credits=True` or when no API key is set), uses your logged-in Google Flow email and subscription credits at `labs.google/fx/tools/flow`.

    Args:
        prompt: Detailed scene, camera motion, lighting, and sound design prompt.
        aspect_ratio: '16:9' (landscape) or '9:16' (vertical/reels). Default '16:9'.
        duration: Video length in seconds (3 to 15, default 10).
        resolution: Output resolution ('360p', '720p', '1080p', '4k'). Default '720p'.
        output_path: Optional local file path to save the generated MP4.
        use_browser_credits: If True (default), uses your logged-in Google Flow web session & credits without needing an API key.
    """
    if use_browser_credits or not _has_real_api_key():
        return generate_video_via_flow_browser(
            prompt=prompt,
            mode="text_to_video",
            aspect_ratio=aspect_ratio,
            duration=duration,
            output_path=output_path,
        )
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
    use_browser_credits: bool = True,
) -> Dict[str, Any]:
    """Animate a starting image frame or interpolate smoothly between a starting frame and an ending frame in Google Flow.

    Args:
        prompt: Description of the camera motion, action, transition, and sound design.
        first_frame: Local file path for the starting frame.
        last_frame: Optional local file path for the ending frame.
        aspect_ratio: '16:9' or '9:16'. Default '16:9'.
        duration: Duration in seconds (default 10).
        resolution: '360p', '720p', '1080p', or '4k'. Default '720p'.
        output_path: Optional local file path to save the generated MP4.
        use_browser_credits: If True (default), uses your logged-in Google Flow web session & credits without needing an API key.
    """
    if use_browser_credits or not _has_real_api_key():
        return generate_video_via_flow_browser(
            prompt=prompt,
            mode="frames_to_video",
            first_frame=first_frame,
            last_frame=last_frame,
            aspect_ratio=aspect_ratio,
            duration=duration,
            output_path=output_path,
        )
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
    use_browser_credits: bool = True,
) -> Dict[str, Any]:
    """Generate a new video guided by reference images (product, character, style) in Google Flow (Ingredients to Video).

    Args:
        prompt: Natural-language prompt describing how the reference images should be combined in the scene.
        reference_images: List of local image paths to use as ingredients/references.
        reference_videos: Optional reference video paths (API mode).
        aspect_ratio: '16:9' or '9:16'. Default '16:9'.
        duration: Duration in seconds (default 10).
        resolution: '360p', '720p', '1080p', or '4k'. Default '720p'.
        output_path: Optional local file path to save the generated MP4.
        use_browser_credits: If True (default), uses your logged-in Google Flow web session & credits.
    """
    if use_browser_credits or not _has_real_api_key():
        return generate_video_via_flow_browser(
            prompt=prompt,
            mode="reference_to_video",
            reference_images=reference_images,
            aspect_ratio=aspect_ratio,
            duration=duration,
            output_path=output_path,
        )
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
def flow_generate_frame(
    prompt: str,
    reference_images: Optional[List[str]] = None,
    aspect_ratio: str = "16:9",
    image_size: str = "2K",
    model: str = DEFAULT_IMAGE_MODEL,
    previous_interaction_id: Optional[str] = None,
    output_path: Optional[str] = None,
    use_browser_credits: bool = True,
) -> Dict[str, Any]:
    """Generate an image (starting frame, keyframe, product shot) with Nano Banana.

    By default (`use_browser_credits=True`, or when no API key is set) it uses your signed-in
    Google Flow account and credits, no API key needed. In that mode Flow picks the size, and
    `image_size`, `model` and `previous_interaction_id` are ignored.

    Args:
        prompt: Detailed visual description of the frame or edit instruction.
        reference_images: Optional list of up to 14 local image paths to fuse.
        aspect_ratio: Aspect ratio ('16:9', '9:16', '1:1'). Default '16:9'.
        image_size: Output resolution ('1K', '2K', '4K'). Default '2K'.
        model: Gemini image model ('gemini-nano-banana-2.1' or 'gemini-3-pro-image').
        previous_interaction_id: Optional interaction ID from a prior turn.
        output_path: Optional custom local file path for saving the image.
        use_browser_credits: If True (default), uses your Google Flow sign-in and credits instead of the Gemini API.
    """
    if use_browser_credits or not _has_real_api_key():
        return generate_image_via_flow_browser(
            prompt=prompt,
            aspect_ratio=aspect_ratio,
            reference_images=reference_images,
            output_path=output_path,
        )
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
    """Extend a video scene (by 3s-10s, up to 30s cumulative) or edit an existing video's style, lighting, or objects."""
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
    """AI Creative Director that turns a brief or product photo into structured Google Flow frame + video prompts."""
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

class FrameRequest(BaseModel):
    prompt: str = Field(..., description="Visual description of the frame to generate or edit.")
    reference_images: Optional[List[str]] = Field(None, description="Optional list of local paths or Gemini File URIs.")
    aspect_ratio: str = Field("16:9", description="Aspect ratio (16:9, 9:16, 1:1).")
    image_size: str = Field("2K", description="Resolution size (1K, 2K, 4K).")
    previous_interaction_id: Optional[str] = Field(None, description="Previous interaction ID for multi-turn edits.")
    use_browser_credits: bool = Field(True, description="Use logged-in Google Flow web session & credits (no API key required).")


class TextToVideoRequest(BaseModel):
    prompt: str = Field(..., description="Scene, camera movement, and sound design prompt.")
    aspect_ratio: str = Field("16:9", description="16:9 or 9:16.")
    duration: int = Field(10, ge=3, le=15, description="Duration in seconds (3-15).")
    resolution: str = Field("720p", description="360p, 720p, 1080p, or 4k.")
    use_browser_credits: bool = Field(True, description="Use logged-in Google Flow web session & credits (no API key required).")


class FramesToVideoRequest(BaseModel):
    prompt: str = Field(..., description="Camera motion and transition prompt.")
    first_frame: str = Field(..., description="Path for starting frame.")
    last_frame: Optional[str] = Field(None, description="Optional path for ending frame.")
    aspect_ratio: str = Field("16:9", description="16:9 or 9:16.")
    duration: int = Field(10, ge=3, le=15, description="Duration in seconds.")
    resolution: str = Field("720p", description="360p, 720p, 1080p, or 4k.")
    use_browser_credits: bool = Field(True, description="Use logged-in Google Flow web session & credits (no API key required).")


class StoryboardRequest(BaseModel):
    concept: str = Field(..., description="Campaign idea or creative brief.")
    num_shots: int = Field(3, ge=1, le=10, description="Number of storyboard shots.")
    aspect_ratio: str = Field("16:9", description="Target aspect ratio.")


def create_openapi_app():
    """Builds a FastAPI application exposing all Flow tools as REST endpoints for ChatGPT Actions."""
    from fastapi import FastAPI, HTTPException

    app = FastAPI(
        title="Google Flow Studio API (ChatGPT & Claude Bridge)",
        version="0.2.0",
        description=(
            "OpenAPI bridge for ChatGPT Custom GPT Actions and REST clients to trigger "
            "Google Flow video generation using your logged-in Google Flow browser credits (no API key required) or Gemini API."
        ),
    )

    @app.post("/flow/browser-login", operation_id="flowBrowserLogin")
    def api_browser_login():
        try:
            return flow_browser_login(wait_seconds=120)
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/flow/generate-frame", operation_id="flowGenerateFrame")
    def api_generate_frame(req: FrameRequest):
        try:
            return flow_generate_frame(
                prompt=req.prompt,
                reference_images=req.reference_images,
                aspect_ratio=req.aspect_ratio,
                image_size=req.image_size,
                previous_interaction_id=req.previous_interaction_id,
                use_browser_credits=req.use_browser_credits,
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
                use_browser_credits=req.use_browser_credits,
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
                use_browser_credits=req.use_browser_credits,
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
        if hasattr(mcp, "settings"):
            mcp.settings.host = args.host
            mcp.settings.port = args.port
            mcp.run(transport=args.transport)
        else:
            mcp.run(transport=args.transport, host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
