# 🎬 Google Flow MCP Server (`google-flow-mcp`)

Use **Google Flow** (Google's AI video studio at [flow.google.com](https://flow.google.com)) from **Claude Desktop**, **Claude Code**, **ChatGPT**, and **Gemini CLI**.

Plan a shot with your assistant, then ask it to generate the video. The server drives Flow with **your own Google account and Flow credits**, so you don't need an API key.

> ⚠️ **Unofficial project.** This is not made by or affiliated with Google. Sign-in mode automates the Flow website in a Chrome window on your computer. Automating a website may go against Google's Terms of Service, and Google can change Flow's UI at any time, which can break this tool. Use it at your own risk with your own account.

---

## ✨ Tools

| Tool | Needs | What it does |
| :--- | :--- | :--- |
| `flow_browser_login` | Chrome | Opens Flow in Chrome so you can sign in once. Your sign-in is saved in `~/.google-flow-mcp/chrome-profile`. |
| `flow_text_to_video` | Flow sign-in | Generates a video from a text prompt with your Flow credits and saves the MP4. |
| `flow_frames_to_video` | Flow sign-in *(experimental)* | Animates a starting image, or transitions from a first frame to a last frame. |
| `flow_reference_to_video` | Flow sign-in *(experimental)* | Generates a video guided by reference images (product, character, style). |
| `flow_generate_frame` | Gemini API key | Generates a still image or keyframe, optionally from reference images. |
| `flow_extend_or_edit_video` | Gemini API key | Extends or edits an existing clip. |
| `flow_storyboard_director` | Gemini API key | Turns a brief into a multi-shot storyboard with frame and motion prompts. |

The video tools use your Flow sign-in by default. If you set `GEMINI_API_KEY` and pass `use_browser_credits=false`, they use the Gemini API instead.

### How sign-in mode works
1. Opens Flow in Chrome with a saved profile, so you stay signed in.
2. Creates a new project, types your prompt, and starts the generation.
3. Flow asks before spending credits (for example *"costing 30 credits?"*). The tool clicks **Approve** for that one generation only, never "Always approve", and returns the cost as `credits_cost`.
4. Waits up to 10 minutes for the video, then saves it to your media folder.

**Leave the Chrome window open until the tool finishes.** Closing it stops the download, but the clip may still finish in your Flow project.

---

## 🚀 Install

### Requirements
- Python 3.10+
- Google Chrome
- A Google account with Google Flow access and credits
- Optional: a [Gemini API key](https://aistudio.google.com/apikey) for the API-only tools

### Setup
```bash
git clone https://github.com/abdureda1999-ai/google-flow-mcp.git
cd google-flow-mcp
python3 -m venv .venv
.venv/bin/pip install -e .
```
Sign-in mode uses your installed Google Chrome, so no extra browser download is needed.

---

## 🔌 Connect to Claude

### Claude Code
```bash
claude mcp add google-flow \
  -e FLOW_MEDIA_DIR="$PWD/media" \
  -- "$PWD/.venv/bin/google-flow-mcp" --transport stdio
```

### Claude Desktop
Add this to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "google-flow": {
      "command": "/ABSOLUTE/PATH/TO/google-flow-mcp/.venv/bin/google-flow-mcp",
      "args": ["--transport", "stdio"],
      "env": {
        "FLOW_MEDIA_DIR": "/ABSOLUTE/PATH/TO/google-flow-mcp/media"
      }
    }
  }
}
```

Add `"GEMINI_API_KEY": "..."` to `env` only if you want the API-only tools.

Then ask Claude: *"Run `flow_browser_login`"*, sign in in the Chrome window, and you're ready.

---

## 🤖 Connect to ChatGPT

ChatGPT runs in the cloud, so it needs a public HTTPS address that reaches the server on your computer. Because sign-in mode opens Chrome on your machine, **your computer must be on with the server and tunnel running** while ChatGPT uses it.

### Option A: MCP connector (ChatGPT developer mode)
```bash
.venv/bin/google-flow-mcp --transport streamable-http --port 8000
```
In another terminal, expose it over HTTPS:
```bash
ngrok http 8000
```
In ChatGPT, open **Settings → Connectors → Advanced → Developer mode**, add a connector, and enter `https://YOUR-TUNNEL.ngrok-free.app/mcp`.

### Option B: Custom GPT Actions (OpenAPI)
```bash
.venv/bin/google-flow-mcp --transport openapi --port 8000
```
Expose it with `ngrok http 8000`, then in **Create a GPT → Configure → Actions → Import from URL** paste `https://YOUR-TUNNEL.ngrok-free.app/openapi.json`.

> 🔒 Anyone with your tunnel URL can use your Flow credits. Don't share the URL, and stop the tunnel when you're done.

---

## ♊ Connect to Gemini CLI

Add the server to `~/.gemini/settings.json`:

```json
{
  "mcpServers": {
    "google-flow": {
      "command": "/ABSOLUTE/PATH/TO/google-flow-mcp/.venv/bin/google-flow-mcp",
      "args": ["--transport", "stdio"],
      "env": {
        "FLOW_MEDIA_DIR": "/ABSOLUTE/PATH/TO/google-flow-mcp/media"
      }
    }
  }
}
```

Restart `gemini`, run `/mcp` to check that `google-flow` is listed, then ask it to run `flow_browser_login`.

> The Gemini web and mobile apps don't support custom MCP servers like this one, so use Gemini CLI.

---

## 💡 Example prompts

- *"Use `flow_text_to_video` to make a cinematic studio commercial of a matte black sports car under moving neon light, 16:9."*
- *"Make a 9:16 vertical clip of coffee being poured in slow motion with warm morning light."*
- *"Use `flow_frames_to_video` with `/path/to/start.png` as the first frame and `/path/to/end.png` as the last frame for an 8-second transition."*

---

## ⚙️ Configuration

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `FLOW_MEDIA_DIR` | `./media` | Where videos, images and screenshots are saved. |
| `GEMINI_API_KEY` | not set | Turns on the API-only tools. |
| `FLOW_HOST` / `FLOW_PORT` | `127.0.0.1` / `8000` | Address for the HTTP transports. |

## 🛠 Troubleshooting

- **"Still on the Google Flow landing page"**: run `flow_browser_login` and finish signing in.
- **"Could not find the Flow prompt box"**: Flow's website changed. Please open an issue.
- **Chrome says the profile is in use**: close any Chrome window the tool left open, then try again.
- **`not_started` status**: Flow didn't ask to approve a generation. Check the saved `ui_screenshot`.

## 📄 License
MIT
