# 🎬 Google Flow MCP Server (`google-flow-mcp`)

Use **Google Flow** (Google's AI video studio at [flow.google.com](https://flow.google.com)) from **Claude Desktop**, **Claude Code**, **ChatGPT**, and **Gemini CLI**.

Plan a shot with your assistant, then ask it to generate the video. The server drives Flow with **your own Google account and Flow credits**, so you don't need an API key.

> ⚠️ **Unofficial project.** This is not made by or affiliated with Google. Sign-in mode automates the Flow website in a Chrome window on your computer. Automating a website may go against Google's Terms of Service, and Google can change Flow's UI at any time, which can break this tool. Use it at your own risk with your own account.

---

## ✨ Tools

| Tool | Needs | What it does |
| :--- | :--- | :--- |
| `flow_browser_login` | Chrome | Opens Flow in Chrome so you can sign in once. Your sign-in is saved in `~/.google-flow-mcp/chrome-profile`. |
| `flow_text_to_video` | Flow sign-in | Starts a video from a text prompt with your Flow credits and returns a `job_id` right away. Video tools run in the background because a clip takes 1-5 minutes, longer than ChatGPT waits for a tool. |
| `flow_check_video` | nothing | Gets a video started by any video tool (pass its `job_id`) and saves the MP4. Waits up to 45s per call; call again while it is still generating. Free, no credits. |
| `flow_frames_to_video` | Flow sign-in *(experimental)* | Animates a starting image, or transitions from a first frame to a last frame. |
| `flow_reference_to_video` | Flow sign-in *(experimental)* | Generates a video guided by reference images (product, character, style). |
| `flow_generate_frame` | Flow sign-in | Generates an image (Nano Banana) with your Flow credits, saves it at full size, and returns the picture so Claude and ChatGPT can show it. Sets the aspect ratio (16:9, 4:3, 1:1, 3:4, 9:16) in Flow's settings and makes one image per request. Reference images are experimental. |
| `flow_show_latest` | nothing | Shows the most recent saved image or video again. Free, no credits. |
| `flow_extend_or_edit_video` | Gemini API key | Extends or edits an existing clip. |
| `flow_storyboard_director` | Gemini API key | Turns a brief into a multi-shot storyboard with frame and motion prompts. |

The video and image tools use your Flow sign-in by default. If you set `GEMINI_API_KEY` and pass `use_browser_credits=false`, they use the Gemini API instead. In sign-in mode Flow chooses the image size (for example 768×1376 for 9:16), so `image_size` and `model` only apply with an API key.

### How sign-in mode works
1. Opens Flow in Chrome with a saved profile, so you stay signed in.
2. Creates a new project, types your prompt, and starts the generation.
3. Flow asks before spending credits (for example *"costing 30 credits?"*). The tool clicks **Approve** for that one generation only, never "Always approve", and returns the cost as `credits_cost`. The tools also read your credit balance before and after, and report `credits_used`, `credits_before` and `credits_after`.
4. Waits for the result (up to 10 minutes for video, 4 for images), then saves it to your media folder. Images are saved at full size, not Flow's small preview. If the page misses the finished image, the tool reloads the project to find it.

**Runs in the background.** On a Mac the tool's Chrome is hidden (like Cmd+H) and minimized as soon as it starts, so it stays signed in without showing a window. Only its Dock icon appears while it works. Set `FLOW_SHOW_BROWSER=1` to watch it work. Only `flow_browser_login` shows a window, so you can sign in.

---

## 🚀 Install (2 minutes)

You need **Google Chrome**, a Google account with **Google Flow** credits, and **uv** (a Python installer). Install uv once:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

No cloning or Python setup needed: every command below runs the server straight from GitHub with `uvx`.

The first time you use it, ask your assistant to **run `flow_browser_login`** and sign in to Google in the Chrome window that opens. You only do this once.

Generated videos and images are saved to **`~/Downloads/google-flow`**.

---

## 🔌 Claude Code

```bash
claude mcp add google-flow -- uvx --from git+https://github.com/abdureda1999-ai/google-flow-mcp google-flow-mcp
```

## 🔌 Claude Desktop

Find the full path of `uvx` with `which uvx` (usually `~/.local/bin/uvx`), then add this to `~/Library/Application Support/Claude/claude_desktop_config.json` and restart Claude:

```json
{
  "mcpServers": {
    "google-flow": {
      "command": "/Users/YOU/.local/bin/uvx",
      "args": ["--from", "git+https://github.com/abdureda1999-ai/google-flow-mcp", "google-flow-mcp"]
    }
  }
}
```

## ♊ Gemini CLI

Add this to `~/.gemini/settings.json`, restart `gemini`, and run `/mcp` to check that `google-flow` is listed:

```json
{
  "mcpServers": {
    "google-flow": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/abdureda1999-ai/google-flow-mcp", "google-flow-mcp"]
    }
  }
}
```

> The Gemini web and mobile apps can't connect to custom MCP servers like this one, so use Gemini CLI.

## 🤖 ChatGPT

ChatGPT runs in the cloud, so it needs a public link to the server on your computer. One command sets that up. First install Cloudflare's free tunnel tool once:

```bash
brew install cloudflared
```

Then start ChatGPT mode:

```bash
uvx --from git+https://github.com/abdureda1999-ai/google-flow-mcp google-flow-mcp chatgpt
```

It prints a link like `https://something.trycloudflare.com/<secret>/mcp`. Then add it to ChatGPT once:

1. In ChatGPT, open **Plugins** (Settings → Plugins → **Browse directory**), click **Add** → **Add custom MCP server**.
2. Fill in:
   - **Name:** `Google Flow`
   - **Server URL:** the link from your Terminal
   - **Authentication:** **No authentication**
3. Tick **I understand and want to continue**, then click **Create as a plugin**.

**Using it:** in any chat, type **@Google Flow**, pick it, and ask for an image, for example:

> *@Google Flow make a 9:16 worm's-eye shot of a red soda can on grass against a blue summer sky*

ChatGPT shows "Generating image in Google Flow…", and after about a minute **the picture appears right in the chat** with a download link. Videos come back with a download link.

- Use a normal chat. ChatGPT's **Work** / agent mode opens Flow in its own browser instead of using this plugin, and won't show the image in the chat.
- Keep that Terminal window open while you use ChatGPT. Your computer must stay on.
- **The free Cloudflare link changes each time the tunnel restarts**, and ChatGPT can't edit a plugin's link, so you'd delete and re-add the plugin. To avoid that, use a permanent link (below).
- Click **Refresh tools** in **Plugins → Google Flow** after updating this server.

### Permanent link (recommended)

A free ngrok account gives you one domain that never changes:

1. Sign up at [dashboard.ngrok.com](https://dashboard.ngrok.com/signup), then run the `ngrok config add-authtoken ...` command shown under **Your Authtoken**.
2. Copy your free domain from **Domains** (like `something.ngrok-free.app`).
3. Start ChatGPT mode with it:

```bash
brew install ngrok
FLOW_NGROK_DOMAIN=something.ngrok-free.app uvx --from git+https://github.com/abdureda1999-ai/google-flow-mcp google-flow-mcp chatgpt
```

The secret part of the link is saved in `~/.google-flow-mcp/secret`, so the full link stays the same every time. Add it to ChatGPT once. If ngrok drops (sleep, Wi-Fi change), the server reconnects on the same domain.

Running it as a background service (launchd)? Add `FLOW_NGROK_DOMAIN` to the service's `EnvironmentVariables` and stop any separate `cloudflared` service, so only one tunnel points at the server.

**Switching an existing ChatGPT plugin to the permanent link**: ChatGPT can't edit a plugin's URL. In **Plugins → Google Flow**, click **Uninstall**, then **Delete app** (uninstalling alone keeps the old app, and its name blocks the new one with "An app with this name already exists"). Then **Add → Add custom MCP server** with the new link and **No authentication**.
- 🔒 **Anyone with the link can spend your Flow credits.** Don't share it, and press Ctrl-C when you're done.

<details>
<summary>Custom GPT Actions (OpenAPI) instead</summary>

```bash
uvx --from git+https://github.com/abdureda1999-ai/google-flow-mcp google-flow-mcp --transport openapi --port 8000
cloudflared tunnel --url http://127.0.0.1:8000
```
In **Create a GPT → Configure → Actions → Import from URL**, paste `https://YOUR-TUNNEL.trycloudflare.com/openapi.json`. This endpoint has no secret, so only run it while you're using it.
</details>

---

## 🧑‍💻 Developing locally

```bash
git clone https://github.com/abdureda1999-ai/google-flow-mcp.git
cd google-flow-mcp
python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/google-flow-mcp --help
```

---

## 💡 Example prompts

- *"Use `flow_text_to_video` to make a cinematic studio commercial of a matte black sports car under moving neon light, 16:9."*
- *"Make a 9:16 vertical clip of coffee being poured in slow motion with warm morning light."*
- *"Use `flow_generate_frame` to make a 9:16 worm's-eye product shot of a cold soda can against a blue summer sky."*
- *"Use `flow_frames_to_video` with `/path/to/start.png` as the first frame and `/path/to/end.png` as the last frame for an 8-second transition."*

---

## ⚙️ Configuration

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `FLOW_MEDIA_DIR` | `~/Downloads/google-flow` | Where videos, images and screenshots are saved. |
| `GEMINI_API_KEY` | not set | Turns on the API-only tools. |
| `FLOW_HOST` / `FLOW_PORT` | `127.0.0.1` / `8000` | Address for the HTTP transports. |
| `FLOW_SECRET` | saved in `~/.google-flow-mcp/secret` | Secret part of the ChatGPT link. |
| `FLOW_NGROK_DOMAIN` | not set | Your free permanent ngrok domain, so the ChatGPT link never changes. |
| `FLOW_SHOW_BROWSER` | not set | Set to `1` to show the Chrome window while generating. |
| `FLOW_PUBLIC_URL` | not set | Your own public address (for example a named Cloudflare tunnel) so the ChatGPT link stays the same. With it, no quick tunnel is started. |

## 🛠 Troubleshooting

- **Use a different Google account for Flow**: move `~/.google-flow-mcp/chrome-profile` aside (for example rename it to `chrome-profile-backup`), then run `flow_browser_login` (or `.venv/bin/python examples/sign_in.py`) and sign in with the other account. Results include `flow_account`, and Flow links carry `authuser=` so they open in that account.
- **ChatGPT hangs when the server runs as a background service (launchd) on a Mac**: macOS blocks background apps from reading `~/Downloads` until you approve it. Set `FLOW_MEDIA_DIR` to a folder outside Downloads, Documents and Desktop, for example `~/Google Flow`.
- **ChatGPT says "Google Flow's connection failed"**: ChatGPT can't reach the link saved in the plugin, and restarting the server won't fix that. A free Cloudflare quick tunnel can expire (`tunnel.log` shows `Unauthorized: Tunnel not found`), which gives you a new link. Check the URL in **Plugins → Google Flow** matches the one the server printed, and switch to a [permanent link](#permanent-link-recommended).
- **A video "timed out" in ChatGPT**: update this server. Video tools now return a `job_id` at once, and ChatGPT fetches the clip with `flow_check_video`. Click **Refresh tools** in the plugin's settings after updating.
- **ngrok `ERR_NGROK_105`**: the saved authtoken isn't valid. Run the full `ngrok config add-authtoken ...` command from [your ngrok dashboard](https://dashboard.ngrok.com/get-started/your-authtoken), with the real token, not a placeholder.
- **Flow in another language**: the tool always opens Flow in English (`hl=en`), so accounts set to Arabic or other languages work.

- **"Still on the Google Flow landing page"**: run `flow_browser_login` and finish signing in.
- **"Could not find the Flow prompt box"**: Flow's website changed. Please open an issue.
- **Chrome says the profile is in use**: close any Chrome window the tool left open, then try again.
- **`not_started` status**: Flow didn't ask to approve a generation. Check the saved `ui_screenshot`.

## 📄 License
MIT
