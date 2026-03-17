# Lilbot

Lilbot is a local-first AI command line assistant for developers and system administrators.

It runs a local language model directly inside Python, keeps tool execution under explicit program control, and is built for practical terminal work like inspecting repositories, checking system state, summarizing logs, and explaining shell commands.

Lilbot is not a cloud assistant, not a web app, and not a thin wrapper around a hosted API.

## Quick Start

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[hf,quantization]"
```

Then run the guided setup:

```bash
lilbot init
lilbot doctor
lilbot self-test
lilbot --version
```

When `lilbot init` asks for `Local model path`, enter a real local checkpoint path if you want chat and free-form AI queries to work. If you leave it blank, deterministic commands still work, but `lilbot` and free-form prompts will not.

If `doctor` looks good, start Lilbot:

```bash
lilbot
```

Or ask a one-shot question:

```bash
lilbot "why is my system slow?"
```

## What Lilbot Can Do

- understand repositories
- trace functions through source trees
- inspect system state
- summarize logs
- explain shell commands
- help reason about broken local developer environments

Examples:

```bash
lilbot
lilbot "why is my system slow?"
lilbot repo summarize .
lilbot repo trace-function authenticate_user .
lilbot logs analyze /var/log/syslog
lilbot explain-command "tar -czf backup.tar.gz project/"
```

## First Run Experience

### `lilbot init`

The init wizard saves your defaults to a persistent config file so you do not need to keep passing the same flags:

- model path
- preferred device
- 4-bit quantization preference
- workspace root
- reasoning limits

By default, the config file lives at:

```text
~/.config/lilbot/config.json
```

You can override that path with `LILBOT_CONFIG_PATH`.

### `lilbot doctor`

The doctor command checks the most common setup problems:

- Python executable
- installed packages
- CUDA visibility
- `bitsandbytes` availability
- model discovery
- current workspace and config file state

Use it whenever Lilbot is not behaving the way you expect:

```bash
lilbot doctor
```

### `lilbot self-test`

The self-test command is a quick pass/warn/fail check for the full local setup without loading the full model for inference.

It verifies:

- config loading
- local model discovery
- required Python runtime imports
- CUDA visibility
- one safe deterministic tool execution

Run it like this:

```bash
lilbot self-test
```

## Installation Options

### Option 1: Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[hf,quantization]"
```

### Option 2: Install Directly From GitHub

