# Lilbot

Lilbot is a local-first AI-powered CLI assistant for developers and system administrators.

It runs a local language model directly inside Python and treats the model as a reasoning engine that chooses from deterministic tools. There are no cloud APIs, hosted model servers, or remote inference dependencies in the runtime design.

## Features

- local Hugging Face model loading
- a small agent loop with explicit tool use
- deterministic filesystem, shell, repository, and log inspection tools
- a deterministic system inspection snapshot for performance diagnosis
- visible reasoning telemetry with `[THOUGHT]`, `[ACTION]`, and `[OBSERVATION]`
- guardrails around shell execution and filesystem access
- a CLI that supports free-form questions plus repo and log subcommands

## Directory Layout

```text
.
├── cli.py
├── lilbot
│   ├── __init__.py
│   ├── __main__.py
│   ├── agent.py
│   ├── cli.py
│   ├── model.py
│   ├── tools
│   │   ├── __init__.py
│   │   ├── filesystem.py
│   │   ├── logs.py
│   │   ├── repo.py
│   │   └── shell.py
│   └── utils
│       ├── __init__.py
│       ├── config.py
│       └── logging.py
└── tests
```

## Install

Create a virtual environment and install the package:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[hf,quantization]"
```

Lilbot uses Hugging Face `BitsAndBytesConfig` with `bitsandbytes` for 4-bit GPU loading.
That is the recommended setup for the bundled Falcon 10B checkpoint.

If you need a non-quantized install instead:

```bash
pip install -e ".[hf]"
```

## Configure A Local Model

Point Lilbot at a local Hugging Face model directory:

```bash
export LILBOT_MODEL_PATH=/path/to/local/model
```

If you keep the model under `lilbot/models/<model-name>`, Lilbot will auto-discover it and use that path by default.

Compatible instruct models include local Falcon, Qwen, and Mistral checkpoints as long as the directory contains the tokenizer and model weights.

For the bundled Falcon model, a practical local setup is:

```bash
export LILBOT_DEVICE=cuda
export LILBOT_QUANTIZE_4BIT=1
python cli.py "why is my system slow?"
```

At startup Lilbot now prints the model runtime summary and any quantization warnings to stderr, so you can confirm whether `bitsandbytes` 4-bit loading actually activated.

## Usage

Free-form reasoning with tools:

```bash
python cli.py "why is my system slow?"
python -m lilbot "explain the largest files in this repository"
```

Repository helpers:

```bash
python cli.py repo summarize .
python cli.py repo trace-function authenticate_user .
```

Log analysis:

```bash
python cli.py logs analyze /var/log/syslog
```

Command explanation:

```bash
python cli.py explain-command "iptables -A INPUT -p tcp --dport 22 -j ACCEPT"
```

## Safety Model

- filesystem reads stay inside `LILBOT_WORKSPACE_ROOT` or the current working directory
- log analysis is limited to the workspace or common system log directories
- shell execution is read-only, allowlisted, and rejects dangerous metacharacters
- system performance diagnosis can use `inspect_system`, which avoids shell pipelines entirely
- the agent stops after `LILBOT_MAX_STEPS`

## Development

Run the tests with:

```bash
python -m unittest discover -s tests -v
```
