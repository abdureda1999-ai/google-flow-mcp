"""Core Google Flow Engine powered by the official google-genai Interactions API.

Wraps:
- Video Generation, Keyframe Interpolation, R2V, Extension & Editing (`gemini-omni-1.2-flash`)
- Frame & Whisk-style Reference Image Fusion (`gemini-nano-banana-2.1` / `gemini-3-pro-image`)
- AI Storyboard & Shot Breakdown Director (`gemini-4-hydrogen`)
"""

from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
import subprocess
import time
import urllib.parse
import uuid
from typing import Any, Dict, List, Optional, Tuple

from google import genai
from google.genai import errors, types

DEFAULT_VIDEO_MODEL = "gemini-omni-1.2-flash"
DEFAULT_IMAGE_MODEL = "gemini-nano-banana-2.1"
DEFAULT_DIRECTOR_MODEL = "gemini-4-hydrogen"

MIN_DURATION_SECONDS = 3
MAX_DURATION_SECONDS = 15
MAX_INTERPOLATION_OR_EXTEND_SECONDS = 10
MAX_REFERENCE_IMAGES = 6
MAX_REFERENCE_VIDEOS_SHORT = 3
MAX_REFERENCE_VIDEOS_LONG = 1


def get_api_key() -> Optional[str]:
    """Retrieves API key from GEMINI_API_KEY environment variable."""
    return os.environ.get("GEMINI_API_KEY")


def get_media_dir() -> str:
    """Returns the configured local media output directory."""
    # Default to a folder people can find, also when installed with uvx/pipx.
    media_dir = os.path.expanduser(os.environ.get("FLOW_MEDIA_DIR") or "~/Downloads/google-flow")
    os.makedirs(media_dir, exist_ok=True)
    return media_dir


def strip_query_params(url: Optional[str]) -> str:
    """Strips query parameters from URL for clean logging and security."""
    if not url:
        return ""
    parsed = urllib.parse.urlparse(url)
    return urllib.parse.urlunparse(parsed._replace(query=""))


def sanitize_error(err: Any) -> str:
    """Sanitizes error messages by redacting API keys, tokens, and internal URLs."""
    if not err:
        return ""

    if isinstance(err, errors.APIError):
        parts = []
        if getattr(err, "code", None):
            parts.append(str(err.code))
        if getattr(err, "status", None):
            parts.append(f"({err.status})")
        if getattr(err, "message", None):
            parts.append(f": {err.message}")
        elif getattr(err, "details", None):
            parts.append(f": {err.details}")
        err_str = " ".join(parts) if parts else str(err)
    else:
        err_str = str(err)

    key = get_api_key()
    if key and len(key) >= 8:
        err_str = err_str.replace(key, "[REDACTED_KEY]")

    err_str = re.sub(r"AIza[0-9A-Za-z_\-]{30,}", "[REDACTED_KEY]", err_str)
    err_str = re.sub(r"AQ\.[0-9A-Za-z_\-]{20,}", "[REDACTED_KEY]", err_str)
    err_str = re.sub(r"ya29\.[0-9A-Za-z_\-]+", "[REDACTED_TOKEN]", err_str)
    err_str = re.sub(
        r"Bearer\s+[A-Za-z0-9_\-\.]+",
        "Bearer [REDACTED_TOKEN]",
        err_str,
        flags=re.IGNORECASE,
    )
    err_str = re.sub(
        r"([?&](?:key|api_key|apiKey|access_token|auth|signature)=)[^&\s\"'<>()]+",
        r"\1[REDACTED]",
        err_str,
    )
    err_str = re.sub(r"\s+", " ", err_str).strip()
    if len(err_str) > 500:
        err_str = err_str[:497] + "..."
    return err_str


_SENSITIVE_DIR_NAMES = {".ssh", ".aws", ".gnupg", ".kube"}


def _is_within(path: str, root: str) -> bool:
    real_path = os.path.realpath(path)
    real_root = os.path.realpath(root)
    return real_path == real_root or real_path.startswith(real_root + os.sep)


def _touches_sensitive_path(path: str) -> bool:
    real_path = os.path.realpath(path)
    home = os.path.realpath(os.path.expanduser("~"))
    blocked_roots = [
        os.path.join(home, ".google-flow-mcp", "chrome-profile"),
        os.path.join(home, ".google-flow-mcp", "secret"),
        os.path.join(home, ".config", "gcloud"),
        "/etc",
        "/private/etc",
    ]
    for blocked in blocked_roots:
        if _is_within(real_path, blocked):
            return True
    parts = set(real_path.split(os.sep))
    return bool(parts & _SENSITIVE_DIR_NAMES)


