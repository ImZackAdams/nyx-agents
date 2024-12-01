import os
import time
from dotenv import load_dotenv
from bot.bot import PersonalityBot
import logging
import warnings

# Suppress specific warnings
warnings.filterwarnings("ignore", message=".*MatMul8bitLt.*")
warnings.filterwarnings("ignore", message=".*quantization_config.*")
warnings.filterwarnings("ignore", message=".*Unused kwargs.*")

# Load environment variables
load_dotenv()

# Configure logging to suppress most messages
logging.basicConfig(level=logging.ERROR)
for name in logging.root.manager.loggerDict:
    logging.getLogger(name).setLevel(logging.ERROR)

def main():
    try:
        model_path = "athena_8bit_model"
        bot = PersonalityBot(model_path=model_path, logger=logging.getLogger(__name__))

    except Exception as e:
        print(f"✨ Initialization error! Check if model path exists: {str(e)} 💅")
        return

    prompts = [
        # Evergreen Crypto Takes
        "Spill the tea on why HODLing isn't always the best strategy! Give us those timeless investment wisdom bombs!",
        "Share your spiciest take on why diversification matters in crypto. Make it iconic!",
        "Drop some timeless wisdom about crypto security practices. Make it sassy but educational!",
        
        # Tech Fundamentals
        "Explain why blockchain technology is more than just crypto! Serve pure tech tea!",
        "Spill the tea on why decentralization matters! Make it relevant for everyone!",
        "Break down smart contracts like you're explaining them to your bestie! Keep it fresh!",
        
        # Philosophical Takes
        "Give us your hottest take on the future of digital ownership! Make it thought-provoking!",
        "Share your spiciest thoughts on web3 privacy! Keep it relevant and real!",
        "Drop some truth bombs about decentralized identity! Make it accessible!",
        
        # Educational Moments
        "Explain consensus mechanisms like you're hosting a masterclass! Extra sass required!",
        "Break down DeFi fundamentals like you're teaching Fashion Week! Make it pop!",
        "Share some timeless blockchain scaling tea! Keep it fresh and fierce!",
        
        # Culture Commentary
        "Spill the tea on crypto community dynamics! Keep it real but make it fun!",
        "Share your thoughts on why DYOR is everything in crypto! Make it memorable!",
        "Rate different crypto research strategies! Be the Simon Cowell of DYOR!"
    ]

    def post_simulated_output(prompt):
        """Generate and print only the response."""
        try:
            generated_output = bot.generate_response(prompt)
            
            # Clean any potential formatting issues
            generated_output = generated_output.replace('\n', ' ').strip()
            
            # Only print if we have a valid response
            if len(generated_output) >= 20:
                print(f"{generated_output}")
            else:
                print("✨ Brewing fresh tea... try again! 💅")
                
        except Exception as e:
            print(f"✨ Oops! Error brewing tea: {str(e)} 💅")

    post_interval = 2  # 10 seconds between posts

    try:
        # Loop through prompts once
        for prompt in prompts:
            post_simulated_output(prompt)
            print("")  # Single blank line between responses
            time.sleep(post_interval)
            
        print("\n✨ All prompts have been processed! Tea time's complete! 💅")

    except KeyboardInterrupt:
        print("\n💅 Tea time's over! Bye bestie! ✨")


if __name__ == "__main__":
    main()