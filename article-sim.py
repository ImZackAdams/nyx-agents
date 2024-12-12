import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from typing import Tuple, Optional
from dataclasses import dataclass
import os
import gc
import logging
import sys
from pathlib import Path
import warnings
import random
import feedparser
import requests
from bs4 import BeautifulSoup

# Suppress warnings
warnings.filterwarnings("ignore")

# Set environment variables for memory management
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:512'

def setup_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter('%(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

@dataclass
class GenerationConfig:
    """Configuration for text generation parameters"""
    max_new_tokens: int = 75  # Reduced to force conciseness
    min_new_tokens: int = 30  # Reduced to avoid fluff
    temperature: float = 0.3  # Reduced significantly to stay on topic
    top_k: int = 20  # Reduced for more focused output
    top_p: float = 0.8  # Reduced for more conservative sampling
    repetition_penalty: float = 1.5  # Increased to avoid repetition

class StyleConfig:
    @staticmethod
    def default():
        sc = StyleConfig()
        sc.openers = [
            "🚀 Breaking Crypto:", 
            "💡 Crypto Update:", 
            "📊 Chain Analysis:",
            "🔥 Dev Report:",
            "⚡️ Latest Stats:",
            "🎯 Chain Metrics:",
        ]
        return sc

class ModelManager:
    def __init__(self, model_path: str, logger: Optional[logging.Logger] = None):
        self.model_path = model_path
        self.logger = logger or setup_logger("model_manager")
        
        if not torch.cuda.is_available():
            raise RuntimeError("CUDA is not available. Please check your PyTorch installation.")
            
        self.device = torch.device("cuda")
        torch.cuda.empty_cache()
        self.model, self.tokenizer = self._setup_model()
        self.generation_config = GenerationConfig()

    def _setup_model(self) -> Tuple[AutoModelForCausalLM, AutoTokenizer]:
        """Initialize and load the model and tokenizer with CUDA support."""
        print("\n📚 Loading tokenizer...")
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                self.model_path,
                local_files_only=True,
                trust_remote_code=True
            )
            
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token

        except Exception as e:
            print(f"❌ Error loading tokenizer: {e}")
            raise

        print("🔧 Loading 4-bit quantized model...")
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
                device_map="balanced",
                quantization_config=quantization_config,
                torch_dtype=torch.float16,
                low_cpu_mem_usage=True,
            ).eval()
            
            if not next(model.parameters()).is_cuda:
                raise RuntimeError("Model failed to load on CUDA")

        except Exception as e:
            print(f"❌ Error loading model: {e}")
            raise

        return model, tokenizer

    def generate(self, context: str) -> str:
        try:
            system_prefix = """You are a crypto news bot. Extract and summarize ONLY the main headline from the article title. Rules:
1. Start with 🚀 for positive growth news
2. Must include ALL specific numbers mentioned in the title
3. Focus ONLY on the main story about developer growth/adoption
4. REQUIRED hashtags for any chains mentioned
5. Keep to NEWS HEADLINE style - clear, direct statement
6. ONLY discuss the main news point, no secondary details
7. Maximum 180 characters (to leave room for hashtags)"""
            
            context_with_constraint = f"{system_prefix}\n\n{context}"
            
            inputs = self.tokenizer(
                context_with_constraint,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=1024
            ).to(self.device)
            
            with torch.inference_mode(), torch.amp.autocast('cuda'):
                outputs = self.model.generate(
                    inputs["input_ids"],
                    attention_mask=inputs["attention_mask"],
                    max_new_tokens=self.generation_config.max_new_tokens,
                    min_new_tokens=self.generation_config.min_new_tokens,
                    do_sample=True,
                    temperature=self.generation_config.temperature,
                    top_k=self.generation_config.top_k,
                    top_p=self.generation_config.top_p,
                    repetition_penalty=self.generation_config.repetition_penalty,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                    use_cache=True,
                )

            generated_text = self.tokenizer.decode(
                outputs[0][inputs["input_ids"].shape[1]:], 
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True
            ).strip()
            
            # Smart tweet cleanup
            if len(generated_text) > 280:
                for punct in ['. ', '! ', '? ']:
                    last_break = generated_text[:280].rfind(punct)
                    if last_break != -1:
                        generated_text = generated_text[:last_break + 1].strip()
                        break
                if len(generated_text) > 280:
                    generated_text = generated_text[:277] + "..."
            
            # Smart hashtag addition
            if 'solana' in generated_text.lower() and '#solana' not in generated_text.lower():
                generated_text += " #Solana"
            if 'ethereum' in generated_text.lower() and '#eth' not in generated_text.lower():
                generated_text += " #ETH"
            if not any(tag in generated_text.lower() for tag in ['#solana', '#eth', '#btc']):
                generated_text += " #crypto"
            
            del outputs
            gc.collect()
            torch.cuda.empty_cache()
                
            return generated_text

        except Exception as e:
            print(f"❌ Error in generation: {e}")
            return ""

    def __del__(self):
        try:
            torch.cuda.empty_cache()
        except:
            pass