def is_strict_media_sandbox() -> bool:
    val = os.environ.get("FLOW_STRICT_MEDIA_SANDBOX", "").strip().lower()
    return val in {"1", "true", "yes", "on"}


def validate_safe_output_path(output_path: Optional[str]) -> Optional[str]:
    """Validates custom output_path against sensitive directories and strict tunnel sandbox."""
    if not output_path:
        return None
    resolved = os.path.abspath(os.path.expanduser(output_path))
    if _touches_sensitive_path(resolved):
        raise ValueError(f"Refusing to write output to sensitive path: {output_path}")
    if is_strict_media_sandbox() and not _is_within(resolved, get_media_dir()):
        raise ValueError(
            f"Custom output_path must stay inside FLOW_MEDIA_DIR ({get_media_dir()}) when strict media sandbox is active."
        )
    return resolved


def validate_safe_input_path(input_path: str) -> str:
    """Validates local input asset paths before uploading to Flow or Gemini Files API."""
    if is_file_uri(input_path):
        return input_path
    resolved = os.path.abspath(os.path.expanduser(input_path))
    if _touches_sensitive_path(resolved):
        raise ValueError(f"Refusing to read input asset from sensitive path: {input_path}")
    if is_strict_media_sandbox():
        allowed_roots = [get_media_dir()]
        extra_dir = os.environ.get("FLOW_ALLOWED_INPUT_DIR", "").strip()
        if extra_dir:
            allowed_roots.append(os.path.expanduser(extra_dir))
        if not any(_is_within(resolved, r) for r in allowed_roots):
            raise ValueError(
                f"Input path '{input_path}' must reside inside FLOW_MEDIA_DIR (or FLOW_ALLOWED_INPUT_DIR) when strict media sandbox is active."
            )
    return resolved


def slugify(text: str, default: str = "flow_asset") -> str:
    """Converts a prompt (including Arabic and other Unicode scripts) into a safe filename slug."""
    cleaned = re.sub(r"[\u064B-\u065F\u0670\u0640]", "", text or "")
    slug = re.sub(r"[^\w]+", "_", cleaned.lower(), flags=re.UNICODE).strip("_")
    return slug[:45] or default


def detect_mime_type(file_path: str) -> str:
    """Determines MIME type based on file extension."""
    ext = os.path.splitext(file_path)[1].lower()
    mime_map = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".pdf": "application/pdf",
    }
    if ext in mime_map:
        return mime_map[ext]
    guessed, _ = mimetypes.guess_type(file_path)
    return guessed or "application/octet-stream"


def is_file_uri(uri: Optional[str]) -> bool:
    """Returns True if the string is a Gemini Files API URI."""
    if not uri:
        return False
    return "files/" in uri and (
        "generativelanguage.googleapis.com" in uri or uri.startswith("files/")
    )


def normalize_file_uri(uri: Optional[str]) -> Optional[str]:
    """Normalizes any File API URI/reference to standard format."""
    if not uri:
        return None
    match = re.search(r"files/([a-zA-Z0-9]+)", uri)
    if match:
        file_id = match.group(1)
        return f"https://generativelanguage.googleapis.com/files/{file_id}"
    return strip_query_params(uri)


def upload_and_wait_active(
    file_path: str,
    display_name: Optional[str] = None,
    max_timeout: int = 300,
) -> Dict[str, Any]:
    """Uploads a local file to the Gemini Files API and waits until ACTIVE."""
    if not get_api_key():
        raise RuntimeError(
            "GEMINI_API_KEY environment variable is not set. Set it before calling Flow tools."
        )
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Local file not found: {file_path}")

    mime_type = detect_mime_type(file_path)
    if not display_name:
        display_name = os.path.basename(file_path)

    client = genai.Client(http_options=types.HttpOptions(timeout=max_timeout * 1000))
    config = types.UploadFileConfig(display_name=display_name, mime_type=mime_type)
    file_obj = client.files.upload(file=file_path, config=config)
    file_name = file_obj.name

    start_time = time.time()
    interval = 2.0
    while time.time() - start_time < max_timeout:
        current = client.files.get(name=file_name)
        state = current.state
        state_str = state.name if hasattr(state, "name") else str(state)
        if state == types.FileState.ACTIVE or state_str == "ACTIVE":
            data = json.loads(current.model_dump_json())
            if data.get("uri"):
                data["uri"] = normalize_file_uri(data["uri"])
            data["mimeType"] = data.get("mime_type") or mime_type
            return data
        if state == types.FileState.FAILED or state_str == "FAILED":
            raise RuntimeError(f"Gemini Files API processing failed for {file_name}.")
        time.sleep(interval)
        interval = min(interval * 1.3, 10.0)

    raise TimeoutError(f"Timed out waiting for uploaded file {file_name} to become ACTIVE.")


