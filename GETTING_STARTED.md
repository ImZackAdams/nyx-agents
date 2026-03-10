# Getting Started

Need the full manual after this? Read [HOWTOUSE.md](HOWTOUSE.md).

## 1. Install the base CLI

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

This installs the deterministic CLI experience without heavy model dependencies.

## 2. Prepare local state

```bash
python -m lilbot init
python -m lilbot doctor
```

`init` creates Lilbot's user data directories and copies `.env.example` to `.env` when a template exists in the current directory.

`doctor` shows:

- workspace root
- memory paths
- configured model path status
- dependency checks
- next steps

## 3. Try the no-model workflows

```bash
python -m lilbot "what files are in this project?"
python -m lilbot note "buy milk"
python -m lilbot "what notes do I have?"
python -m lilbot "my name is Zack"
python -m lilbot "what is my name?"
```

## 4. Add local-model support when you want it

```bash
pip install -e ".[hf]"
```

Optional 4-bit GPU support:

```bash
pip install -e ".[hf,quantization]"
```

Then point Lilbot at a local model:

```bash
export LILBOT_MODEL_PATH=/path/to/local/model
```

Or place one in Lilbot's default app-data model directory and rerun `python -m lilbot doctor`.

## 5. Start the CLI

```bash
python -m lilbot
```

## 6. Run the regression suite

```bash
python -m unittest discover -s tests -v
```
