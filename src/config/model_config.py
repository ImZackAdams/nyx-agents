"""
Model configuration and setup for the fine-tuned Mistral model with CUDA support.
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
        # Convert the passed-in path to an absolute path
        # Typically your Mistral model is in: new_src/ml/text/model_files/mistral_qlora_finetuned
        repo_root = os.path.dirname(os.path.dirname(__file__))  # one level up from config/
        self.model_path = os.path.join(repo_root, "ml", "text", "model_files", "mistral_qlora_finetuned")

        # Or, if you actually want to use the user-provided model_path as a subfolder under repo_root:
        # self.model_path = os.path.join(repo_root, model_path)

        self.logger = logger

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
                local_files_only=True,
                trust_remote_code=True
            )
            
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token

        except Exception as e:
            self.logger.error(f"Error loading tokenizer: {e}")
            raise RuntimeError(f"Failed to load tokenizer from {self.model_path}")

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
                local_files_only=True,
                trust_remote_code=True,
                device_map="balanced",  # Uses all available GPUs
                quantization_config=quantization_config,
                torch_dtype=torch.float16,
                low_cpu_mem_usage=True,
            ).eval()
            
            # Verify model is on CUDA
            if not next(model.parameters()).is_cuda:
                raise RuntimeError("Model failed to load on CUDA")

        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            raise RuntimeError(f"Failed to load model from {self.model_path}")

        return model, tokenizer

    def generate(self, context: str) -> str:
        """Generate a response using the model with strict length enforcement."""
        try:
            # Add explicit length constraint to the system prompt
            system_prefix = "IMPORTANT: Your response MUST be between 80-180 characters. No exceptions."
            context_with_constraint = f"{system_prefix}\n\n{context}"
            
            # Prepare input with truncation
            inputs = self.tokenizer(
                context_with_constraint,
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

            generated_text = self.tokenizer.decode(
                outputs[0][inputs["input_ids"].shape[1]:], 
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True
            ).strip()
            
            # Truncate if still too long
            if len(generated_text) > 180:
                last_break = generated_text[:180].rfind('.')
                if last_break == -1:
                    last_break = generated_text[:180].rfind('!')
                if last_break == -1:
                    last_break = 180
                generated_text = generated_text[:last_break + 1].strip()
            
            # Ensure minimal length
            if len(generated_text) < 80:
                return ""
                
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
