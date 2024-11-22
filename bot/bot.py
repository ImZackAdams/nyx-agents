import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from .utilities import log_resource_usage
from nltk.sentiment import SentimentIntensityAnalyzer
import random
from .hooks import generate_hook, add_emojis_and_hashtags, clean_response


class PersonalityBot:
    def __init__(self, model_path, logger):
        self.model_path = model_path
        self.logger = logger
        self.model, self.tokenizer = self._setup_model()
        self.sentiment_analyzer = SentimentIntensityAnalyzer()  # Initialize VADER

    def _setup_model(self):
        """Initialize and load the model and tokenizer."""
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model not found at {self.model_path}")

        tokenizer = AutoTokenizer.from_pretrained(self.model_path, use_fast=True)
        tokenizer.pad_token = tokenizer.pad_token or tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto"
        ).eval()

        return model, tokenizer
    
    def _analyze_sentiment(self, text: str) -> str:
        """Analyze the sentiment of a given text and return the dominant sentiment."""
        sentiment_scores = self.sentiment_analyzer.polarity_scores(text)
       # self.logger.info(f"Sentiment scores: {sentiment_scores}")

        if sentiment_scores["compound"] > 0.05:
            return "positive"
        elif sentiment_scores["compound"] < -0.05:
            return "negative"
        else:
            return "neutral"

    def categorize_prompt(self, prompt: str) -> str:
        """Categorize the input prompt into predefined categories."""
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

    def _generate_model_response(self, context: str) -> str:
        """Generate a response using the loaded model."""
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        inputs = self.tokenizer(
            context,
            return_tensors="pt",
            truncation=True,
            padding=True,
            max_length=1024
        ).to(device)

        outputs = self.model.generate(
            inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            max_new_tokens=80,
            do_sample=True,
            temperature=0.7,
            top_k=50,
            top_p=0.9,
            repetition_penalty=1.5,
            pad_token_id=self.tokenizer.pad_token_id,
            eos_token_id=self.tokenizer.eos_token_id,
        )

        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)

    def _prepare_context(self, prompt: str, sentiment: str = "neutral", category: str = "general") -> str:
        """Modify instructions based on sentiment and category to guide the model."""
        base_instruction = (
            "You are Athena, a crypto and finance expert. Your tweets are witty, insightful, and funny."
            "Blend storytelling and sarcasm into concise posts. Focus on engaging crypto enthusiasts."
            "Your twitter handle is @tballbothq."
            "Give a disclaimer before offering financial advice."
        )

        sentiment_tone = {
            "positive": "Use an energetic and witty tone, with plenty of positivity.",
            "negative": "Maintain humor in a less sarcastic and more empathetic manner.",
            "neutral": "Use a balanced tone with clever humor.",
        }.get(sentiment, "Use a balanced tone with clever humor.")

        category_focus = {
            "market_analysis": "Focus on market trends, technical insights, and trading tips.",
            "tech_discussion": "Discuss blockchain protocols, code, and scaling challenges.",
            "defi": "Explain DeFi concepts like yield farming, staking, and TVL trends.",
            "nft": "Talk about NFTs, rarity traits, and minting news.",
            "culture": "Highlight community vibes, DAOs, and crypto ethos.",
        }.get(category, "Keep it general and versatile for any crypto topic.")

        examples = (
            "Prompt: What's your take on Bitcoin as digital gold?\n"
            "Tweet: Bitcoin as digital gold? Nah, it's more like digital real estate in the metaverse—except everyone's still arguing over the property lines. 🚀\n\n"
            "Prompt: Explain staking in the context of DeFi but make it funny.\n"
            "Tweet: Staking in DeFi is like putting your money on a treadmill—you lock it up, it works out, and somehow you end up with more. Gains on gains! 🏋️‍♂️\n\n"
        )

        return f"{base_instruction} {sentiment_tone} {category_focus}\n\n{examples}Prompt: {prompt}\nTweet:"



    def _enhance_response(self, response: str, category: str, sentiment: str) -> str:
        """Post-process and enhance the response with hooks, emojis, and hashtags."""
        response = clean_response(response)
        if sentiment == "positive" and random.random() <= 0.1:  # Hooks 10% chance for positive sentiment
            response = f"{generate_hook(category)} {response}".strip()
        response = add_emojis_and_hashtags(response, category)

        return response

    def generate_response(self, prompt: str) -> str:
            """Generate a Twitter-ready response based on a given prompt."""
            if not prompt.strip():
                raise ValueError("Input prompt is empty or invalid.")

            # self.logger.info("Before inference:")
            # log_resource_usage(self.logger)

            # Analyze sentiment and categorize the prompt
            sentiment = self._analyze_sentiment(prompt)  # Analyze sentiment
            category = self.categorize_prompt(prompt)  # Categorize prompt

            # Prepare context for the model
            context = self._prepare_context(prompt, sentiment, category)
            generated_text = self._generate_model_response(context)

            # Extract relevant response
            response = self._extract_relevant_tweet(prompt, generated_text)
            if len(response) < 20:
                self.logger.warning("Generated response is too short. Falling back to default response.")
                response = self._get_fallback_response(prompt)

            # Enhance response based on category and sentiment
            response = self._enhance_response(response, category, sentiment)

            # self.logger.info("After inference and enhancements:")
            # log_resource_usage(self.logger)

            return response[:280]
            



    def _extract_relevant_tweet(self, prompt: str, text: str) -> str:
        """Extract the generated tweet corresponding to the input prompt."""
        try:
            return text.split(f"Prompt: {prompt}\nTweet:")[-1].strip().split("\n")[0]
        except IndexError:
            return "Sorry, I couldn't generate a response for that."

    def _get_fallback_response(self) -> str:
        """Provide a default fallback response."""
        return "This is intriguing! But I can't make sense of it right now. Care to clarify?"
