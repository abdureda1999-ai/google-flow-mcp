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
| `flow_generate_frame` | Flow sign-in | Generates an image (Nano Banana) with your Flow credits, saves it at full size, and returns the picture so Claude and ChatGPT can show it. Reference images are experimental. |
| `flow_extend_or_edit_video` | Gemini API key | Extends or edits an existing clip. |
| `flow_storyboard_director` | Gemini API key | Turns a brief into a multi-shot storyboard with frame and motion prompts. |

The video and image tools use your Flow sign-in by default. If you set `GEMINI_API_KEY` and pass `use_browser_credits=false`, they use the Gemini API instead. In sign-in mode Flow chooses the image size (for example 768×1376 for 9:16), so `image_size` and `model` only apply with an API key.

### How sign-in mode works
1. Opens Flow in Chrome with a saved profile, so you stay signed in.
2. Creates a new project, types your prompt, and starts the generation.
3. Flow asks before spending credits (for example *"costing 30 credits?"*). The tool clicks **Approve** for that one generation only, never "Always approve", and returns the cost as `credits_cost`. The tools also read your credit balance before and after, and report `credits_used`, `credits_before` and `credits_after`.
4. Waits for the result (up to 10 minutes for video, 7 for images), then saves it to your media folder. Images are saved at full size, not Flow's small preview.

**Leave the Chrome window open until the tool finishes.** Closing it stops the download, but the clip may still finish in your Flow project.

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

It prints a link like `https://something.trycloudflare.com/<secret>/mcp`. In ChatGPT, turn on **Developer mode** (Settings → Apps & Connectors → Advanced), create a connector, paste the link, and choose **No authentication**.

- Ask ChatGPT for an image and it shows the picture in the chat, with a private **download link**. Videos come back with a download link too.
- Keep that Terminal window open while you use ChatGPT. Your computer must stay on.
- The link changes each time you start it, unless you set `FLOW_SECRET` (the secret part stays the same; the tunnel address still changes).
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
| `FLOW_SECRET` | random each start | Secret part of the ChatGPT link. |
| `FLOW_PUBLIC_URL` | not set | Your own public address (for example a named Cloudflare tunnel) so the ChatGPT link stays the same. With it, no quick tunnel is started. |

## 🛠 Troubleshooting

- **"Still on the Google Flow landing page"**: run `flow_browser_login` and finish signing in.
- **"Could not find the Flow prompt box"**: Flow's website changed. Please open an issue.
- **Chrome says the profile is in use**: close any Chrome window the tool left open, then try again.
- **`not_started` status**: Flow didn't ask to approve a generation. Check the saved `ui_screenshot`.

## 📄 License
MIT
