import os
import logging
import requests
from typing import List
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_utils.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('AIUtils')

def generate_search_keywords(prompt: str) -> List[str]:
    """
    Generate search keywords from a user prompt using Deepseek API.
    The keywords are designed to retrieve the most relevant context for answering the prompt.
    """
    try:
        # Get API key from environment
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable is not set")
        
        # Prepare the API request
        url = "https://api.deepseek.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Create a system prompt that instructs the model to generate search keywords
        system_prompt = """You are a search keyword generator. Your task is to analyze the user's question and generate a list of keywords that would help find the most relevant information to answer it.
        The keywords should be:
        1. Specific and focused on the main topics
        2. Include important entities, concepts, and relationships
        3. Be in the same language as the question
        4. Be suitable for searching in a database of Telegram messages
        5. Include different forms of the same word (e.g., for Russian words, include different cases and forms)
        6. Include common variations and synonyms
        7. Include both full phrases and individual important words
        
        For example, if the question is about "круассаны", include:
        - круассаны, круассанов, круассанами, круассан
        - пекарня, пекарни, пекарню
        - купить, куплю, купил, купила
        - вкусные, вкусный, вкусная
        
        Return only the keywords, separated by commas."""
        
        # Prepare the messages for the API
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        # Make the API request
        response = requests.post(
            url,
            headers=headers,
            json={
                "model": "deepseek-chat",
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 300  # Increased to allow for more variations
            }
        )
        
        # Check if the request was successful
        response.raise_for_status()
        
        # Extract the keywords from the response
        keywords_text = response.json()['choices'][0]['message']['content']
        keywords = [k.strip() for k in keywords_text.split(',')]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = [k for k in keywords if not (k in seen or seen.add(k))]
        
        logger.info(f"Generated keywords for prompt '{prompt}': {unique_keywords}")
        return unique_keywords
        
    except Exception as e:
        logger.error(f"Error generating search keywords: {str(e)}")
        raise 