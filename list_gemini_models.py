#!/usr/bin/env python3
"""Check available Google Gemini models"""
import os
from dotenv import load_dotenv

load_dotenv()

try:
    from google import genai
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("GOOGLE_API_KEY not set in .env")
        exit(1)
    
    client = genai.Client(api_key=api_key)
    
    print("Available models:")
    print("-" * 60)
    
    models = client.models.list()
    for model in models:
        print(f"  - {model.name}")
        if hasattr(model, 'supported_generation_methods'):
            print(f"    Methods: {model.supported_generation_methods}")
    
except Exception as e:
    print(f"Error: {e}")
    print("\nTrying to list models that support image generation...")
    print("The new API might use 'imagen-3.0-fast-generate-001' or similar")
