# 🎬 Google Flow MCP Server (`google-flow-mcp`)

Connect **Google Flow**'s AI Filmmaking & Creative Studio pipeline (**Gemini Omni 1.2 Flash** video engine + **Nano Banana 2.1** Whisk/reference frame studio + **Gemini 4 Hydrogen** storyboard director) directly to **Claude Desktop**, **Claude Code**, **ChatGPT**, and **Antigravity IDE**.

Stop tab-hopping between ChatGPT, Claude, Whisk, and video generators. Brainstorm a campaign in Claude or ChatGPT and let the assistant generate frames, interpolate keyframes, animate product shots, and extend scenes directly on your machine.

---

## ✨ Features & Tools

| Tool Name | Engine Model | Capability |
| :--- | :--- | :--- |
| `flow_storyboard_director` | `gemini-4-hydrogen` | Turns a creative brief or product photo into a structured multi-shot storyboard with ready-to-run frame & motion prompts. |
| `flow_generate_frame` | `gemini-nano-banana-2.1` / `gemini-3-pro-image` | Generates starting frames, ending keyframes, or **Whisk-style multi-image fusion** (up to 14 reference images for product, lighting, and style consistency) at `1K`, `2K`, or `4K`. |
| `flow_text_to_video` | `gemini-omni-1.2-flash` | Generates `3s`–`15s` commercial & cinematic video clips in `16:9` or `9:16` at `360p`, `720p`, `1080p`, or `4k` with custom camera & sound design. |
| `flow_frames_to_video` | `gemini-omni-1.2-flash` | **First-Frame & Keyframe Interpolation**: Animates a starting image (`first_frame`) or smoothly transitions between `first_frame` and `last_frame` (e.g., Blender 3D previs frames or studio product shots). |
| `flow_reference_to_video` | `gemini-omni-1.2-flash` | **Ingredients / Reference-to-Video (R2V)**: Guides video generation using up to 6 reference images (characters, products, environments) and reference motion videos. |
| `flow_extend_or_edit_video` | `gemini-omni-1.2-flash` | **Scene Builder**: Extends an existing clip by `3s`–`10s` per turn (up to `30s` total) or edits style/lighting/objects turn-by-turn while preserving consistency. |

---

## 🚀 Quick Installation

### Prerequisites
- **Python 3.10+**
- **FFmpeg** installed on your system (`brew install ffmpeg` on macOS)
- A **Google Gemini API Key** ([Get one from Google AI Studio](https://aistudio.google.com/apikey))

### Setup
```bash
git clone https://github.com/YOUR_USERNAME/google-flow-mcp.git
cd google-flow-mcp

# Create virtual environment and install dependencies
python3 -m venv .venv
.venv/bin/pip install -e .
```

---

## 🔌 1. Connect to Claude (Claude Desktop & Claude Code)

### Option A: Claude Code CLI
Run one command in your terminal:
```bash
claude mcp add google-flow \
  -e GEMINI_API_KEY="your_api_key_here" \
  -e FLOW_MEDIA_DIR="$PWD/media" \
  -- "$PWD/.venv/bin/google-flow-mcp" --transport stdio
```

### Option B: Claude Desktop App
Add the following to your `claude_desktop_config.json` (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "google-flow": {
      "command": "/ABSOLUTE/PATH/TO/google-flow-mcp/.venv/bin/google-flow-mcp",
      "args": ["--transport", "stdio"],
      "env": {
        "GEMINI_API_KEY": "your_api_key_here",
        "FLOW_MEDIA_DIR": "/ABSOLUTE/PATH/TO/google-flow-mcp/media"
      }
    }
  }
}
```

---

## 🤖 2. Connect to ChatGPT

You can connect this server to ChatGPT in two ways:

### Option A: ChatGPT MCP Connector (Plus / Pro / Team / Enterprise)
1. Start the server in `sse` or `streamable-http` mode:
   ```bash
   export GEMINI_API_KEY="your_api_key_here"
   .venv/bin/google-flow-mcp --transport sse --port 8000
   ```
2. Expose port `8000` over HTTPS using Cloudflare Tunnel or `ngrok`:
   ```bash
   ngrok http 8000
   ```
3. In ChatGPT **Settings → Connectors / Developer Mode → Add MCP Server**, enter your tunnel URL (e.g., `https://your-tunnel.ngrok-free.app/sse`).

### Option B: ChatGPT Custom GPT Actions (OpenAPI REST Bridge)
1. Start the server in `openapi` mode:
   ```bash
   export GEMINI_API_KEY="your_api_key_here"
   .venv/bin/google-flow-mcp --transport openapi --port 8000
   ```
2. Expose port `8000` via `ngrok http 8000`.
3. In ChatGPT **Create a Custom GPT → Configure → Actions → Import from URL**, paste:
   ```text
   https://your-tunnel.ngrok-free.app/openapi.json
   ```

---

## 💡 Example Prompts (In Claude or ChatGPT)

- **Full Campaign Pipeline:**
  > *"Plan a 3-shot luxury CGI commercial for a matte-black espresso machine using `flow_storyboard_director`. Then generate the 2K starting frame for Shot 1 with `flow_generate_frame` and animate it into a 10-second 1080p commercial clip using `flow_frames_to_video`."*
- **Blender Previs / First-to-Last Frame Transition:**
  > *"Use `flow_frames_to_video` with `/path/to/start_render.png` as `first_frame` and `/path/to/end_render.png` as `last_frame` to create an 8-second dramatic lighting transition."*
- **Scene Extension:**
  > *"Extend the video we just generated (`previous_interaction_id`) by 10 seconds as the camera pulls back through neon-lit rain."*

---

## 📄 License
MIT License
