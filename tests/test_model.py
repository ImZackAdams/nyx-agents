from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from lilbot.model.hf_model import (
    HuggingFaceLocalModel,
    _render_prompt_with_chat_template,
    _select_dtype_kwarg,
)


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

    def test_build_max_memory_map_leaves_gpu_headroom(self) -> None:
        class FakeCuda:
            @staticmethod
            def current_device() -> int:
                return 0

            @staticmethod
            def mem_get_info(device_index: int) -> tuple[int, int]:
                del device_index
                gib = 1024 * 1024 * 1024
                return (12 * gib, 12 * gib)

        model = object.__new__(HuggingFaceLocalModel)
        model.device = SimpleNamespace(type="cuda", index=0)
        model.torch = SimpleNamespace(cuda=FakeCuda())

        with patch.dict("os.environ", {"LILBOT_GPU_HEADROOM_MB": "2048", "LILBOT_CPU_OFFLOAD_GB": "64"}):
            memory_map = model._build_max_memory_map()

        gib = 1024 * 1024 * 1024
        self.assertEqual(memory_map, {0: 10 * gib, "cpu": 64 * gib})

    def test_runtime_summary_mentions_cpu_offload(self) -> None:
        model = object.__new__(HuggingFaceLocalModel)
        model.model_name = "fake-model"
        model.device = SimpleNamespace(type="cuda")
        model.max_new_tokens = 128
        model.temperature = 0.0
        model.quantization_active = True
        model.uses_chat_template = True
        model.model = SimpleNamespace(hf_device_map={"model.layers.0": "cuda:0", "lm_head": "cpu"})

        summary = model._runtime_summary()

        self.assertIn("device=cuda", summary)
        self.assertIn("4-bit", summary)
        self.assertIn("cpu-offload", summary)
        self.assertIn("chat-template", summary)

    def test_select_dtype_kwarg_uses_torch_dtype_for_transformers_4(self) -> None:
        self.assertEqual(_select_dtype_kwarg("4.47.1"), "torch_dtype")

    def test_select_dtype_kwarg_uses_dtype_for_transformers_5(self) -> None:
        self.assertEqual(_select_dtype_kwarg("5.3.0"), "dtype")
