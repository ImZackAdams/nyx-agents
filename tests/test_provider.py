from __future__ import annotations

import unittest

from lilbot.llm.provider import EchoProvider, ProviderConfig, build_provider


class ProviderFactoryTests(unittest.TestCase):
    def test_auto_backend_without_model_uses_echo(self) -> None:
        provider = build_provider(ProviderConfig(backend="auto", model_path=None))
        self.assertIsInstance(provider, EchoProvider)

    def test_echo_backend_uses_echo_provider(self) -> None:
        provider = build_provider(ProviderConfig(backend="echo", model_path=None))
        self.assertIsInstance(provider, EchoProvider)

    def test_hf_backend_requires_model_path(self) -> None:
        with self.assertRaises(RuntimeError):
            build_provider(ProviderConfig(backend="hf", model_path=None))

    def test_echo_provider_supports_callback_streaming(self) -> None:
        provider = EchoProvider()
        chunks: list[str] = []

        result = provider.generate("hello", on_token=chunks.append)

        self.assertEqual(result, "FINAL: (echo provider) No model configured.")
        self.assertEqual("".join(chunks), result)
