# Lilbot

A minimal local‑LLM CLI for running a model on your machine.

## Run
```bash
python3 -m lilbot run
```

Optional environment defaults:
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

## Notes
- The default model path is `lilbot/models/falcon3_10b_instruct` if it exists.
- Use `--device cpu` if CUDA isn’t available.

## License
MIT. See `LICENSE`.
