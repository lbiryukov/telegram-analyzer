import logging
from typing import List, Dict, Any
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_context_builder.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('AIContextBuilder')

class AIContextBuilder:
    def __init__(self):
        pass
    
    def build_context(self, messages: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
        """
        Build a context dictionary from retrieved messages for AI processing.
        Organizes messages in a thread-like structure and includes only essential fields.
        
        Args:
            messages: List of messages from the message retriever
            query: The original search query
            
        Returns:
            Dictionary containing:
            - query: original search query
            - messages: list of simplified message objects
            - message_threads: dictionary mapping message IDs to their child messages
        """
        try:
            # Create a simplified message list with only essential fields
            simplified_messages = []
            message_threads = {}
            
            for msg in messages:
                # Create simplified message object
                simple_msg = {
                    'message_id': msg['message_id'],
                    'parent_id': msg.get('reply_to_message_id'),  # May be None
                    'date': msg['date'],
                    'author': msg['sender'],
                    'text': msg['text']
                }
                
                simplified_messages.append(simple_msg)
                
                # Build thread structure
                parent_id = msg.get('reply_to_message_id')
                if parent_id:
                    if parent_id not in message_threads:
                        message_threads[parent_id] = []
                    message_threads[parent_id].append(msg['message_id'])
            
            # Sort messages by date
            simplified_messages.sort(key=lambda x: x['date'])
            
            context = {
                'query': query,
                'messages': simplified_messages,
                'message_threads': message_threads
            }
            
            logger.info(f"Built context with {len(simplified_messages)} messages and {len(message_threads)} threads")
            return context
            
        except Exception as e:
            logger.error(f"Error building context: {str(e)}")
            raise
    
    def format_context_for_prompt(self, context: Dict[str, Any]) -> str:
        """
        Format the context into a string suitable for the AI prompt.
        Creates a readable conversation format with thread indicators.
        
        Args:
            context: Context dictionary from build_context
            
        Returns:
            Formatted string containing the conversation context
        """
        try:
            formatted_lines = []
            
            # Add the AI assistant introduction
            formatted_lines.append("You are a helpful and knowledgeable AI assistant.\n")
            
            # Add the context section
            formatted_lines.append("Context:")
            formatted_lines.append("{Insert the provided context here — clearly and completely}\n")
            
            # Track message indentation levels based on thread structure
            indent_levels = {}
            
            # Add the messages
            for msg in context['messages']:
                # Determine indentation level
                if msg['parent_id'] is None:
                    indent_level = 0
                else:
                    # If it's a reply, indent one level more than parent
                    parent_level = indent_levels.get(msg['parent_id'], 0)
                    indent_level = parent_level + 1
                
                # Store this message's indent level
                indent_levels[msg['message_id']] = indent_level
                
                # Format the message with proper indentation
                indent = "  " * indent_level
                
                # Handle date formatting
                date = msg['date']
                if isinstance(date, str):
                    # If date is already a string, use it as is
                    date_str = date
                else:
                    # If date is a datetime object, format it
                    date_str = date.strftime("%Y-%m-%d %H:%M:%S")
                
                formatted_msg = (
                    f"{indent}[{date_str}] {msg['author']}:\n"
                    f"{indent}{msg['text']}"
                )
                formatted_lines.append(formatted_msg)
            
            # Add the user's question section
            formatted_lines.append("\nUser's Question:")
            formatted_lines.append("{Insert the user's question here — exactly as given}\n")
            
            # Add the instructions for the AI
            formatted_lines.append("Based only on the context above, generate the most accurate, complete, and well-structured answer to the user's question.")
            formatted_lines.append("\nIf necessary, explain your reasoning clearly and concisely.")
            formatted_lines.append("\nIf the context does not provide enough information to answer fully, say so explicitly and suggest what might be missing.")
            
            return "\n".join(formatted_lines)
            
        except Exception as e:
            logger.error(f"Error formatting context: {str(e)}")
            raise
    
    def get_context_for_ai(self, messages: List[Dict[str, Any]], query: str) -> str:
        """
        Convenience method that builds and formats context in one step.
        
        Args:
            messages: List of messages from the message retriever
            query: The original search query
            
        Returns:
            Formatted string ready for AI prompt
        """
        context = self.build_context(messages, query)
        return self.format_context_for_prompt(context) 