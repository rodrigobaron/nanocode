# nanocode

**nanocode** is a minimal CLI coding assistant that serves as a lightweight alternative to Claude Code.

## What it does

- Interactive AI coding assistant in the terminal
- Supports **Anthropic (Claude)** and **OpenRouter** APIs
- Provides 6 tools the AI can use: `read`, `write`, `edit`, `glob`, `grep`, `bash`
- **Skills system** for task-specific AI behavior

## Key features

- Reads/writes/edits files
- Searches code with regex
- Runs shell commands
- Extended thinking mode (when available)
- Markdown rendering with ANSI colors
- Skills for specialized tasks (algorithmic art, code review, bash scripts)

## Usage

```bash
./nanocode.py                    # Uses Anthropic (Claude)
./nanocode.py -p openrouter      # Uses OpenRouter
./nanocode.py -m claude-sonnet-4 # Specify model
./nanocode.py --no-think         # Disable extended thinking
./nanocode.py -s myskills        # Custom skills directory
```

## Commands

- `/q` or `exit` - Quit
- `/c` - Clear conversation
- `/skills` - List available skills

## Skills

Skills provide specialized AI behavior for specific tasks. Create `.md` files in the `skills/` directory:

```markdown
---
name: myskill
description: What this skill does
license: Optional license
---

Skill-specific instructions here...
```

### Using Skills

Activate a skill with `/skillname <prompt>`:

```bash
/algorithmic-art create a flow field with particles
/code-review review my code for security issues
/bash-script create a backup script
```

Only one skill can be active per conversation.

## Setup

Requires one of these environment variables:
- `ANTHROPIC_API_KEY` - for Anthropic/Claude
- `OPENROUTER_API_KEY` - for OpenRouter

## License

MIT License
