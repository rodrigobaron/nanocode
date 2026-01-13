# nanocode

**nanocode** is a minimal CLI coding assistant that serves as a lightweight alternative to Claude Code.

## What it does

- Interactive AI coding assistant in the terminal
- Supports **Anthropic (Claude)** and **OpenRouter** APIs
- Provides 6 tools the AI can use: `read`, `write`, `edit`, `glob`, `grep`, `bash`

## Key features

- Reads/writes/edits files
- Searches code with regex
- Runs shell commands
- Extended thinking mode (when available)
- Markdown rendering with ANSI colors

## Usage

```bash
./nanocode.py                    # Uses Anthropic (Claude)
./nanocode.py -p openrouter      # Uses OpenRouter
./nanocode.py -m claude-sonnet-4 # Specify model
./nanocode.py --no-think         # Disable extended thinking
```

## Commands

- `/q` or `exit` - Quit
- `/c` - Clear conversation

## Setup

Requires one of these environment variables:
- `ANTHROPIC_API_KEY` - for Anthropic/Claude
- `OPENROUTER_API_KEY` - for OpenRouter

## License

MIT License
