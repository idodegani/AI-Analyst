import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test environment variables
print("Testing environment variables:")
print(f"OPENAI_API_KEY: {'Set' if os.environ.get('OPENAI_API_KEY') else 'Not set'}")
print(f"LLAMA_CLOUD_API_KEY: {'Set' if os.environ.get('LLAMA_CLOUD_API_KEY') else 'Not set'}")
print(f"LLAMA_CLOUD_INDEX_NAME: {os.environ.get('LLAMA_CLOUD_INDEX_NAME', 'Not set')}")
print(f"LLAMA_CLOUD_PROJECT_NAME: {os.environ.get('LLAMA_CLOUD_PROJECT_NAME', 'Not set')}")
print(f"LLAMA_CLOUD_ORGANIZATION_ID: {os.environ.get('LLAMA_CLOUD_ORGANIZATION_ID', 'Not set')}")
