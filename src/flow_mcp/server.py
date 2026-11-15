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
    get_media_dir,
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


_MAX_INLINE_IMAGE_BYTES = 3 * 1024 * 1024
IMAGE_WIDGET_URI = "ui://widget/flow-image.html"  # ChatGPT widget that shows images and videos


def _public_file_url(path: Optional[str]) -> Optional[str]:
    """Download link for a saved file, when running in ChatGPT mode (served on the secret tunnel path)."""
    base = os.environ.get("FLOW_PUBLIC_FILES_BASE")
    if not base or not path or not os.path.isfile(path):
        return None
    from urllib.parse import quote

    media_dir = os.path.realpath(get_media_dir())
    if os.path.dirname(os.path.realpath(path)) != media_dir:
        return None
    return f"{base}/{quote(os.path.basename(path))}"


def _with_media(result: Dict[str, Any], show_image: bool = False) -> Any:
    """Add a download link and, for images, return the picture itself so ChatGPT/Claude can show it."""
    path = result.get("output_path")
    url = _public_file_url(path)
    if url:
        result["download_url"] = url
        if show_image:
            result["markdown"] = f"![Generated image]({url})"
    if not (show_image and path and os.path.isfile(path)):
        return result
    if os.path.getsize(path) > _MAX_INLINE_IMAGE_BYTES:
        return result
    import json

    from mcp.types import CallToolResult, TextContent

    try:
        from mcp.server.mcpserver import Image
    except ImportError:  # older MCP SDK
        from mcp.server.fastmcp import Image  # type: ignore

    content = [
        TextContent(type="text", text=json.dumps(result, indent=2)),
        Image(path=path).to_image_content(),
    ]
    return CallToolResult(content=content, structured_content={"result": result})


@mcp.tool()
def flow_browser_login(wait_seconds: int = 120) -> Dict[str, Any]:
    """Open Google Flow (`https://labs.google/fx/tools/flow`) in a visible Chrome window to sign in with your Google email and use your Flow subscription credits (NO API key required).

    Args:
        wait_seconds: Seconds to wait for you to sign in before returning status (default 120).
    """
    return login_and_verify_flow_session(wait_seconds=wait_seconds)


@mcp.tool(
    meta={
        "openai/outputTemplate": IMAGE_WIDGET_URI,
        "openai/toolInvocation/invoking": "Generating video in Google Flow...",
        "openai/toolInvocation/invoked": "Video ready",
    }
)
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
        return _with_media(generate_video_via_flow_browser(
            prompt=prompt,
            mode="text_to_video",
            aspect_ratio=aspect_ratio,
            duration=duration,
            output_path=output_path,
        ))
    return generate_flow_video(
        prompt=prompt,
        aspect_ratio=aspect_ratio,
        duration=duration,
        resolution=resolution,
        output_path=output_path,
    )


@mcp.tool(
    meta={
        "openai/outputTemplate": IMAGE_WIDGET_URI,
        "openai/toolInvocation/invoking": "Generating video in Google Flow...",
        "openai/toolInvocation/invoked": "Video ready",
    }
)
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
        return _with_media(generate_video_via_flow_browser(
            prompt=prompt,
            mode="frames_to_video",
            first_frame=first_frame,
            last_frame=last_frame,
            aspect_ratio=aspect_ratio,
            duration=duration,
            output_path=output_path,
        ))
    return generate_flow_video(
        prompt=prompt,
        first_frame=first_frame,
        last_frame=last_frame,
        aspect_ratio=aspect_ratio,
        duration=duration,
        resolution=resolution,
        output_path=output_path,
    )


@mcp.tool(
    meta={
        "openai/outputTemplate": IMAGE_WIDGET_URI,
        "openai/toolInvocation/invoking": "Generating video in Google Flow...",
        "openai/toolInvocation/invoked": "Video ready",
    }
)
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
        return _with_media(generate_video_via_flow_browser(
            prompt=prompt,
            mode="reference_to_video",
            reference_images=reference_images,
            aspect_ratio=aspect_ratio,
            duration=duration,
            output_path=output_path,
        ))
    return generate_flow_video(
        prompt=prompt,
        reference_images=reference_images,
        reference_videos=reference_videos,
        aspect_ratio=aspect_ratio,
        duration=duration,
        resolution=resolution,
        output_path=output_path,
    )



