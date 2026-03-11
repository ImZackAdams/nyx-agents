# Getting Started

## 1. Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## 2. Inspect the local setup

```bash
python -m lilbot doctor
python -m lilbot tools
```

## 3. Start the CLI

Interactive chat:

```bash
python -m lilbot
```

One-shot prompt:

```bash
python -m lilbot run "summarize this repo"
```

Inline prompt:

```bash
python -m lilbot "read the README and summarize it"
```

## 4. Use direct chat commands

```text
!ls
!read README.md
!write notes.txt hello
!append notes.txt " world"
!sys
```

## 5. Add a local model

```bash
pip install -e ".[hf]"
export LILBOT_MODEL_PATH=/path/to/local/model
python -m lilbot models
```

Optional 4-bit GPU support:

```bash
pip install -e ".[hf,quantization]"
```

## 6. Run tests

```bash
python -m unittest discover -s tests -v
```
