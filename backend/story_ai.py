# vertex_ai_setup.py
from google.cloud import aiplatform
import os


def create_prompt(city, climate_data):
    return f"""
    You are a climate communication expert. Based on the following climate data, write an engaging and informative summary that explains what this means for residents of {city} in a human-centered way:

    {climate_data}

    Your summary should:
    - Start with a striking local fact or change (e.g., temperature rise or rainfall changes)
    - Explain what it means for daily life, health, or the environment in {city}
    - Be clear, non-technical, and emotionally resonant
    - Avoid fictional stories or made-up characters
    - Use second-person ("you", "your city") language when appropriate

    Keep it under 300 words. End with a hopeful or action-oriented message.
    """
