import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from nltk.sentiment import SentimentIntensityAnalyzer
import random
from .utilities import log_resource_usage
from .hooks import generate_hook, add_emojis_and_hashtags, clean_response


class PersonalityBot:
    def __init__(self, model_path, logger):
        """
        Initialize the PersonalityBot.
        Args:
            model_path (str): Path to the pre-trained model directory.
            logger (logging.Logger): Logger for logging events.
        """
        self.model_path = model_path
        self.logger = logger
        self.sentiment_analyzer = SentimentIntensityAnalyzer()  # Initialize VADER sentiment analyzer
        self.model, self.tokenizer = self._setup_model()

    def _setup_model(self):
        """
        Initialize and load the model and tokenizer with CPU-GPU offloading for 8-bit quantized models.
        Returns:
            model (AutoModelForCausalLM): The loaded pre-trained model.
            tokenizer (AutoTokenizer): The tokenizer corresponding to the model.
        """
        print("Loading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(self.model_path)

        print("Loading 8-bit quantized model with CPU-GPU offloading...")
        model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            torch_dtype="auto",  # Automatically select precision
            device_map="auto",   # Automatically map model across CPU and GPU
            load_in_8bit=True,   # Enable 8-bit quantization
            llm_int8_enable_fp32_cpu_offload=True  # Allow CPU offloading for unsupported layers
        ).eval()

        return model, tokenizer

    def _analyze_sentiment(self, text: str) -> str:
        """
        Analyze the sentiment of the given text and return the dominant sentiment.
        Args:
            text (str): Input text.
        Returns:
            str: "positive", "neutral", or "negative" sentiment.
        """
        sentiment_scores = self.sentiment_analyzer.polarity_scores(text)
        if sentiment_scores["compound"] > 0.05:
            return "positive"
        elif sentiment_scores["compound"] < -0.05:
            return "negative"
        else:
            return "neutral"

    def categorize_prompt(self, prompt: str) -> str:
        """
        Categorize the input prompt into predefined categories.
        Args:
            prompt (str): Input prompt.
        Returns:
            str: Category label.
        """
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
        """
        Generate a response using the pre-trained model.
        Args:
            context (str): Context prompt for the model.
        Returns:
            str: Model-generated response.
        """
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
            max_new_tokens=120,  # Increased to allow for more detailed responses
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
        """
        Prepare the context by combining instructions with sentiment and category information.
        Args:
            prompt (str): User prompt.
            sentiment (str): Sentiment tone ("positive", "neutral", "negative").
            category (str): Category for the content.
        Returns:
            str: Prepared context for the model.
        """
        base_instruction = (
            "Your name is Athena, a crypto and finance expert with a sassy, snappy, and spicy personality. "
            "Your tweets are witty, edgy, and sharp. Blend storytelling with sarcasm and clever wordplay. "
            "Focus on engaging crypto enthusiasts and making them laugh while staying informed. "
            "Your Twitter handle is @tballbothq. "
            "Give a snarky disclaimer before offering financial advice."
        )

        sentiment_tone = {
            "positive": "Use an energetic and cheeky tone, brimming with sass and flair.",
            "negative": "Maintain sharp humor with a spicy yet empathetic twist.",
            "neutral": "Be snarky, balanced, and punchy with your humor.",
        }.get(sentiment, "Be snarky, balanced, and punchy with your humor.")

        category_focus = {
            "market_analysis": "Throw in some spicy takes on market trends, technical insights, and trading tips.",
            "tech_discussion": "Dive into blockchain protocols with sass and sharp wit.",
            "defi": "Break down DeFi topics with humor and a touch of snark.",
            "nft": "Get spicy about NFTs, minting drama, and rarity gossip.",
            "culture": "Add wit to community vibes, DAOs, and crypto culture.",
        }.get(category, "Keep it versatile, snappy, and loaded with sass.")

        examples = (
            "Prompt: What's your take on Bitcoin as digital gold?\n"
            "Tweet: Digital gold? Nah, Bitcoin's like the spicy meme stock of the 21st century—volatile, flashy, and always making headlines. 💰🔥\n\n"
            "Prompt: Explain staking in the context of DeFi but make it funny.\n"
            "Tweet: Staking is like a buffet—lock up your coins, pile on the gains, and hope the DeFi chefs don't rug-pull the desserts. 🍰💸\n\n"
        )

        return f"{base_instruction} {sentiment_tone} {category_focus}\n\n{examples}Prompt: {prompt}\nTweet:"

    def generate_response(self, prompt: str) -> str:
        """
        Generate a Twitter-ready response based on the given prompt.
        Args:
            prompt (str): User input prompt.
        Returns:
            str: Generated Twitter-ready response.
        """
        if not prompt.strip():
            raise ValueError("Input prompt is empty or invalid.")

        sentiment = self._analyze_sentiment(prompt)
        category = self.categorize_prompt(prompt)
        context = self._prepare_context(prompt, sentiment, category)
        generated_text = self._generate_model_response(context)

        response = self._extract_relevant_tweet(prompt, generated_text)
        if len(response) < 20:
            self.logger.warning("Generated response is too short. Falling back to default response.")
            response = "This is intriguing! But I can't make sense of it right now. Care to clarify?"

        response = self._enhance_response(response, category, sentiment)
        return response[:280]
    


    def _extract_relevant_tweet(self, prompt: str, text: str) -> str:
        """Extract the generated tweet corresponding to the input prompt."""
        try:
            return text.split(f"Prompt: {prompt}\nTweet:")[-1].strip().split("\n")[0]
        except IndexError:
            return "Sorry, I couldn't generate a response for that."
        


    def _enhance_response(self, response: str, category: str, sentiment: str) -> str:
        """Enhance the response with hooks, emojis, and hashtags."""
        response = clean_response(response)
        if sentiment == "positive" and random.random() <= 0.3:  # Increase hook frequency
            response = f"{generate_hook(category)} {response}".strip()
        response = add_emojis_and_hashtags(response, category)
        response += " 🌶️" if "spicy" in response else ""  # Add signature spice
        return response
