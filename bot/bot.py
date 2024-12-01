import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from nltk.sentiment import SentimentIntensityAnalyzer
import random
from .utilities import log_resource_usage
from .hooks import generate_hook, add_emojis_and_hashtags, clean_response


class PersonalityBot:
    OPENERS = [
        "Hot take!", "Fun fact:", "Did you know?", "Guess what?", 
        "Newsflash!", "Heads up!", "Crypto chat time!", "Just thinking:",
        "Question for you:", "Quick thought:", "So here's the deal:",
        "Word on the street:", "Update:", "Random thought:",
        "Crypto musings:", "Tech vibes:", "Here's a spicy take:",
    ]

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
        self.recent_openers = []  # Track recently used openers
        self.recent_responses = []  # Track recently generated responses
        self.max_history = 10  # Keep up to 10 previous responses

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
        quantization_config = BitsAndBytesConfig(load_in_8bit=True)
        model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            torch_dtype="auto",
            device_map="auto",
            quantization_config=quantization_config,
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
        try:
            sentiment_scores = self.sentiment_analyzer.polarity_scores(text)
            if sentiment_scores["compound"] > 0.05:
                return "positive"
            elif sentiment_scores["compound"] < -0.05:
                return "negative"
            else:
                return "neutral"
        except Exception as e:
            self.logger.error(f"Error analyzing sentiment: {e}")
            return "neutral"

    def _get_random_opener(self) -> str:
        """Select a random opener from the list."""
        opener = random.choice(self.OPENERS)
        while opener in self.recent_openers:
            opener = random.choice(self.OPENERS)
        self.recent_openers.append(opener)
        if len(self.recent_openers) > self.max_history:
            self.recent_openers.pop(0)
        return opener

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
            max_new_tokens=100,  # Shorter output for focused tweets
            do_sample=True,
            temperature=0.6,  # Lower temperature for deterministic results
            top_k=30,         # Reduce randomness
            top_p=0.8,        # Narrow probability distribution
            repetition_penalty=2.2,  # Penalize repetitive patterns
            pad_token_id=self.tokenizer.pad_token_id,
            eos_token_id=self.tokenizer.eos_token_id,
        )

        # Decode and return the model's response
        return self.tokenizer.decode(outputs[0], skip_special_tokens=True)


    def _store_response(self, response: str):
        """Store the response to avoid repetition."""
        self.recent_responses.append(response)
        if len(self.recent_responses) > self.max_history:
            self.recent_responses.pop(0)

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
        self.logger.info(f"Generated context: {context}")

        generated_text = self._generate_model_response(context)
        self.logger.info(f"Generated raw response: {generated_text}")

        response = self._extract_relevant_tweet(prompt, generated_text)
        if len(response) < 20:
            self.logger.warning("Generated response is too short. Falling back to default response.")
            response = "This is intriguing! But I can't make sense of it right now. Care to clarify?"

        response = self._enhance_response(response, category, sentiment)
        self.logger.info(f"Final enhanced response: {response}")
        return response[:280]

    def _extract_relevant_tweet(self, prompt: str, text: str) -> str:
        """Extract the generated tweet corresponding to the input prompt."""
        try:
            # Split and isolate the response part after the context
            tweet = text.split("Tweet:")[-1].strip().split("\n")[0]
            forbidden_phrases = ["In this thread", "1/", "2/", "To be continued", "Next part"]
            if any(phrase in tweet for phrase in forbidden_phrases):
                return "Sorry, this bot only makes standalone tweets!"
            return tweet
        except IndexError:
            return "Sorry, I couldn't generate a response for that."

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
        opener = self._get_random_opener()  # Get a random opener
        base_instruction = (
            "Your name is Athena, a crypto and finance expert with a SUPER sassy, snappy, and spicy personality. "
            "Your tweets are witty, edgy, and sharp. Blend storytelling with sarcasm and clever wordplay. "
            "Focus on engaging crypto enthusiasts and making them laugh while staying informed."
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

        # Emphasize the prompt and make the instruction less dominant
        return f"{opener} {prompt}\n\nInstruction:\n{base_instruction}\n{category_focus}\n{sentiment_tone}\nTweet:"

    def _enhance_response(self, response: str, category: str, sentiment: str) -> str:
        """Enhance the response with hooks, emojis, and hashtags."""
        response = clean_response(response)
        # Ensure response is unique
        if response in self.recent_responses:
            response += " (new thought!)"
        response = response[:280].rsplit(' ', 1)[0] + "…" if len(response) > 280 else response
        if response.endswith(("and", "but", "or", ",")):
            response = response.rsplit(' ', 1)[0].rstrip(",.") + "."
        response = add_emojis_and_hashtags(response, category)
        self._store_response(response)  # Store response to avoid repetition
        return response
