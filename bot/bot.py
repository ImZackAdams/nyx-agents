import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from .utilities import log_resource_usage
from .hooks import generate_hook, add_emojis, add_hashtags, clean_response, generate_engagement_phrase

class PersonalityBot:
    def __init__(self, model_path, logger):
        self.model_path = model_path
        self.logger = logger
        self.model, self.tokenizer = self.setup_model()

    def setup_model(self):
        """Load the model and tokenizer."""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found at {self.model_path}")
        
        tokenizer = AutoTokenizer.from_pretrained(self.model_path, use_fast=True)
        tokenizer.pad_token = tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto"
        ).eval()
        return model, tokenizer

    def categorize_prompt(self, prompt):
        """Categorize input prompt for contextual response generation."""
        categories = {
            "market_analysis": ["price", "market", "chart", "trend", "trading", "volume"],
            "tech_discussion": ["blockchain", "protocol", "code", "network", "scaling"],
            "defi": ["defi", "yield", "farming", "liquidity", "stake"],
            "nft": ["nft", "art", "mint", "opensea", "rarity"],
            "culture": ["community", "dao", "alpha", "fomo"],
        }
        
        prompt_lower = prompt.lower()
        for category, keywords in categories.items():
            if any(keyword in prompt_lower for keyword in keywords):
                return category
        return "general"

    def generate_response(self, prompt):
        """Generate a Twitter-ready response with validation and debugging."""
        if not prompt or not prompt.strip():
            raise ValueError("Input prompt is empty or invalid.")

        self.logger.info("Before inference:")
        log_resource_usage(self.logger)

        # Tokenize input
        try:
            inputs = self.tokenizer(
                prompt,
                return_tensors="pt",
                truncation=True,
                max_length=1024
            )
            self.logger.info(f"Tokenizer output: {inputs}")
        except Exception as e:
            self.logger.error(f"Error during tokenization: {str(e)}")
            raise ValueError("Failed to tokenize the input prompt.")

        # Validate tokenized input
        if "input_ids" not in inputs or len(inputs["input_ids"]) == 0:
            self.logger.error("Tokenizer output is invalid: input_ids are missing or empty.")
            raise ValueError("Tokenizer failed to generate valid input_ids.")

        # Move inputs to the correct device
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        try:
            inputs = inputs.to(device)
        except Exception as e:
            self.logger.error(f"Error transferring inputs to device: {str(e)}")
            raise ValueError("Failed to move inputs to the correct device.")

        # Generate response
        try:
            outputs = self.model.generate(
                inputs["input_ids"],  # Use only input_ids
                max_new_tokens=80,
                temperature=0.7,
                top_k=50,
                top_p=0.9,
                repetition_penalty=1.5,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
        except Exception as e:
            self.logger.error(f"Error during generation: {str(e)}")
            raise ValueError("Failed to generate a response.")

        self.logger.info("After inference:")
        log_resource_usage(self.logger)

        # Ensure the response fits Twitter's character limit
        return response[:280]



