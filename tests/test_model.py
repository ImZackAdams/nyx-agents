from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from lilbot.model.hf_model import HuggingFaceLocalModel, _render_prompt_with_chat_template


class FakeTokenizerWithTemplate:
    chat_template = "template"

    def __init__(self) -> None:
        self.calls: list[tuple[object, bool, bool]] = []

    def apply_chat_template(
        self,
        messages: object,
        *,
        tokenize: bool,
        add_generation_prompt: bool,
    ) -> str:
        self.calls.append((messages, tokenize, add_generation_prompt))
        return "<|user|>\nwrapped\n<|assistant|>\n"


class FakeTokenizerWithoutTemplate:
    chat_template = None


class ModelHelpersTests(unittest.TestCase):
    def test_missing_model_message_points_to_init(self) -> None:
        with self.assertRaises(RuntimeError) as exc_info:
            HuggingFaceLocalModel(None)

        self.assertIn("Run `lilbot init`", str(exc_info.exception))

    def test_render_prompt_uses_chat_template_when_available(self) -> None:
        tokenizer = FakeTokenizerWithTemplate()

        rendered = _render_prompt_with_chat_template(tokenizer, "why is my system slow?")

        self.assertEqual(rendered, "<|user|>\nwrapped\n<|assistant|>\n")
        self.assertEqual(
            tokenizer.calls,
            [([{"role": "user", "content": "why is my system slow?"}], False, True)],
        )

    def test_render_prompt_leaves_plain_prompt_without_template(self) -> None:
        rendered = _render_prompt_with_chat_template(
            FakeTokenizerWithoutTemplate(),
            "why is my system slow?",
        )

        self.assertEqual(rendered, "why is my system slow?")

    def test_auto_device_can_fallback_to_cpu_on_oom(self) -> None:
        model = object.__new__(HuggingFaceLocalModel)
        model.device_pref = "auto"
        model.device = SimpleNamespace(type="cuda")

        self.assertTrue(model._should_fallback_to_cpu(RuntimeError("CUDA out of memory")))

    def test_explicit_cuda_does_not_silently_fallback(self) -> None:
        model = object.__new__(HuggingFaceLocalModel)
        model.device_pref = "cuda"
        model.device = SimpleNamespace(type="cuda")

        self.assertFalse(model._should_fallback_to_cpu(RuntimeError("CUDA out of memory")))

    def test_quantization_oom_uses_cpu_fallback_for_auto_device(self) -> None:
        class FakeAutoModel:
            @staticmethod
            def from_pretrained(model_name: str, **kwargs):
                del model_name, kwargs
                raise RuntimeError("CUDA out of memory")

        model = object.__new__(HuggingFaceLocalModel)
        model.device_pref = "auto"
        model.device = SimpleNamespace(type="cuda")
        model.model_name = "fake-model"
        model.load_warnings = []
        model.quantization_active = False
        model._load_model_on_cpu = Mock(return_value="cpu-model")

        loaded = model._load_model(FakeAutoModel, {"quantization_config": object()})

        self.assertEqual(loaded, "cpu-model")
        model._load_model_on_cpu.assert_called_once()

    def test_quantization_oom_raises_for_explicit_cuda(self) -> None:
        class FakeAutoModel:
            @staticmethod
            def from_pretrained(model_name: str, **kwargs):
                del model_name, kwargs
                raise RuntimeError("CUDA out of memory")

        model = object.__new__(HuggingFaceLocalModel)
        model.device_pref = "cuda"
        model.device = SimpleNamespace(type="cuda")
        model.model_name = "fake-model"
        model.load_warnings = []
        model.quantization_active = False

        with self.assertRaises(RuntimeError) as exc_info:
            model._load_model(FakeAutoModel, {"quantization_config": object()})

        self.assertIn("4-bit GPU loading ran out of memory", str(exc_info.exception))
