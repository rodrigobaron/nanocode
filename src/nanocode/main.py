#!/usr/bin/env python3
"""nanocode - minimal claude code alternative"""

import argparse
import glob as globlib
import json 
import os 
import re
import subprocess
import aiohttp


PROVIDERS = {
    "anthropic": {
        "url": "https://api.anthropic.com/v1/messages",
        "default_model": "claude-opus-4-5",
        "env_key": "ANTHROPIC_API_KEY",
    },
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "default_model": "minimax/minimax-m2.1",
        "env_key": "OPENROUTER_API_KEY",
    },
}

# ANSI colors
RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
BLUE, CYAN, GREEN, YELLOW, RED = "\033[34m", "\033[36m", "\033[32m", "\033[33m", "\033[31m"


# --- Tool implementations ---


def read(args):
    lines = open(args["path"]).readlines()
    offset = args.get("offset", 0)
    limit = args.get("limit", len(lines))
    selected = lines[offset : offset + limit]
    return "".join(f"{offset + idx + 1:4}| {line}" for idx, line in enumerate(selected))


def write(args):
    with open(args["path"], "w") as f:
        f.write(args["content"])
    return "ok"


def edit(args):
    text = open(args["path"]).read()
    old, new = args["old"], args["new"]
    if old not in text:
        return "error: old_string not found"
    count = text.count(old)
    if not args.get("all") and count > 1:
        return f"error: old_string appears {count} times, must be unique (use all=true)"
    replacement = text.replace(old, new) if args.get("all") else text.replace(old, new, 1)
    with open(args["path"], "w") as f:
        f.write(replacement)
    return "ok"


def glob(args):
    pattern = (args.get("path", ".") + "/" + args["pat"]).replace("//", "/")
    files = globlib.glob(pattern, recursive=True)
    files = sorted(files, key=lambda f: os.path.getmtime(f) if os.path.isfile(f) else 0, reverse=True)
    return "\n".join(files) or "none"


def grep(args):
    pattern = re.compile(args["pat"])
    hits = []
    for filepath in globlib.glob(args.get("path", ".") + "/**", recursive=True):
        try:
            for line_num, line in enumerate(open(filepath), 1):
                if pattern.search(line):
                    hits.append(f"{filepath}:{line_num}:{line.rstrip()}")
        except Exception:
            pass
    return "\n".join(hits[:50]) or "none"


def bash(args):
    result = subprocess.run(args["cmd"], shell=True, capture_output=True, text=True, timeout=30)
    return (result.stdout + result.stderr).strip() or "(empty)"


# --- Tool definitions: (description, schema, function) ---

TOOLS = {
    "read": ("Read file with line numbers (file path, not directory)", {"path": "string", "offset": "number?", "limit": "number?"}, read),
    "write": ("Write content to file", {"path": "string", "content": "string"}, write),
    "edit": ("Replace old with new in file (old must be unique unless all=true)", {"path": "string", "old": "string", "new": "string", "all": "boolean?"}, edit),
    "glob": ("Find files by pattern, sorted by mtime", {"pat": "string", "path": "string?"}, glob),
    "grep": ("Search files for regex pattern", {"pat": "string", "path": "string?"}, grep),
    "bash": ("Run shell command", {"cmd": "string"}, bash),
}


def run_tool(name, args):
    try:
        return TOOLS[name][2](args)
    except Exception as err:
        return f"error: {err}"


def make_anthropic_schema():
    result = []
    for name, (description, params, _fn) in TOOLS.items():
        properties, required = {}, []
        for param_name, param_type in params.items():
            is_optional = param_type.endswith("?")
            base_type = param_type.rstrip("?")
            properties[param_name] = {"type": "integer" if base_type == "number" else base_type}
            if not is_optional:
                required.append(param_name)
        result.append({"name": name, "description": description, "input_schema": {"type": "object", "properties": properties, "required": required}})
    return result