# Small display widget so ChatGPT shows the generated picture inside the chat.
# It reads the tool result that ChatGPT passes in (window.openai.toolOutput).
IMAGE_WIDGET_HTML = r"""
<div id="flow-root" style="font-family: system-ui, sans-serif; color: inherit;"></div>
<script>
(function () {
  function render() {
    var root = document.getElementById("flow-root");
    var out = (window.openai && window.openai.toolOutput) || {};
    var r = out.result || out;
    var url = r.download_url;
    if (!url) {
      root.textContent = r.message || "Generating image in Google Flow...";
      return;
    }
    root.innerHTML = "";
    var isVideo = /\.(mp4|webm|mov)(\?|$)/i.test(url) || /video/i.test(r.mode || "");
    var img = document.createElement(isVideo ? "video" : "img");
    img.src = url;
    if (isVideo) {
      img.controls = true;
      img.playsInline = true;
      img.loop = true;
    } else {
      img.alt = "Generated image";
    }
    img.style.cssText = "display:block;max-width:100%;max-height:640px;border-radius:12px;margin:0 auto;";
    var link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.rel = "noopener";
    link.textContent = isVideo ? "Download video" : "Download image";
    link.style.cssText = "display:block;text-align:center;margin-top:8px;font-size:14px;color:inherit;";
    root.appendChild(img);
    root.appendChild(link);
  }
  window.addEventListener("openai:set_globals", render);
  render();
})();
</script>
"""


@mcp.resource(
    IMAGE_WIDGET_URI,
    name="flow-image-widget",
    mime_type="text/html+skybridge",
    meta={
        "openai/widgetDescription": "Shows the image or video generated in Google Flow with a download link.",
        "openai/widgetCSP": {"resource_domains": ["https://*.trycloudflare.com"], "connect_domains": []},
    },
)
def flow_image_widget() -> str:
    return IMAGE_WIDGET_HTML


