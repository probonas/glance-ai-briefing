# AI News Briefing — Glance Extension

An AI-curated news briefing extension for [Glance](https://github.com/glanceapp/glance).
Fetches headlines from RSS feeds configured in Glance, asks DeepSeek to pick the
3 most significant stories, and serves styled HTML through Glance's extension protocol.

## Quick start

### 1. Install

```bash
pip install .
```

### 2. Set your API key

```bash
export DEEPSEEK_API_KEY=sk-...
```

Get a key at https://platform.deepseek.com/

### 3. Run

```bash
briefing serve
```

The server starts on `http://127.0.0.1:8080`.

### 4. Add to Glance

In your Glance `glance.yml`:

```yaml
- type: extension
  url: http://localhost:8080
  cache: 1s
```

## Docker

```bash
export DEEPSEEK_API_KEY=sk-...
docker compose up -d
```

Mounts `~/glance-config` read-only so the extension discovers RSS feeds
from your live Glance configuration. Feed changes are picked up automatically
on the next refresh cycle — no restart needed.

See `docker-compose.yml` for the volume mount setup.

## Configuration

Optional `briefing.yml` (all values have defaults):

```yaml
glance_config: ~/glance-config/config/home.yml

ai:
  provider: deepseek
  model: deepseek-chat
  api_url: https://api.deepseek.com/v1/chat/completions
  temperature: 0.3
  timeout_seconds: 30

curation:
  story_count: 3
  headlines_per_feed: 4

refresh_interval: 14400  # seconds (4 hours)

server:
  host: 127.0.0.1
  port: 8080
```

Config discovery (first found wins):
1. `--config` CLI flag
2. `./briefing.yml`
3. `~/.config/briefing/briefing.yml`

## CLI

```bash
briefing serve              # Start the HTTP server
briefing serve --port 9090  # Override port
briefing refresh            # Run pipeline once, print HTML, exit
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Widget shows nothing | API key not set | `export DEEPSEEK_API_KEY=sk-...` |
| `api=error:http401` | Wrong or expired API key | Check your DeepSeek key |
| `api=error:timeout` | Network issue or DeepSeek down | Wait for next refresh |
| `No RSS feeds configured` | Glance config not found | Check `glance_config` path in `briefing.yml` |
| Feed changes not picked up | Normal — feeds re-read on next refresh cycle | Wait up to `refresh_interval` seconds |
