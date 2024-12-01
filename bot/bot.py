"""
Core bot implementation for Athena, a crypto and finance personality bot.
Handles response generation and management using the pre-trained model.
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from typing import List, Tuple, Optional
import re

from .utilities import log_resource_usage
from .hooks import (
    TextProcessor,  # New import
    analyze_sentiment,
    categorize_prompt,
    prepare_context,
    validate_tweet_length
)

class PersonalityBot:
    def __init__(self, model_path: str, logger):
        """
        Initialize the PersonalityBot.
        Args:
            model_path (str): Path to the pre-trained model directory
            logger: Logger instance for tracking events and errors
        """
        self.model_path = model_path
        self.logger = logger
        self.model, self.tokenizer = self._setup_model()
        
        # Response history management
        self.recent_responses: List[str] = []
        self.max_history: int = 10
        
        # Initialize TextProcessor
        self.text_processor = TextProcessor(max_history=self.max_history)

    def _setup_model(self) -> Tuple[AutoModelForCausalLM, AutoTokenizer]:
        """
        Initialize and load the model and tokenizer with CPU-GPU offloading.
        Returns:
            tuple: (model, tokenizer)
        """
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

    @log_resource_usage
    def _generate_model_response(self, context: str) -> str:
        """
        Generate a response using the pre-trained model.
        Args:
            context (str): Context prompt for the model
        Returns:
            str: Model-generated response
        """
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
                max_new_tokens=100,  # Shorter output for focused tweets
                do_sample=True,
                temperature=0.6,     # Lower temperature for deterministic results
                top_k=30,           # Reduce randomness
                top_p=0.8,          # Narrow probability distribution
                repetition_penalty=2.2,  # Penalize repetitive patterns
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )

            return self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            return ""

    def _store_response(self, response: str) -> None:
        """
        Store the response in history to avoid repetition.
        Args:
            response (str): Generated response to store
        """
        self.recent_responses.append(response)
        if len(self.recent_responses) > self.max_history:
            self.recent_responses.pop(0)

    def _format_response(self, response: str, prompt: str) -> str:
        """
        Format and clean the generated response using TextProcessor.
        Args:
            response (str): Raw response text
            prompt (str): Original prompt for category detection
        Returns:
            str: Formatted and cleaned response
        """
        # Handle duplicate responses before processing
        if response in self.recent_responses:
            response = f"{response} (new thought!)"
        
        # Use TextProcessor for cleaning and styling
        processed_response = self.text_processor.process_tweet(prompt, response)
        
        return processed_response

    def generate_response(self, prompt: str) -> str:
        """
        Generate a Twitter-ready response based on the given prompt.
        Args:
            prompt (str): User input prompt
        Returns:
            str: Generated Twitter-ready response
        Raises:
            ValueError: If prompt is empty or invalid
        """
        if not prompt.strip():
            raise ValueError("Input prompt is empty or invalid.")

        try:
            # Analyze input
            sentiment = analyze_sentiment(prompt, self.logger)
            category = categorize_prompt(prompt)
            
            # Generate context
            context = prepare_context(
                prompt=prompt,
                sentiment=sentiment,
                category=category,
                recent_openers=self.text_processor.recent_openers  # Use TextProcessor's openers
            )
            self.logger.info(f"Generated context: {context}")

            # Generate response
            generated_text = self._generate_model_response(context)
            if not generated_text:
                return "✨ Having a galaxy brain moment... try that again? 💅"
            
            self.logger.info(f"Generated raw response: {generated_text}")

            # Format response using TextProcessor
            response = self._format_response(generated_text, prompt)
            
            # Store if valid
            if validate_tweet_length(response):
                self._store_response(response)
            else:
                self.logger.warning("Generated response failed length validation")
                return "💅 Tea's brewing but not quite ready... spill that question again? ✨"

            return response

        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            return "✨ Oops, the tea got cold! Let's try brewing a fresh cup! 💅"