You are developer of nanocode, a minimal CLI coding assistant that serves as a lightweight alternative to Claude Code.  
- Interactive AI coding assistant in the terminal
- Supports **Anthropic (Claude)** and **OpenRouter** APIs
- Provides 6 tools the AI can use: `read`, `write`, `edit`, `glob`, `grep`, `bash`

# Project Structure

```
.
├── src
│   └── nanocode
│       ├── __init__.py
│       ├── __main__.py
│       └── main.py
├── .gitignore
├── AGENT.md
├── pyproject.toml
├── README.md
└── uv.lock
```

# Instructions

* Write right and simple code which solve the user requests.
* If you are unsure, ask for clarification.
* Update DEVLOG.md to keep track the features/bugfixes implemented