def resolve_or_upload_asset(
    asset_path: str,
    default_mime: str,
    strip_audio: bool = False,
) -> Tuple[str, str]:
    """Resolves an existing Files API URI or uploads a local file."""
    if is_file_uri(asset_path):
        if strip_audio:
            raise ValueError(
                "strip_audio=True requires a local video file path rather than a remote File URI."
            )
        normalized = normalize_file_uri(asset_path)
        return normalized or asset_path, default_mime

    asset_path = validate_safe_input_path(asset_path)
    if not os.path.exists(asset_path):
        raise FileNotFoundError(
            f"Asset '{asset_path}' is neither a valid Gemini File URI nor an existing local path."
        )

    upload_target = asset_path
    temp_stripped = None
    try:
        if strip_audio:
            media_dir = get_media_dir()
            base_name = os.path.basename(asset_path)
            name, ext = os.path.splitext(base_name)
            temp_stripped = os.path.join(
                media_dir, f"temp_stripped_{name}_{uuid.uuid4().hex[:8]}{ext}"
            )
            cmd = ["ffmpeg", "-y", "-i", asset_path, "-c:v", "copy", "-an", temp_stripped]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if proc.returncode != 0:
                raise RuntimeError(
                    f"ffmpeg failed to strip audio: {sanitize_error(proc.stderr)}"
                )
            upload_target = temp_stripped

        meta = upload_and_wait_active(upload_target)
        return meta["uri"], meta.get("mimeType") or default_mime
    finally:
        if temp_stripped and os.path.exists(temp_stripped):
            try:
                os.remove(temp_stripped)
            except OSError:
                pass


