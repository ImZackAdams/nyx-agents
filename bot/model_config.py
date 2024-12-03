"""
Model configuration and setup for the Athena bot.
Handles model initialization and generation parameters.
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from typing import Tuple
from dataclasses import dataclass

@dataclass
class GenerationConfig:
    """Configuration for text generation parameters"""
    max_new_tokens: int = 100
    temperature: float = 0.6
    top_k: int = 30
    top_p: float = 0.8
    repetition_penalty: float = 2.2

class ModelManager:
    def __init__(self, model_path: str, logger):
        self.model_path = model_path
        self.logger = logger
        self.model, self.tokenizer = self._setup_model()
        self.generation_config = GenerationConfig()

    def _setup_model(self) -> Tuple[AutoModelForCausalLM, AutoTokenizer]:
        """Initialize and load the model and tokenizer with CPU-GPU offloading."""
        self.logger.info("Loading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(self.model_path)

        self.logger.info("Loading 8-bit quantized model with CPU-GPU offloading...")
        quantization_config = BitsAndBytesConfig(load_in_8bit=True)
        
        try:
            model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                torch_dtype="auto",
                device_map="auto",
                quantization_config=quantization_config,
            ).eval()
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            raise RuntimeError(f"Failed to load model from {self.model_path}")

        return model, tokenizer

    def generate(self, context: str) -> str:
        """Generate a response using the model."""
        try:
            inputs = self.tokenizer(
                context,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=1024
            ).to(self.model.device)
            
            outputs = self.model.generate(
                inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_new_tokens=self.generation_config.max_new_tokens,
                do_sample=True,
                temperature=self.generation_config.temperature,
                top_k=self.generation_config.top_k,
                top_p=self.generation_config.top_p,
                repetition_penalty=self.generation_config.repetition_penalty,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )

            return self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            return ""