class PersonalityBot:
    def __init__(self, model_path: str, logger: Optional[logging.Logger] = None, style_config: StyleConfig = None):
        self.model_manager = ModelManager(model_path, logger=logger)
        self.style_config = style_config or StyleConfig.default()
        self.recent_openers = []
        self.max_history = 10

    def _prepare_context(self, prompt: str) -> str:
        opener = random.choice([op for op in self.style_config.openers 
                              if op not in self.recent_openers])
        self.recent_openers.append(opener)
        if len(self.recent_openers) > self.max_history:
            self.recent_openers.pop(0)
        
        return f"{opener} {prompt}"

    def generate_response(self, prompt: str) -> str:
        if not prompt.strip():
            return ""

        try:
            context = self._prepare_context(prompt)
            return self.model_manager.generate(context)

        except Exception as e:
            print(f"❌ Error generating response: {e}")
            return ""

def fetch_latest_article(feed_url="https://www.coindesk.com/arc/outboundfeeds/rss/?"):
    feed = feedparser.parse(feed_url)
    if feed.entries:
        return feed.entries[0]
    return None

def get_full_article_text(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        return f"Failed to retrieve article: {str(e)}"

    soup = BeautifulSoup(response.text, 'html.parser')

    # Remove unwanted elements
    for element in soup.find_all(['script', 'style', 'nav', 'header', 'footer']):
        element.decompose()

    # Try different selectors to find the article content
    content_selectors = [
        ('article', None),
        ('main', None),
        ('div', 'article-content'),
        ('div', 'post-content'),
        ('div', 'entry-content'),
        ('div', 'content-body'),
    ]

    for tag, class_name in content_selectors:
        container = soup.find(tag, class_=class_name) if class_name else soup.find(tag)
        if container:
            # Get all text blocks
            text_blocks = []
            for p in container.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                text = p.get_text(strip=True)
                if text and len(text) > 20:  # Filter out short snippets
                    text_blocks.append(text)
            
            if text_blocks:
                return "\n\n".join(text_blocks)

    return "Could not find main content. Try updating selectors."

def create_summary_prompt(article_text, title):
    return f"""WRITE ONE TWEET ABOUT THIS EXACT HEADLINE:

{title}

REQUIRED FORMAT:
🚀 [Main News Fact] + [Key Number/Metric] #Hashtags

EXAMPLE GOOD TWEETS:
"🚀 Solana leads crypto dev growth in 2024 with massive 83% surge in new developers #Solana"
"🚀 Ethereum hits new milestone with 5,000 monthly active developers in Q4 2024 #ETH"

Rules:
1. USE THE EXACT NUMBERS from the title/first paragraph
2. Focus ONLY on developer growth/numbers
3. Chain-specific hashtags required
4. ONE clear statement, no extra details
5. Maximum 180 chars (leaves room for hashtags)

Generate ONE tweet that captures ONLY the headline news about developer activity."""

def simulate_bot_responses():
    print("\n" + "="*80)
    print("🤖 CRYPTO NEWS BOT SIMULATION")
    print("="*80)

    model_path = "./mistral_qlora_finetuned"
    if not Path(model_path).exists():
        print("❌ Error: Model not found at specified path")
        return

    try:
        bot = PersonalityBot(model_path=model_path)

        print("\n📰 Fetching latest article from CoinDesk...")
        latest_article = fetch_latest_article()
        
        if latest_article:
            title = latest_article.get("title", "No title")
            link = latest_article.get("link", "No link")
            
            print("\n📍 ARTICLE DETAILS")
            print("-" * 40)
            print(f"Title: {title}")
            print(f"Link: {link}")

            print("\n📝 Extracting content...")
            full_content = get_full_article_text(link)
            
            if "Could not find main content" in full_content or full_content.startswith("Failed to"):
                print("❌ Error: Could not retrieve article content")
                return
            
            prompt = create_summary_prompt(full_content, title)
            
            print("\n🎯 GENERATING SUMMARIES")
            print("-" * 40)
            
            summaries = []
            for attempt in range(3):
                print(f"\nAttempt {attempt + 1}:")
                summary = bot.generate_response(prompt)
                if summary and 50 <= len(summary) <= 280:
                    print(f"{summary}")
                    print(f"Length: {len(summary)} characters")
                    print("-" * 40)
                    summaries.append(summary)
            
            if summaries:
                # Score summaries based on relevance and quality
                def score_summary(summary):
                    score = 0
                    if any(chain in summary.lower() for chain in ['solana', 'ethereum', 'btc']):
                        score += 1
                    if any(tag in summary for tag in ['#Solana', '#ETH', '#BTC']):
                        score += 1
                    if any(char.isdigit() for char in summary):
                        score += 1
                    if 'developer' in summary.lower() or 'dev' in summary.lower():
                        score += 1
                    return score

                best_summary = max(summaries, key=score_summary)
                
                print("\n✨ BEST GENERATED TWEET")
                print("-" * 40)
                print(f"{best_summary}")
                print(f"\nCharacter count: {len(best_summary)}/280")
                
                hashtags = ' '.join(word for word in best_summary.split() if word.startswith('#'))
                if hashtags:
                    print(f"Hashtags used: {hashtags}")
            else:
                print("\n❌ No valid summaries generated")
        else:
            print("❌ No article found")

    except Exception as e:
        print(f"\n❌ Error during simulation: {str(e)}")

    print("\n" + "="*80)

if __name__ == "__main__":
    simulate_bot_responses()