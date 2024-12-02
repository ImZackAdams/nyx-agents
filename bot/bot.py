"""
Core bot implementation for Athena, a crypto and finance personality bot.
Handles response generation and management using the pre-trained model.
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from typing import List, Tuple, Dict, Optional
import re
import random
from dataclasses import dataclass

from .text_processor import (
    TextProcessor,
    StyleConfig,
    Category,
    ContentAnalyzer
)
from .utilities import log_resource_usage

@dataclass
class GenerationConfig:
    """Configuration for text generation parameters"""
    max_new_tokens: int = 100
    temperature: float = 0.6
    top_k: int = 30
    top_p: float = 0.8
    repetition_penalty: float = 2.2

class PersonalityBot:
    def __init__(self, model_path: str, logger, style_config: Optional[StyleConfig] = None):
        """
        Initialize the PersonalityBot.
        Args:
            model_path (str): Path to the pre-trained model directory
            logger: Logger instance for tracking events and errors
            style_config: Optional custom style configuration
        """
        self.model_path = model_path
        self.logger = logger
        self.model, self.tokenizer = self._setup_model()
        
        # Response history management
        self.max_history: int = 10
        self.recent_responses: List[str] = []
        
        # Initialize processors
        self.style_config = style_config or StyleConfig.default()
        self.text_processor = TextProcessor(self.style_config, self.max_history)
        self.content_analyzer = ContentAnalyzer()
        
        # Default generation config
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

    @log_resource_usage
    def _generate_model_response(self, context: str) -> str:
        """Generate a response using the pre-trained model."""
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

    def _store_response(self, response: str) -> None:
        """Store the response in history to avoid repetition."""
        self.recent_responses.append(response)
        if len(self.recent_responses) > self.max_history:
            self.recent_responses.pop(0)

    def _prepare_context(self, prompt: str, sentiment: str, category: Category) -> str:
        """Prepare the context for response generation."""
        opener = random.choice([op for op in self.style_config.openers 
                              if op not in self.text_processor.recent_openers])
        
        base_instruction = (
            "You are Athena, a sassy, spicy, crypto and finance expert with major attitude and wit. "
            "Create ONE spicy, short, complete tweet (max 240 chars) that serves tea and drops knowledge."
            "You do not give investment advice."
            "Do not spread misinofrmation and be factual unless making a joke."
            "You are a Saggitaruis and were born on Thanksgiving, november 28th."
        )

        sentiment_guidance = {
            "positive": "Serve the tea with extra sparkle! Make your excitement contagious!",
            "negative": "Keep the sass while serving truth. Balance criticism with wit.",
            "neutral": "Facts + Fashion = Your Tweet! Stay objective but make it pop."
        }.get(sentiment, "Balance insight with sass!")

        category_guidance = {
            Category.MARKET_ANALYSIS: "Spill market tea with data and drama!",
            Category.TECH_DISCUSSION: "Tech tea, bestie style!",
            Category.DEFI: "DeFi drama with receipts!",
            Category.NFT: "Rate these NFTs like Met Gala fits!",
            Category.CULTURE: "Community tea time!",
            Category.GENERAL: "Crypto gossip with facts!"
        }.get(category, "Serve that crypto tea with style!")

        return f"{opener} {prompt}\n\n{base_instruction}\n{category_guidance}\n{sentiment_guidance}\nTweet:"

    def _validate_tweet_length(self, tweet: str) -> bool:
        """Check if tweet meets length requirements."""
        clean_length = len(tweet.strip())
        return 50 <= clean_length <= 240

    def generate_response(self, prompt: str) -> str:
        """Generate a Twitter-ready response based on the given prompt."""
        if not prompt.strip():
            raise ValueError("Input prompt is empty or invalid.")

        try:
            # Analyze input
            sentiment = self.content_analyzer.analyze_sentiment(prompt)
            category = self.content_analyzer.categorize_prompt(prompt)
            
            # Generate context
            context = self._prepare_context(prompt, sentiment, category)
            self.logger.info(f"Generated context: {context}")

            # Generate response
            generated_text = self._generate_model_response(context)
            if not generated_text:
                return "✨ Having a galaxy brain moment... try that again? 💅"
            
            self.logger.info(f"Generated raw response: {generated_text}")

            # Format response using TextProcessor
            response = self.text_processor.process_tweet(prompt, generated_text)
            
            # Validate and store
            if self._validate_tweet_length(response):
                self._store_response(response)
                return response
            else:
                self.logger.warning("Generated response failed length validation")
                return "💅 Tea's brewing but not quite ready... spill that question again? ✨"

        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            return "✨ Oops, the tea got cold! Let's try brewing a fresh cup! 💅"