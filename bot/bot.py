import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from .utilities import log_resource_usage
from .hooks import generate_hook, add_emojis, add_hashtags, clean_response


class PersonalityBot:
    def __init__(self, model_path, logger):
        self.model_path = model_path
        self.logger = logger
        self.model, self.tokenizer = self._setup_model()

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

    def _prepare_context(self, prompt: str) -> str:
        """Combine the instruction, examples, and prompt into a context."""
        instruction = (
            "You are a woman named Athena and your twitter handle is @tballbothq. "
            "You are a crypto and finance expert with a sharp sense of humor, blending witty sarcasm with storytelling. "
            "Your goal is to create engaging, funny, and insightful tweets. "
            "Each tweet should be coherent, logical, and provide a clear punchline or takeaway."
        )

        examples = (
            "Prompt: What's your take on Bitcoin as digital gold?\n"
            "Tweet: Bitcoin as digital gold? Nah, it's more like digital real estate in the metaverse—except everyone's still arguing over the property lines. 🚀 #Bitcoin #Crypto\n\n"
            "Prompt: Explain staking in the context of DeFi but make it funny.\n"
            "Tweet: Staking in DeFi is like putting your money on a treadmill—you lock it up, it works out, and somehow you end up with more than just sweaty tokens. Gains on gains! 🏋️‍♂️ #DeFi #Staking\n\n"
        )

        return f"{instruction}\n\n{examples}Prompt: {prompt}\nTweet:"

    def _enhance_response(self, response: str, category: str) -> str:
        """Post-process and enhance the response with hooks, emojis, and hashtags."""
        response = clean_response(response)
        response = f"{generate_hook(category)} {response}".strip()
        response = add_emojis(response, category)
        response = add_hashtags(response, category)
        return response

    def generate_response(self, prompt: str) -> str:
        """Generate a Twitter-ready response based on a given prompt."""
        if not prompt.strip():
            raise ValueError("Input prompt is empty or invalid.")

        self.logger.info("Before inference:")
        log_resource_usage(self.logger)

        context = self._prepare_context(prompt)
        generated_text = self._generate_model_response(context)

        response = self._extract_relevant_tweet(prompt, generated_text)
        if len(response) < 20:
            self.logger.warning("Generated response is too short. Falling back to default response.")
            response = self._get_fallback_response()

        category = self.categorize_prompt(prompt)
        response = self._enhance_response(response, category)

        self.logger.info("After inference and enhancements:")
        log_resource_usage(self.logger)

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