def generate_frame_image(
    prompt: str,
    reference_images: Optional[List[str]] = None,
    aspect_ratio: str = "16:9",
    image_size: str = "2K",
    model: str = DEFAULT_IMAGE_MODEL,
    previous_interaction_id: Optional[str] = None,
    output_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Generates or edits a high-resolution frame or Whisk-style reference fusion image."""
    if not get_api_key():
        raise RuntimeError("GEMINI_API_KEY environment variable is not set.")

    input_parts: List[Dict[str, Any]] = []
    if reference_images:
        if len(reference_images) > 14:
            raise ValueError("Up to 14 reference images are supported by Nano Banana 2.1.")
        for img_path in reference_images:
            uri, mime = resolve_or_upload_asset(img_path, "image/png")
            input_parts.append({"type": "image", "uri": uri, "mime_type": mime})

    input_parts.append({"type": "text", "text": prompt.strip()})

    if not output_path:
        filename = f"frame_{slugify(prompt)}_{uuid.uuid4().hex[:6]}.png"
        output_path = os.path.join(get_media_dir(), filename)
    else:
        output_path = validate_safe_output_path(output_path) or output_path
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    client = genai.Client(http_options=types.HttpOptions(timeout=300 * 1000))
    create_kwargs: Dict[str, Any] = {
        "model": model,
        "input": input_parts,
        "response_format": {
            "type": "image",
            "mime_type": "image/png",
            "aspect_ratio": aspect_ratio,
            "image_size": image_size.upper(),
        },
    }
    if previous_interaction_id:
        create_kwargs["previous_interaction_id"] = previous_interaction_id

    try:
        interaction = client.interactions.create(**create_kwargs)
    except Exception as e:
        raise RuntimeError(f"Frame generation failed: {sanitize_error(e)}")

    generated_image = getattr(interaction, "output_image", None)
    if not generated_image or not getattr(generated_image, "data", None):
        raise RuntimeError("No image data returned by the model.")

    image_bytes = base64.b64decode(generated_image.data)
    with open(output_path, "wb") as f:
        f.write(image_bytes)

    return {
        "status": "completed",
        "model": model,
        "interaction_id": interaction.id,
        "output_path": output_path,
        "aspect_ratio": aspect_ratio,
        "image_size": image_size.upper(),
        "prompt": prompt,
    }


def generate_flow_video(
    prompt: str,
    aspect_ratio: str = "16:9",
    duration: int = 10,
    resolution: str = "720p",
    first_frame: Optional[str] = None,
    last_frame: Optional[str] = None,
    reference_images: Optional[List[str]] = None,
    reference_videos: Optional[List[str]] = None,
    extend_video: Optional[str] = None,
    edit_video: Optional[str] = None,
    strip_audio: bool = False,
    previous_interaction_id: Optional[str] = None,
    output_path: Optional[str] = None,
    model: str = DEFAULT_VIDEO_MODEL,
    timeout: int = 600,
) -> Dict[str, Any]:
    """Generates, interpolates, references, extends, or edits a video with Gemini Omni 1.2 Flash."""
    if not get_api_key():
        raise RuntimeError("GEMINI_API_KEY environment variable is not set.")

    if last_frame and not first_frame:
        raise ValueError("last_frame requires first_frame to be provided.")

    if duration < MIN_DURATION_SECONDS or duration > MAX_DURATION_SECONDS:
        raise ValueError(
            f"Duration must be between {MIN_DURATION_SECONDS} and {MAX_DURATION_SECONDS} seconds."
        )

    if (first_frame and last_frame) or extend_video:
        if duration > MAX_INTERPOLATION_OR_EXTEND_SECONDS:
            raise ValueError(
                f"Keyframe transitions and video extensions support {MIN_DURATION_SECONDS}s to {MAX_INTERPOLATION_OR_EXTEND_SECONDS}s per turn (got {duration}s)."
            )

    ref_imgs = reference_images or []
    if len(ref_imgs) > MAX_REFERENCE_IMAGES:
        raise ValueError(f"Up to {MAX_REFERENCE_IMAGES} reference images are supported.")

    ref_vids = reference_videos or []
    if ref_vids:
        if extend_video or edit_video or previous_interaction_id:
            raise ValueError(
                "Reference videos are only supported when generating a new video, not during video editing or extension."
            )
        max_vids = (
            MAX_REFERENCE_VIDEOS_LONG
            if duration > MAX_INTERPOLATION_OR_EXTEND_SECONDS
            else MAX_REFERENCE_VIDEOS_SHORT
        )
        if len(ref_vids) > max_vids:
            raise ValueError(
                f"Up to {max_vids} reference video(s) supported for {duration}s generation."
            )

    res_clean = resolution.strip().lower()
    if res_clean not in {"360p", "720p", "1080p", "4k"}:
        raise ValueError("Resolution must be one of: 360p, 720p, 1080p, 4k.")

    input_parts: List[Dict[str, Any]] = []

    f1_uri, f1_mime = None, None
    if first_frame:
        f1_uri, f1_mime = resolve_or_upload_asset(first_frame, "image/png")
        input_parts.append({"type": "image", "uri": f1_uri, "mime_type": f1_mime})

    if last_frame:
        if last_frame == first_frame and f1_uri:
            input_parts.append({"type": "image", "uri": f1_uri, "mime_type": f1_mime})
        else:
            f2_uri, f2_mime = resolve_or_upload_asset(last_frame, "image/png")
            input_parts.append({"type": "image", "uri": f2_uri, "mime_type": f2_mime})

    for img in ref_imgs:
        u, m = resolve_or_upload_asset(img, "image/png")
        input_parts.append({"type": "image", "uri": u, "mime_type": m})

    if extend_video:
        u, m = resolve_or_upload_asset(extend_video, "video/mp4", strip_audio=strip_audio)
        input_parts.append({"type": "video", "uri": u, "mime_type": m})

    if edit_video:
        u, m = resolve_or_upload_asset(edit_video, "video/mp4", strip_audio=strip_audio)
        input_parts.append({"type": "video", "uri": u, "mime_type": m})

    for rv in ref_vids:
        u, m = resolve_or_upload_asset(rv, "video/mp4", strip_audio=strip_audio)
        input_parts.append({"type": "video", "uri": u, "mime_type": m})

    prompt_text = prompt.strip()

    def _append_hint(text: str, hint: str) -> str:
        if not text:
            return hint
        sep = "" if text[-1] in ".!?" else "."
        return f"{text}{sep} {hint}"

    if extend_video:
        if not any(
            k in prompt_text.lower() for k in ("extend", "continue", "continuation", "keep going")
        ):
            prompt_text = f"Extend this video. {prompt_text}".strip()
    elif first_frame and last_frame:
        if first_frame == last_frame:
            if "starting frame" not in prompt_text.lower() and "first frame" not in prompt_text.lower():
                first_ref = "the first image" if ref_imgs else "this image"
                prompt_text = _append_hint(
                    prompt_text,
                    f"Use {first_ref} as both the starting frame and the final frame.",
                )
        else:
            if "starting frame" not in prompt_text.lower() and "first frame" not in prompt_text.lower():
                prompt_text = _append_hint(
                    prompt_text,
                    "Use the first image as the starting frame and the second image as the final frame.",
                )
    elif first_frame:
        if "starting frame" not in prompt_text.lower() and "first frame" not in prompt_text.lower():
            first_ref = "the first image" if ref_imgs else "this image"
            prompt_text = _append_hint(prompt_text, f"Use {first_ref} as the starting frame.")

    input_parts.append({"type": "text", "text": prompt_text})

    video_config: Dict[str, Any] = {
        "type": "video",
        "delivery": "uri",
        "aspect_ratio": aspect_ratio,
        "duration": f"{duration}s",
        "resolution": res_clean,
    }

    if not output_path:
        filename = f"video_{slugify(prompt)}_{uuid.uuid4().hex[:6]}.mp4"
        output_path = os.path.join(get_media_dir(), filename)
    else:
        output_path = validate_safe_output_path(output_path) or output_path
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    client = genai.Client(http_options=types.HttpOptions(timeout=int(timeout) * 1000))
    create_kwargs: Dict[str, Any] = {
        "model": model,
        "input": input_parts,
        "response_format": video_config,
    }
    if previous_interaction_id:
        create_kwargs["previous_interaction_id"] = previous_interaction_id

    try:
        interaction = client.interactions.create(**create_kwargs)
    except Exception as e:
        raise RuntimeError(f"Video generation failed: {sanitize_error(e)}")

    output_video = getattr(interaction, "output_video", None)
    if not output_video or not getattr(output_video, "uri", None):
        err_msg = "No video URI returned in response."
        if edit_video or extend_video or ref_vids:
            err_msg += (
                " Note: Uploading videos for edits, extensions, or references is restricted in the EEA, UK, Switzerland, and some US states."
            )
        raise RuntimeError(err_msg)

    video_bytes = client.files.download(file=output_video.uri)
    with open(output_path, "wb") as f:
        f.write(video_bytes)

    return {
        "status": "completed",
        "model": model,
        "interaction_id": interaction.id,
        "output_path": output_path,
        "video_uri": strip_query_params(output_video.uri),
        "aspect_ratio": aspect_ratio,
        "duration": f"{duration}s",
        "resolution": res_clean,
        "prompt": prompt_text,
    }


def generate_storyboard_plan(
    concept: str,
    num_shots: int = 3,
    reference_images: Optional[List[str]] = None,
    aspect_ratio: str = "16:9",
    model: str = DEFAULT_DIRECTOR_MODEL,
) -> Dict[str, Any]:
    """Uses Gemini 4 Hydrogen as an AI Creative Director to plan multi-shot Flow prompts."""
    if not get_api_key():
        raise RuntimeError("GEMINI_API_KEY environment variable is not set.")

    input_parts: List[Dict[str, Any]] = []
    if reference_images:
        for img_path in reference_images:
            uri, mime = resolve_or_upload_asset(img_path, "image/png")
            input_parts.append({"type": "image", "uri": uri, "mime_type": mime})

    schema = {
        "type": "object",
        "properties": {
            "campaign_title": {"type": "string"},
            "visual_style_guide": {"type": "string"},
            "shots": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "shot_number": {"type": "integer"},
                        "duration_seconds": {"type": "integer"},
                        "first_frame_prompt": {"type": "string"},
                        "video_motion_prompt": {"type": "string"},
                        "sound_design": {"type": "string"},
                    },
                    "required": [
                        "shot_number",
                        "duration_seconds",
                        "first_frame_prompt",
                        "video_motion_prompt",
                        "sound_design",
                    ],
                },
            },
        },
        "required": ["campaign_title", "visual_style_guide", "shots"],
    }

    director_instruction = (
        f"You are an expert Commercial Film Director & Google Flow Pipeline Architect. "
        f"Break the user's concept into a {num_shots}-shot commercial storyboard for {aspect_ratio} aspect ratio. "
        f"For each shot, write a detailed `first_frame_prompt` (for Nano Banana 2.1 image generation) and a "
        f"`video_motion_prompt` (for Gemini Omni 1.2 Flash video generation, including camera movement, lighting, and sound design)."
    )

    input_parts.append({"type": "text", "text": f"{director_instruction}\n\nConcept: {concept}"})

    client = genai.Client(http_options=types.HttpOptions(timeout=120 * 1000))
    interaction = client.interactions.create(
        model=model,
        input=input_parts,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": schema,
        },
    )

    raw_text = interaction.output_text or "{}"
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        parsed = {"raw_storyboard": raw_text}

    return {
        "status": "completed",
        "model": model,
        "interaction_id": interaction.id,
        "storyboard": parsed,
    }
