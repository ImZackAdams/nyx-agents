"""
Model configuration and setup for the Falcon model with CUDA support.
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from typing import Tuple
from dataclasses import dataclass
import os

# Set environment variables for memory management
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:512'

@dataclass
class GenerationConfig:
    """Configuration for text generation parameters"""
    max_new_tokens: int = 100
    temperature: float = 0.7
    top_k: int = 50
    top_p: float = 0.8
    repetition_penalty: float = 2.2

class ModelManager:
    def __init__(self, model_path: str, logger):
        # Build the absolute path to the model
        self.model_path = os.path.abspath(model_path)
        self.logger = logger

        # Verify model path exists
        if not os.path.exists(self.model_path):
            raise RuntimeError(f"Model path does not exist: {self.model_path}")

        # Verify required files exist
        required_files = [
            "config.json",
            "tokenizer.json",
            "tokenizer_config.json",
            "model.safetensors.index.json"
        ]
        for file in required_files:
            if not os.path.exists(os.path.join(self.model_path, file)):
                raise RuntimeError(f"Required file {file} not found in {self.model_path}")

        # Verify CUDA availability
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available. Please check your PyTorch installation.")
            
        self.device = torch.device("cuda")
        torch.cuda.empty_cache()  # Clear CUDA cache before loading
        self.model, self.tokenizer = self._setup_model()
        self.generation_config = GenerationConfig()

    def _setup_model(self) -> Tuple[AutoModelForCausalLM, AutoTokenizer]:
        """Initialize and load the model and tokenizer with CUDA support."""
        self.logger.info(f"Loading tokenizer from local path: {self.model_path}")
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                trust_remote_code=True,
                use_fast=True
            )
            
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token

        except Exception as e:
            self.logger.error(f"Error loading tokenizer: {e}")
            raise RuntimeError(f"Failed to load tokenizer from {self.model_path}: {str(e)}")

        self.logger.info("Loading 4-bit quantized model with CUDA...")
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )
        
        try:
            model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                trust_remote_code=True,
                device_map="balanced",
                quantization_config=quantization_config,
                torch_dtype=torch.float16,
                low_cpu_mem_usage=True,
            ).eval()
            
            # Verify model is on CUDA
            if not next(model.parameters()).is_cuda:
                raise RuntimeError("Model failed to load on CUDA")

        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            raise RuntimeError(f"Failed to load model from {self.model_path}: {str(e)}")

        return model, tokenizer

    def generate(self, context: str) -> str:
        """Generate a response using the model with strict length enforcement."""
        try:
            # Format the prompt properly for Falcon
            formatted_prompt = f"User: {context}\n\nAssistant:"
            
            # Prepare input with truncation
            inputs = self.tokenizer(
                formatted_prompt,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=1024
            ).to(self.device)
            
            # Generate with more restrictive parameters
            with torch.inference_mode(), torch.amp.autocast('cuda'):
                outputs = self.model.generate(
                    inputs["input_ids"],
                    attention_mask=inputs["attention_mask"],
                    max_new_tokens=60,
                    min_new_tokens=20,
                    do_sample=True,
                    temperature=0.7,
                    top_k=30,
                    top_p=0.9,
                    repetition_penalty=1.2,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                    use_cache=True,
                )

            # Clean up the generated text
            generated_text = self.tokenizer.decode(
                outputs[0][inputs["input_ids"].shape[1]:], 
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True
            ).strip()
            
            # Remove any artifacts
            generated_text = generated_text.replace("User:", "").replace("Assistant:", "").strip()
            
            return generated_text

        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            return ""

    def __del__(self):
        """Cleanup when the object is deleted."""
        try:
            torch.cuda.empty_cache()
        except:
            pass