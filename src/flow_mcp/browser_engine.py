"""Browser-driven Google Flow Engine (No API Key Required).

Uses your logged-in Google account and Google AI Ultra / Pro credits directly on:
- Google Flow (`https://labs.google/fx/tools/flow`)
- Google Whisk (`https://labs.google/fx/tools/whisk`)

Maintains a persistent Chrome profile at `~/.google-flow-mcp/chrome-profile` so you only
sign in once with your Google email, and Claude / ChatGPT can trigger video & image
generations using your subscription credits.
"""

from __future__ import annotations

import os
import re
import time
import urllib.request
import uuid
from typing import Any, Dict, List, Optional

FLOW_URL = "https://labs.google/fx/tools/flow"
WHISK_URL = "https://labs.google/fx/tools/whisk"


def get_profile_dir() -> str:
    """Returns the persistent Chrome profile directory where your Google login lives."""
    default_dir = os.path.expanduser("~/.google-flow-mcp/chrome-profile")
    profile_dir = os.environ.get("FLOW_CHROME_PROFILE", default_dir)
    os.makedirs(profile_dir, exist_ok=True)
    return profile_dir


def get_media_dir() -> str:
    """Returns the directory where generated videos and images are saved."""
    media_dir = os.environ.get(
        "FLOW_MEDIA_DIR",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "media")),
    )
    os.makedirs(media_dir, exist_ok=True)
    return media_dir


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug[:45] or "flow_output"


def _launch_persistent_context(playwright: Any, headless: bool = False):
    """Launches Google Chrome with the persistent user profile."""
    profile_dir = get_profile_dir()
    # Remove stale SingletonLock if a previous Chrome instance crashed
    lock_file = os.path.join(profile_dir, "SingletonLock")
    if os.path.lexists(lock_file):
        try:
            os.remove(lock_file)
        except OSError:
            pass

    return playwright.chromium.launch_persistent_context(
        user_data_dir=profile_dir,
        channel="chrome",
        headless=headless,
        accept_downloads=True,
        viewport={"width": 1440, "height": 900},
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--no-default-browser-check",
        ],
    )


