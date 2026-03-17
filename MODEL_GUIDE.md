# Lilbot Model Guide

Lilbot is local-first, which means model choice is part of the user experience.

The best model is not the biggest one you can find. The best model is the one that fits your hardware, starts reliably, and answers fast enough that people will actually keep using the tool.

## General Rule

Prefer:

- instruction-tuned local models
- models you can fully load on the hardware you actually have
- 4-bit GPU loading when the machine supports it
- smaller models over unstable giant ones

## Hardware Tiers

## CPU-Only

Use this when:

- there is no compatible GPU
- CUDA is unavailable in the active Python environment
- reliability matters more than speed

Recommended approach:

```bash
lilbot --device cpu
```

Pick a smaller checkpoint and keep expectations realistic. CPU mode works, but cold starts and replies will be slower.

## 8-12 GB NVIDIA GPUs

Use this when:

- you have a consumer GPU with limited VRAM
- you want local inference without dropping to CPU

Recommended approach:

```bash
lilbot --device cuda --quantize-4bit
```

Use a smaller checkpoint or a model known to fit in 4-bit mode. If the model is too large, startup will be frustrating and users will blame the tool.

## 16-24 GB NVIDIA GPUs

This is the sweet spot for a lot of local-first CLI usage.

Recommended approach:

```bash
lilbot --device cuda --quantize-4bit
```

This usually gives the best balance between quality, startup reliability, and response latency.

## Higher-End GPUs

If the user has plenty of VRAM, they have more freedom. The same guidance still applies:

- use the smallest model that meets the quality bar
- keep `doctor` and `init` in the onboarding flow
- test the real startup path, not just the model in isolation

## What Users Need to Know

Every outside user needs clear answers to these questions:

1. Where do I put the model?
2. Which model size fits my hardware?
3. Should I use CPU or CUDA?
4. Do I need `bitsandbytes`?
5. How do I know if my setup is actually healthy?

Lilbot answers those with:

- `lilbot init`
- `lilbot doctor`
- the saved user config at `~/.config/lilbot/config.json`

## Recommended Onboarding Flow

For a fresh machine:

```bash
lilbot init
lilbot doctor
lilbot
```

If CUDA or quantization is missing, fix that before trying to tune prompt behavior or controller logic.

## Practical Advice for Maintainers

- document one recommended model per hardware tier
- test on at least one CPU-only setup and one mid-range CUDA setup
- avoid making the default experience depend on a giant checkpoint
- treat startup reliability as a first-class feature
