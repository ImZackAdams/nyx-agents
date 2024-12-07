print("1. Testing basic imports...")

try:
    from bot.processors.text_processor import TextProcessor
    print("✓ Successfully imported TextProcessor")
except ImportError as e:
    print(f"✗ Failed to import TextProcessor: {str(e)}")
    
try:
    from bot.configs.style_config import StyleConfig, Category
    print("✓ Successfully imported StyleConfig and Category")
except ImportError as e:
    print(f"✗ Failed to import StyleConfig and Category: {str(e)}")
    
try:
    from bot.bot import PersonalityBot
    print("✓ Successfully imported PersonalityBot")
except ImportError as e:
    print(f"✗ Failed to import PersonalityBot: {str(e)}")

print("\n2. All import tests complete.")