def make_openai_schema():
    result = []
    for name, (description, params, _fn) in TOOLS.items():
        properties, required = {}, []
        for param_name, param_type in params.items():
            is_optional = param_type.endswith("?")
            base_type = param_type.rstrip("?")
            properties[param_name] = {"type": "integer" if base_type == "number" else base_type}
            if not is_optional:
                required.append(param_name)
        result.append({"type": "function", "function": {"name": name, "description": description, "parameters": {"type": "object", "properties": properties, "required": required}}})
    return result


async def call_anthropic(session, messages, system_prompt, model, api_key, thinking=False):
    body = {
        "model": model,
        "max_tokens": 16000 if thinking else 8192,
        "system": system_prompt,
        "messages": messages,
        "tools": make_anthropic_schema(),
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    if thinking:
        body["thinking"] = {"type": "enabled", "budget_tokens": 10000}
        headers["anthropic-beta"] = "interleaved-thinking-2025-05-14"

    async with session.post(PROVIDERS["anthropic"]["url"], json=body, headers=headers) as resp:
        return await resp.json()


async def call_openrouter(session, messages, system_prompt, model, api_key, thinking=False):
    # Convert Anthropic message format to OpenAI format
    openai_messages = [{"role": "system", "content": system_prompt}]
    for msg in messages:
        if msg["role"] == "user":
            if isinstance(msg["content"], str):
                openai_messages.append({"role": "user", "content": msg["content"]})
            elif isinstance(msg["content"], list):
                # Tool results
                for item in msg["content"]:
                    if item.get("type") == "tool_result":
                        openai_messages.append({"role": "tool", "tool_call_id": item["tool_use_id"], "content": item["content"]})
                    else:
                        openai_messages.append({"role": "user", "content": str(item)})
        elif msg["role"] == "assistant":
            if isinstance(msg["content"], list):
                text_parts = [b["text"] for b in msg["content"] if b.get("type") == "text"]
                tool_calls = [{"id": b["id"], "type": "function", "function": {"name": b["name"], "arguments": json.dumps(b["input"])}} for b in msg["content"] if b.get("type") == "tool_use"]
                openai_messages.append({"role": "assistant", "content": " ".join(text_parts) or None, **({"tool_calls": tool_calls} if tool_calls else {})})
            else:
                openai_messages.append({"role": "assistant", "content": msg["content"]})

    body = {"model": model, "max_tokens": 16000 if thinking else 8192, "messages": openai_messages, "tools": make_openai_schema()}
    if thinking:
        body["include_reasoning"] = True
        # body["reasoning_split"] = True

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    async with session.post(PROVIDERS["openrouter"]["url"], json=body, headers=headers) as resp:
        data = await resp.json()

    # Convert OpenAI response to Anthropic format
    choice = data["choices"][0]
    content_blocks = []
    # Handle reasoning/thinking from OpenRouter
    if choice["message"].get("reasoning"):
        content_blocks.append({"type": "thinking", "thinking": choice["message"]["reasoning"]})
    if choice["message"].get("content"):
        content_blocks.append({"type": "text", "text": choice["message"]["content"]})
    for tc in choice["message"].get("tool_calls", []):
        content_blocks.append({"type": "tool_use", "id": tc["id"], "name": tc["function"]["name"], "input": json.loads(tc["function"]["arguments"])})
    return {"content": content_blocks, "stop_reason": "tool_use" if choice["message"].get("tool_calls") else "end_turn"}


async def call_api(session, messages, system_prompt, provider, model, api_key, thinking=False):
    if provider == "anthropic":
        return await call_anthropic(session, messages, system_prompt, model, api_key, thinking)
    else:
        return await call_openrouter(session, messages, system_prompt, model, api_key, thinking)


def separator():
    return f"{DIM}{'─' * min(os.get_terminal_size().columns, 80)}{RESET}"


def render_markdown(text):
    return re.sub(r"\*\*(.+?)\*\*", f"{BOLD}\\1{RESET}", text)


def main():
    parser = argparse.ArgumentParser(description="nanocode - minimal claude code alternative")
    parser.add_argument("--provider", "-p", choices=["anthropic", "openrouter"], default="anthropic", help="API provider")
    parser.add_argument("--model", "-m", help="Model to use (defaults: anthropic=claude-opus-4-5, openrouter=minimax/minimax-m1)")
    parser.add_argument("--no-think", action="store_true", help="Disable extended thinking")
    args = parser.parse_args()

    provider_config = PROVIDERS[args.provider]
    model = args.model or provider_config["default_model"]
    api_key = os.environ.get(provider_config["env_key"], "")

    if not api_key:
        print(f"{RED}Error: {provider_config['env_key']} not set{RESET}")
        return

    thinking = not args.no_think
    thinking_indicator = " +thinking" if thinking else ""
    print(f"{BOLD}nanocode{RESET} | {DIM}{args.provider}:{model}{thinking_indicator} | {os.getcwd()}{RESET}\n")
    messages = []
    system_prompt = f"Concise coding assistant. cwd: {os.getcwd()}"
    
    # Load AGENT.md if exists
    agent_file = os.path.join(os.getcwd(), "AGENT.md")
    if os.path.exists(agent_file):
        agent_content = open(agent_file).read().strip()
        system_prompt += f"\n\n<agent_instructions>\n{agent_content}\n</agent_instructions>"
        print(f"{DIM}Loaded AGENT.md{RESET}\n")

    import asyncio
    async def run():
        async with aiohttp.ClientSession() as session:
            while True:
                try:
                    print(separator())
                    user_input = await asyncio.to_thread(input, f"{BOLD}{BLUE}❯{RESET} ")
                    user_input = user_input.strip()
                    print(separator())
                    if not user_input:
                        continue
                    if user_input in ("/q", "exit"):
                        break
                    if user_input == "/c":
                        messages.clear()
                        print(f"{GREEN}⏺ Cleared conversation{RESET}")
                        continue

                    messages.append({"role": "user", "content": user_input})

                    # agentic loop: keep calling API until no more tool calls
                    while True:
                        response = await call_api(session, messages, system_prompt, args.provider, model, api_key, thinking)
                        content_blocks = response.get("content", [])
                        tool_results = []

                        for block in content_blocks:
                            if block["type"] == "thinking":
                                thinking_preview = block["thinking"].replace("\n", " ")[:100]
                                if len(block["thinking"]) > 100:
                                    thinking_preview += "..."
                                print(f"\n{DIM}💭 {thinking_preview}{RESET}")

                            if block["type"] == "text" and len(block['text'].strip()) > 0:
                                print(f"\n{CYAN}⏺{RESET} {render_markdown(block['text'])}")

                            if block["type"] == "tool_use":
                                tool_name = block["name"]
                                tool_args = block["input"]
                                arg_preview = str(list(tool_args.values())[0])[:50] if tool_args else ""
                                print(f"\n{GREEN}⏺ {tool_name.capitalize()}{RESET}({DIM}{arg_preview}{RESET})")

                                result = await asyncio.to_thread(run_tool, tool_name, tool_args)
                                result_lines = result.split("\n")
                                preview = result_lines[0][:60]
                                if len(result_lines) > 1:
                                    preview += f" ... +{len(result_lines) - 1} lines"
                                elif len(result_lines[0]) > 60:
                                    preview += "..."
                                print(f"  {DIM}⎿  {preview}{RESET}")

                                tool_results.append({"type": "tool_result", "tool_use_id": block["id"], "content": result})

                        messages.append({"role": "assistant", "content": content_blocks})

                        if not tool_results:
                            break
                        messages.append({"role": "user", "content": tool_results})

                    print()

                except (KeyboardInterrupt, EOFError):
                    break
                except Exception as err:
                    print(f"{RED}⏺ Error: {err}{RESET}")

    asyncio.run(run())


if __name__ == "__main__":
    main()