For users who do not want to clone the repository first:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install "lilbot[hf,quantization] @ git+https://github.com/ImZackAdams/lilbot.git"
```

If your pip version or shell does not like that direct-reference form, use this fallback:

```bash
python -m pip install "git+https://github.com/ImZackAdams/lilbot.git"
python -m pip install torch transformers accelerate
python -m pip install bitsandbytes
```

### Option 3: Conda Environment

If you prefer conda, make sure you create the environment with Python included:

```bash
conda create -n lilbot python=3.12 -y
conda activate lilbot
python -m pip install "lilbot[hf,quantization] @ git+https://github.com/ImZackAdams/lilbot.git"
```

Then continue with:

```bash
lilbot init
lilbot doctor
lilbot self-test
```

### Option 4: CPU-Only Setup

If you do not want GPU dependencies:

```bash
pip install -e ".[hf]"
```

Then prefer CPU mode:

```bash
lilbot --device cpu
```

### Local Model Discovery

Lilbot expects a local Hugging Face checkpoint.

You can provide one explicitly:

```bash
lilbot --model /path/to/local/model
```

Or set it once:

```bash
export LILBOT_MODEL=/path/to/local/model
```

If you keep a checkpoint under `lilbot/models/<model-name>`, Lilbot will auto-discover it.

## Using Lilbot on Another Machine

Lilbot is a normal Python CLI package. On another local machine, the workflow is:

1. create or activate a Python environment
2. install Lilbot into that environment
3. point it at a local model
4. run `lilbot init`
5. run `lilbot doctor`
6. run `lilbot self-test`
7. start using `lilbot`

The `lilbot` command only exists inside the environment where the package was installed. If a user switches environments, they need Lilbot installed there too.

If a user installed Lilbot from GitHub or a package index, commands like `python -m pip install -e ".[hf,quantization]"` only work after cloning the Lilbot repository and `cd`-ing into it. They do not work from an unrelated project directory.

## Choosing a Model for Your Hardware

Lilbot does not rely on a hosted model service, so users need a local checkpoint that fits their machine.

Start here:

- CPU-only machines: use a smaller instruction-tuned model and prefer `--device cpu`
- 8-12 GB NVIDIA GPUs: use `--device cuda --quantize-4bit` and choose a smaller or more aggressively quantized checkpoint
- 16-24 GB NVIDIA GPUs: `--device cuda --quantize-4bit` is usually the best default
- larger GPUs: use whichever local checkpoint gives you the quality/latency tradeoff you want

The detailed setup guide is in [MODEL_GUIDE.md](/home/athena/Desktop/lilbot/MODEL_GUIDE.md).

## Interactive Mode

Start the chat loop:

```bash
lilbot
```

Useful interactive commands:

- `/help`
- `/status`
- `/model`
- `/tools`
- `/clear`
- `/exit`

The startup banner shows:

- active model path
- runtime mode
- workspace root
- config file path

## One-Shot Commands

Use the query mode when you want an answer and then want your shell prompt back:

```bash
lilbot "why is my system slow?"
lilbot --device cuda --quantize-4bit "explain the largest files in this repository"
```

## Deterministic Subcommands

Some workflows are deterministic and do not need the full agent loop:

```bash
lilbot repo summarize .
lilbot repo trace-function authenticate_user .
lilbot logs analyze /var/log/syslog
lilbot explain-command "iptables -A INPUT -p tcp --dport 22 -j ACCEPT"
```

## Configuration

Lilbot reads configuration in this order:

1. command-line flags
2. environment variables
3. user config file
4. built-in defaults

Common settings:

- `LILBOT_MODEL`
- `LILBOT_DEVICE`
- `LILBOT_QUANTIZE_4BIT`
- `LILBOT_WORKSPACE_ROOT`
- `LILBOT_MAX_NEW_TOKENS`
- `LILBOT_MAX_STEPS`
- `LILBOT_CONFIG_PATH`

The sample environment file is in [.env.example](/home/athena/Desktop/lilbot/.env.example).

For support and bug reports, it is helpful to include:

```bash
lilbot --version
lilbot doctor
lilbot self-test
```

## Performance Tips

For larger local checkpoints, the fastest practical path is usually:

```bash
lilbot --device cuda --quantize-4bit
```

If responses feel slow:

- run `lilbot doctor`
- make sure `bitsandbytes` is actually installed
- prefer `--device cuda --quantize-4bit` over `--device auto`
- reduce generation with `--max-new-tokens 128`
- use `/clear` in interactive mode when the session context gets stale

If `--device auto` chooses CUDA and the model still does not fit, Lilbot falls back to CPU during model load.

## Troubleshooting

### No model found

Run:

```bash
lilbot doctor
```

Then either:

- put a local checkpoint under `lilbot/models/`
- run `lilbot init` and save a model path
- pass `--model /path/to/model`
- keep using deterministic commands until a model is configured

### CUDA was requested but is not available

Check that the Python environment you launched Lilbot from can see the GPU:

```bash
python3 -c "import torch; print(torch.cuda.is_available())"
```

If it prints `False`, either fix the environment or use:

```bash
lilbot --device cpu
```

### 4-bit quantization is not activating

Install the optional package:

```bash
python -m pip install bitsandbytes
```

Then verify with:

```bash
lilbot doctor
```

### The first reply is much slower than later replies

That is expected for large local checkpoints. The first request includes model load time. The interactive REPL keeps the model resident after startup, which makes follow-up turns faster.

## Safety Model

Lilbot is local-first, but it is still defensive by default:

- filesystem tools stay inside the configured workspace root
- log analysis is restricted to the workspace or common system log directories
- shell execution runs in restricted, read-oriented mode
- dangerous commands and install-script pipelines are blocked
- the controller enforces a strict `max_steps` limit

The model is used as a reasoning engine. It does not get to act as the operating system.

## Architecture

Lilbot is split into clear layers:

- CLI in `lilbot/cli.py`
- agent wrapper in `lilbot/agent.py`
- controller loop in `lilbot/controller.py`
- prompt construction in `lilbot/prompts.py`
- model backend abstraction in `lilbot/model/`
- tool registry and tool implementations in `lilbot/tools/`
- shell safety policy in `lilbot/safety/`
- observability helpers in `lilbot/utils/`
- session memory in `lilbot/memory/`
- retrieval stubs in `lilbot/retrieval/`

## Development

Run the test suite with:

```bash
python -m unittest discover -s tests -v
```

The current roadmap is in [ROADMAP.md](/home/athena/Desktop/lilbot/ROADMAP.md).