def login_and_verify_flow_session(wait_seconds: int = 120) -> Dict[str, Any]:
    """Opens Google Flow in a visible Chrome window so the user can log in with their Google email,
    or verifies that the session is already logged in and ready."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        context = _launch_persistent_context(p, headless=False)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.goto(FLOW_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(4)

            # Check if we need to click "Sign in" or "Create with Flow"
            start_time = time.time()
            logged_in = False

            while time.time() - start_time < wait_seconds:
                url = page.url
                content = page.content().lower()
                # Check if inside the Flow project workspace or New Project screen
                has_textarea = page.locator("textarea").count() > 0
                has_new_project = (
                    page.get_by_text("New project", exact=False).count() > 0
                    or page.get_by_role("button", name=re.compile(r"new project|create", re.I)).count() > 0
                )

                if ("accounts.google.com" not in url) and (has_textarea or has_new_project):
                    logged_in = True
                    break

                time.sleep(2)

            screenshot_path = os.path.join(get_media_dir(), "flow_session_status.png")
            page.screenshot(path=screenshot_path)

            return {
                "status": "authenticated" if logged_in else "waiting_for_login",
                "current_url": page.url,
                "profile_dir": get_profile_dir(),
                "screenshot_path": screenshot_path,
                "message": (
                    "Google Flow session is logged in and ready to use your subscription credits!"
                    if logged_in
                    else "Chrome window opened to Google Flow. Please finish signing in with your Google email and run again."
                ),
            }
        finally:
            context.close()


def generate_video_via_flow_browser(
    prompt: str,
    mode: str = "text_to_video",
    first_frame: Optional[str] = None,
    last_frame: Optional[str] = None,
    reference_images: Optional[List[str]] = None,
    aspect_ratio: str = "16:9",
    output_path: Optional[str] = None,
    timeout_seconds: int = 240,
    headless: bool = False,
) -> Dict[str, Any]:
    """Automates the live Google Flow web UI (`labs.google/fx/tools/flow`) using your logged-in
    Google account and AI credits (no API key needed)."""
    from playwright.sync_api import sync_playwright

    if not output_path:
        filename = f"flow_browser_{_slugify(prompt)}_{uuid.uuid4().hex[:6]}.mp4"
        output_path = os.path.join(get_media_dir(), filename)
    else:
        output_path = os.path.abspath(output_path)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

    captured_video_urls: List[str] = []

    def _on_response(response: Any) -> None:
        try:
            ct = response.headers.get("content-type", "").lower()
            url = response.url
            if "video/mp4" in ct or url.endswith(".mp4") or ("storage.googleapis.com" in url and "video" in ct):
                if url not in captured_video_urls:
                    captured_video_urls.append(url)
        except Exception:
            pass

    with sync_playwright() as p:
        context = _launch_persistent_context(p, headless=headless)
        try:
            page = context.pages[0] if context.pages else context.new_page()
            page.on("response", _on_response)
            page.goto(FLOW_URL, wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)

            # 1. If on landing page, click "Create with Flow" or "New project"
            for btn_pattern in [r"create with flow", r"new project", r"get started", r"start creating"]:
                btn = page.get_by_role("button", name=re.compile(btn_pattern, re.I))
                if btn.count() > 0 and btn.first.is_visible():
                    btn.first.click()
                    time.sleep(4)
                    break

            # Also check links/divs with "New project"
            new_proj_text = page.get_by_text(re.compile(r"^\+?\s*New project$", re.I))
            if new_proj_text.count() > 0 and new_proj_text.first.is_visible():
                new_proj_text.first.click()
                time.sleep(4)

            # Verify not stuck on Google login
            if "accounts.google.com" in page.url:
                raise RuntimeError(
                    "You are not signed in to Google Flow yet. Call `flow_browser_login` first and sign in with your Google email in the Chrome window."
                )

            # 2. Select generation mode if mode dropdown exists (Text to Video / Frames to Video / Ingredients to Video)
            target_mode_label = {
                "text_to_video": "Text to Video",
                "frames_to_video": "Frames to Video",
                "reference_to_video": "Ingredients to Video",
            }.get(mode, "Text to Video")

            mode_selector = page.get_by_text(
                re.compile(r"Text to Video|Frames to Video|Ingredients to Video", re.I)
            )
            if mode_selector.count() > 0 and mode_selector.first.is_visible():
                current_mode_text = mode_selector.first.inner_text()
                if target_mode_label.lower() not in current_mode_text.lower():
                    mode_selector.first.click()
                    time.sleep(1)
                    option = page.get_by_text(re.compile(target_mode_label, re.I))
                    if option.count() > 0:
                        option.last.click()
                        time.sleep(1.5)

            # 3. Upload frames or reference images if provided
            files_to_upload: List[str] = []
            if first_frame and os.path.exists(first_frame):
                files_to_upload.append(os.path.abspath(first_frame))
            if last_frame and os.path.exists(last_frame):
                files_to_upload.append(os.path.abspath(last_frame))
            if reference_images:
                for img in reference_images:
                    if os.path.exists(img):
                        files_to_upload.append(os.path.abspath(img))

            if files_to_upload:
                file_inputs = page.locator('input[type="file"]')
                if file_inputs.count() > 0:
                    file_inputs.first.set_input_files(files_to_upload)
                    time.sleep(4)

            # 4. Fill the prompt textarea
            textarea = page.locator("textarea").first
            textarea.wait_for(state="visible", timeout=30000)

            existing_videos = page.locator("video").count()
            initial_captured_count = len(captured_video_urls)

            textarea.click()
            textarea.fill(prompt)
            time.sleep(1)

            # 5. Click the Generate / Submit button (or press Enter)
            submitted = False
            for submit_pattern in [r"generate", r"create", r"submit", r"arrow_forward", r"send"]:
                gen_btn = page.get_by_role("button", name=re.compile(submit_pattern, re.I))
                if gen_btn.count() > 0 and gen_btn.last.is_visible() and gen_btn.last.is_enabled():
                    gen_btn.last.click()
                    submitted = True
                    break

            if not submitted:
                textarea.press("Enter")

            # 6. Wait for the new video to render or download
            start_wait = time.time()
            downloaded_file: Optional[str] = None
            final_video_src: Optional[str] = None

            while time.time() - start_wait < timeout_seconds:
                # Check if a new network MP4 response was captured
                if len(captured_video_urls) > initial_captured_count:
                    final_video_src = captured_video_urls[-1]
                    break

                # Check if a new <video> element appeared with a valid src
                videos = page.locator("video")
                if videos.count() > existing_videos:
                    for idx in range(videos.count() - 1, -1, -1):
                        v = videos.nth(idx)
                        src = v.get_attribute("src") or ""
                        if not src:
                            source_tag = v.locator("source").first
                            if source_tag.count() > 0:
                                src = source_tag.get_attribute("src") or ""
                        if src and src.startswith("http"):
                            final_video_src = src
                            break
                    if final_video_src:
                        break

                time.sleep(3)

            # Save a UI screenshot of the result
            ui_screenshot = os.path.splitext(output_path)[0] + "_flow_ui.png"
            page.screenshot(path=ui_screenshot)

            if final_video_src and final_video_src.startswith("http"):
                # Download via the authenticated browser context
                resp = context.request.get(final_video_src)
                if resp.ok:
                    with open(output_path, "wb") as f:
                        f.write(resp.body())
                    downloaded_file = output_path

            return {
                "status": "completed" if downloaded_file else "submitted_in_flow_ui",
                "engine": "google_flow_browser_credits",
                "mode": mode,
                "prompt": prompt,
                "output_path": downloaded_file,
                "ui_screenshot": ui_screenshot,
                "flow_project_url": page.url,
                "video_src": final_video_src,
                "message": (
                    f"Video generated using your Google Flow account credits and saved to {downloaded_file}"
                    if downloaded_file
                    else f"Prompt submitted in your Google Flow browser session ({page.url}). Screenshot saved to {ui_screenshot}."
                ),
            }
        finally:
            context.close()