@mcp.tool(
    meta={
        "openai/outputTemplate": IMAGE_WIDGET_URI,
        "openai/toolInvocation/invoking": "Generating image in Google Flow...",
        "openai/toolInvocation/invoked": "Image ready",
    }
)
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
        return _with_media(
            generate_image_via_flow_browser(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                reference_images=reference_images,
                output_path=output_path,
            ),
            show_image=True,
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


def _plain(result: Any) -> Any:
    """REST callers get plain JSON, not the MCP image wrapper."""
    sc = getattr(result, "structured_content", None)
    if isinstance(sc, dict) and "result" in sc:
        return sc["result"]
    return result


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
            return _plain(flow_generate_frame(
                prompt=req.prompt,
                reference_images=req.reference_images,
                aspect_ratio=req.aspect_ratio,
                image_size=req.image_size,
                previous_interaction_id=req.previous_interaction_id,
                use_browser_credits=req.use_browser_credits,
            ))
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


def _start_cloudflare_tunnel(port: int):
    """Start a free Cloudflare quick tunnel. Returns (process, public_url) or (None, None)."""
    import re
    import shutil
    import subprocess
    import time

    exe = shutil.which("cloudflared")
    if not exe:
        return None, None
    proc = subprocess.Popen(
        [exe, "tunnel", "--no-autoupdate", "--url", f"http://127.0.0.1:{port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    deadline = time.time() + 45
    while time.time() < deadline and proc.poll() is None:
        line = proc.stdout.readline()
        m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com", line or "")
        if m:
            import threading

            # Keep draining output so the tunnel never blocks on a full pipe.
            threading.Thread(target=lambda: [None for _ in proc.stdout], daemon=True).start()
            return proc, m.group(0)
    proc.terminate()
    return None, None


def _start_ngrok_tunnel(port: int, domain: str):
    """Keep a permanent ngrok link (your free static domain) pointed at this server.
    Restarts ngrok if it ever exits, so the link stays the same. Returns (stopper, public_url)."""
    import shutil
    import subprocess
    import threading
    import time

    exe = shutil.which("ngrok")
    if not exe:
        return None, None
    domain = domain.replace("https://", "").replace("http://", "").strip("/")
    state = {"proc": None, "stop": False}

    def run() -> None:
        while not state["stop"]:
            state["proc"] = subprocess.Popen(
                [exe, "http", f"--url=https://{domain}", str(port), "--log=stdout", "--log-level=warn"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            state["proc"].wait()
            if not state["stop"]:
                time.sleep(5)  # network blip or sleep: reconnect on the same domain

    threading.Thread(target=run, daemon=True).start()

    class _Stopper:
        def terminate(self) -> None:
            state["stop"] = True
            if state["proc"]:
                state["proc"].terminate()

    return _Stopper(), f"https://{domain}"


def _cloudflared_quick_tunnel_url(metrics_addr: str, wait_seconds: int = 60):
    """Read the public URL of a separately running cloudflared quick tunnel from its metrics server
    (cloudflared ... --metrics 127.0.0.1:20241). Keeping the tunnel in its own process means
    restarting or updating this server doesn't change the ChatGPT link."""
    import json
    import time
    import urllib.request

    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://{metrics_addr}/quicktunnel", timeout=3) as r:
                host = json.load(r).get("hostname")
            if host:
                return f"https://{host}"
        except Exception:
            pass
        time.sleep(2)
    return None


def _load_or_create_secret() -> str:
    """Use FLOW_SECRET, or a secret saved in ~/.google-flow-mcp/secret so the ChatGPT link stays the same."""
    import secrets

    if os.environ.get("FLOW_SECRET"):
        return os.environ["FLOW_SECRET"]
    path = os.path.join(os.path.expanduser("~"), ".google-flow-mcp", "secret")
    try:
        with open(path) as f:
            saved = f.read().strip()
        if saved:
            return saved
    except OSError:
        pass
    token = secrets.token_urlsafe(18)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(token)
    os.chmod(path, 0o600)
    return token


def _register_file_route(token: str) -> None:
    """Serve generated files at /<secret>/files/<name> so ChatGPT can show and download them."""
    from starlette.responses import FileResponse, PlainTextResponse

    @mcp.custom_route(f"/{token}/files/{{name}}", methods=["GET"], include_in_schema=False)
    async def _serve_file(request):  # type: ignore[no-untyped-def]
        name = os.path.basename(request.path_params.get("name", ""))
        media_dir = os.path.realpath(get_media_dir())
        path = os.path.realpath(os.path.join(media_dir, name))
        if not name or os.path.dirname(path) != media_dir or not os.path.isfile(path):
            return PlainTextResponse("Not found", status_code=404)
        return FileResponse(path)


def run_chatgpt_mode(port: int) -> None:
    """One command for ChatGPT: MCP over HTTP on a secret path, exposed through a public tunnel."""
    import sys

    token = _load_or_create_secret()
    path = f"/{token}/mcp"
    # FLOW_PUBLIC_URL: your own tunnel/domain. FLOW_NGROK_DOMAIN: a permanent free ngrok domain.
    # Otherwise a temporary Cloudflare quick tunnel is started (its link changes on restart).
    public_url = (os.environ.get("FLOW_PUBLIC_URL") or "").rstrip("/") or None
    ngrok_domain = os.environ.get("FLOW_NGROK_DOMAIN", "").strip()
    proc = None
    if not public_url and ngrok_domain:
        proc, public_url = _start_ngrok_tunnel(port, ngrok_domain)
    metrics = os.environ.get("FLOW_CLOUDFLARED_METRICS", "").strip()
    if not public_url and metrics:
        public_url = _cloudflared_quick_tunnel_url(metrics)
    if not public_url:
        proc, public_url = _start_cloudflare_tunnel(port)

    bar = "=" * 72
    print(bar, file=sys.stderr)
    if public_url:
        print("ChatGPT connector URL (paste this into ChatGPT, keep it private):", file=sys.stderr)
        print(f"\n    {public_url}{path}\n", file=sys.stderr)
        print("In ChatGPT: Plugins > Add > Add custom MCP server. Then type @Google Flow in a chat.", file=sys.stderr)
        print("Authentication: No authentication (the secret in the URL protects it).", file=sys.stderr)
    else:
        print("Could not start a public tunnel. Install cloudflared and run again:", file=sys.stderr)
        print("    brew install cloudflared", file=sys.stderr)
        print(f"Local URL (only reachable from this computer): http://127.0.0.1:{port}{path}", file=sys.stderr)
    print("Anyone with this URL can use your Flow credits. Press Ctrl-C to stop.", file=sys.stderr)
    print(bar, file=sys.stderr)

    _register_file_route(token)
    if public_url:
        os.environ["FLOW_PUBLIC_FILES_BASE"] = f"{public_url}/{token}/files"

    try:
        from mcp.server.transport_security import TransportSecuritySettings

        # The tunnel sends its own Host header; the secret path is the protection here.
        security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
        mcp.run(
            transport="streamable-http",
            host="127.0.0.1",
            port=port,
            streamable_http_path=path,
            transport_security=security,
        )
    finally:
        if proc:
            proc.terminate()


def main():
    parser = argparse.ArgumentParser(
        description="Run the Google Flow MCP Server (stdio, sse, streamable-http, or openapi)."
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http", "openapi", "chatgpt"],
        default="stdio",
        help=(
            "Transport protocol: 'stdio' (Claude, Gemini CLI), 'chatgpt' (one command: HTTP server + "
            "public tunnel + secret URL for ChatGPT), 'sse'/'streamable-http' (manual HTTP), or 'openapi' "
            "(ChatGPT Custom GPT Actions)."
        ),
    )
    parser.add_argument(
        "mode",
        nargs="?",
        choices=["chatgpt"],
        help="Shortcut: `google-flow-mcp chatgpt` is the same as `--transport chatgpt`.",
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
    if args.mode == "chatgpt":
        args.transport = "chatgpt"

    if args.transport == "chatgpt":
        run_chatgpt_mode(args.port)
        return

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
