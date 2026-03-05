from __future__ import annotations

from typing import Protocol, Optional

import os


class LLMProvider(Protocol):
    def generate(self, prompt: str) -> str:
        ...


class EchoProvider:
    """Placeholder provider for local testing."""

    def generate(self, prompt: str) -> str:
        return "FINAL: (echo provider) No model configured."


class LocalHFProvider:
    """
    Local HuggingFace model provider.
    Expects a local model path containing tokenizer + model files.
    """

    def __init__(self, model_path: str, max_new_tokens: int = 200):
        self.model_path = os.path.abspath(model_path)
        self.max_new_tokens = max_new_tokens

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model path not found: {self.model_path}")

        # Lazy import to keep base deps minimal unless used.
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM

        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            trust_remote_code=True,
            torch_dtype=torch.float16 if torch.cuda.is_available() else None,
        )
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device).eval()

    def generate(self, prompt: str) -> str:
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=2048,
        ).to(self.device)

        with self.torch.inference_mode():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                repetition_penalty=1.1,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        generated = self.tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        ).strip()

        # Ensure required format if model doesn't follow instructions
        if not generated.startswith(("FINAL:", "TOOL:")):
            generated = f"FINAL: {generated}"
        return generated
