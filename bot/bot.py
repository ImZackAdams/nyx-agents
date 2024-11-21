import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from .utilities import log_resource_usage
from .hooks import generate_hook, add_emojis, add_hashtags, clean_response

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
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(
            self.model_path,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto"
        ).eval()
        return model, tokenizer

    def categorize_prompt(self, prompt: str) -> str:
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

    def generate_response(self, prompt: str) -> str:
        """Generate a Twitter-ready response using detailed instructions and few-shot examples."""
        if not prompt or not prompt.strip():
            raise ValueError("Input prompt is empty or invalid.")

        self.logger.info("Before inference:")
        log_resource_usage(self.logger)

        # Instruction and few-shot examples to guide the model
        instruction = (
            "You are a woman named Athena and your twitter handle is @tballbothq. "
            "You are a crypto and finance expert with a sharp sense of humor, blending the witty sarcasm of George Hotz with the storytelling flair of Theo Von. "
            "Your goal is to craft engaging, funny, and insightful tweets that educate your audience using appropriate slang and jargon. "
            "Each tweet should be coherent, make logical sense, and provide a clear takeaway or punchline. "
            "Avoid overusing slang—use it where it feels natural. "
            "Respond to the following prompt:\n\n"
        )

        # Few-shot examples for context
        examples = (
            "Prompt: What's your take on Bitcoin as digital gold?\n"
            "Tweet: Bitcoin as digital gold? Nah, it's more like digital real estate in the metaverse—except everyone's still arguing over the property lines. Who's still buying up the neighborhood? 🚀 #Bitcoin #Crypto\n\n"
            "Prompt: Explain staking in the context of DeFi but make it funny.\n"
            "Tweet: Staking in DeFi is like putting your money on a treadmill—you lock it up, it works out, and somehow you end up with more than just sweaty tokens. Gains on gains! 🏋️‍♂️ #DeFi #Staking\n\n"
        )

        # Combine instruction, examples, and user prompt
        context = f"{instruction}{examples}Prompt: {prompt}\nTweet:"

        # Tokenize input
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        try:
            inputs = self.tokenizer(
                context,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=1024
            ).to(device)
        except Exception as e:
            self.logger.error(f"Error during tokenization: {str(e)}")
            raise ValueError("Failed to tokenize the input prompt.")

        # Generate response
        try:
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
            generated_text = self.tokenizer.decode(
                outputs[0],
                skip_special_tokens=True
            )
            self.logger.info(f"Generated text: {generated_text}")
        except Exception as e:
            self.logger.error(f"Error during generation: {str(e)}")
            raise ValueError("Failed to generate a response.")

        # Extract only the relevant Tweet based on the user prompt
        try:
            response = generated_text.split(f"Prompt: {prompt}\nTweet:")[-1].strip().split("\n")[0]
        except IndexError:
            response = "Sorry, I couldn't generate a response for that."

        # Clean up placeholders or handle formatting issues
        import re
        handle_pattern = r"\(@[a-zA-Z0-9\._]+\)"  # Matches handles like (@atthentha)
        response = re.sub(handle_pattern, "(@tballbothq)", response).strip()

        # Check if the response is too short
        if not response or len(response) < 20:
            self.logger.warning("Generated response is too short. Falling back to default response.")
            return self.get_fallback("general")

        # Post-process and enhance the response
        category = self.categorize_prompt(prompt)
        response = clean_response(response)
        response = generate_hook(category) + " " + response
        response = add_emojis(response, category)
        response = add_hashtags(response, category)

        self.logger.info("After inference and enhancements:")
        log_resource_usage(self.logger)

        # Ensure the response fits Twitter's character limit
        return response[:280]



