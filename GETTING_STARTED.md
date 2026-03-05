# Getting Started

## Run the CLI
```bash
python3 -m lilbot run
```

## Configure model and device
```bash
export LILBOT_MODEL_PATH=/path/to/model
export LILBOT_DEVICE=cuda
export LILBOT_QUANTIZE_4BIT=1
export LILBOT_MAX_NEW_TOKENS=64
```

Then:
```bash
python3 -m lilbot run
```

## One‑shot prompt
```bash
python3 -m lilbot run --prompt "Hello"
```
