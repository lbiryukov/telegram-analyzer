import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Literal
import pandas as pd
from backend.telegram_analyzer import TelegramAnalyzer
from backend.ai_utils import generate_search_keywords, get_ai_response
from backend.message_retriever import MessageRetriever
from backend.ai_context_builder import AIContextBuilder
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('benchmark.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('Benchmark')

# Load environment variables
load_dotenv()

# Constants
MAX_CONTEXT_LENGTH = 50000  # Maximum allowed context length

class Benchmark:
    def __init__(self):
        self.telegram_analyzer = TelegramAnalyzer()
        self.message_retriever = MessageRetriever()
        self.ai_context_builder = AIContextBuilder()
        
        # Create results directory if it doesn't exist
        os.makedirs('benchmark_results', exist_ok=True)
    
    def run_test_case(
        self,
        chat_url: str,
        prompt: str,
        circ_count: int,
        answer_depth: int,
        model: Literal['deepseek', 'gemma3'] = 'gemma3',
        days_back: int = 365
    ) -> Dict[str, Any]:
        """
        Run a single test case with specific settings.
        
        Args:
            chat_url: Telegram chat URL
            prompt: User's question
            circ_count: Number of context messages
            answer_depth: Answer chain depth
            model: AI model to use (deepseek or gemma3)
            days_back: Number of days to look back
            
        Returns:
            Dictionary containing results and timing information
        """
        start_time = time.time()
        results = {
            'chat_url': chat_url,
            'prompt': prompt,
            'settings': {
                'circ_count': circ_count,
                'answer_depth': answer_depth,
                'model': model,
                'days_back': days_back
            },
            'timing': {},
            'results': {}
        }
        
        try:
            # 1. Get chat ID
            chat_id = self.telegram_analyzer.get_chat_id_from_url(chat_url)
            if not chat_id:
                raise ValueError(f"Could not find chat ID for URL: {chat_url}")
            
            # 2. Set date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # 3. Fetch messages from chat
            fetch_start = time.time()
            result = self.telegram_analyzer.fetch_messages_sync(
                chat_urls=[chat_url],
                telegram_api_id=os.getenv('TELEGRAM_API_ID'),
                telegram_api_hash=os.getenv('TELEGRAM_API_HASH'),
                days_back=days_back,
                progress_callback=None
            )
            results['timing']['fetch_messages'] = time.time() - fetch_start
            results['results']['fetch_result'] = result
            
            # 4. Generate keywords
            keyword_start = time.time()
            keywords = generate_search_keywords(prompt, model=model)
            results['timing']['generate_keywords'] = time.time() - keyword_start
            results['results']['keywords'] = keywords
            
            # 5. Get message stats
            stats_start = time.time()
            keyword_messages = self.message_retriever.get_messages_with_keywords(
                chat_id=chat_id,
                keywords=keywords,
                start_date=start_date,
                end_date=end_date
            )
            
            stats = {
                'parameters': {
                    'chat_id': chat_id,
                    'keywords': keywords,
                    'date_range': f"{start_date} to {end_date}"
                },
                'keyword_messages': {
                    'count': len(keyword_messages),
                    'total_length': sum(len(msg['text']) for msg in keyword_messages),
                    'by_keyword': {
                        keyword: {
                            'count': len([msg for msg in keyword_messages if keyword.lower() in msg['text'].lower()]),
                            'total_length': sum(len(msg['text']) for msg in keyword_messages if keyword.lower() in msg['text'].lower())
                        }
                        for keyword in keywords
                    }
                }
            }
            results['timing']['get_stats'] = time.time() - stats_start
            results['results']['message_stats'] = stats
            
            # 6. Optimize keywords
            optimize_start = time.time()
            optimized_keywords = self.message_retriever.optimize_keywords_for_length(
                chat_id=chat_id,
                keywords=keywords,
                start_date=start_date,
                end_date=end_date,
                existing_stats=stats,
                max_length=20000
            )
            results['timing']['optimize_keywords'] = time.time() - optimize_start
            results['results']['optimized_keywords'] = optimized_keywords
            
            # 7. Retrieve messages with context
            retrieve_start = time.time()
            result = self.message_retriever.get_messages_with_context(
                chat_id=chat_id,
                keywords=optimized_keywords,
                start_date=start_date,
                end_date=end_date,
                circ_count=circ_count,
                answer_depth_limit=answer_depth,
                max_length=20000
            )
            results['timing']['retrieve_messages'] = time.time() - retrieve_start
            results['results']['context_message_count'] = len(result['messages'])
            
            # 8. Create context
            context_start = time.time()
            context = self.ai_context_builder.get_context_for_ai(
                messages=result['messages'],
                query=prompt
            )
            results['timing']['create_context'] = time.time() - context_start
            
            # 9. Get AI response
            ai_start = time.time()
            ai_response = get_ai_response(context, prompt, model=model)
            results['timing']['get_ai_response'] = time.time() - ai_start
            
            if ai_response['error']:
                raise ValueError(f"AI response error: {ai_response['error']}")
            
            results['results']['ai_response'] = ai_response['response']
            
            # 10. Evaluate response
            eval_start = time.time()
            evaluation = self.evaluate_response(prompt, ai_response['response'], model=model)
            results['timing']['evaluate_response'] = time.time() - eval_start
            results['results']['evaluation'] = evaluation
            
            # Calculate total time
            results['timing']['total'] = time.time() - start_time
            
            return results
            
        except Exception as e:
            logger.error(f"Error in test case: {str(e)}")
            results['error'] = str(e)
            results['timing']['total'] = time.time() - start_time
            return results
    
    def evaluate_response(self, prompt: str, response: str, model: Literal['deepseek', 'gemma3'] = 'gemma3') -> Dict[str, Any]:
        """
        Evaluate how well the AI response matches the user's prompt.
        
        Args:
            prompt: User's original question
            response: AI's response
            model: AI model to use for evaluation
            
        Returns:
            Dictionary containing evaluation metrics
        """
        try:
            # Generate evaluation prompt with structured format
            eval_prompt = f"""
            Evaluate the following response to a user's question. Provide scores and explanation in the following format:

            SCORES:
            relevance: [1-5]
            completeness: [1-5]
            accuracy: [1-5]
            clarity: [1-5]
            overall: [1-5]

            EXPLANATION:
            [Your detailed explanation here]

            User's question: {prompt}
            
            AI's response: {response}
            """
            
            # Get evaluation from AI
            eval_response = get_ai_response(eval_prompt, "Evaluate the response", model=model)
            
            if eval_response['error']:
                raise ValueError(f"Evaluation error: {eval_response['error']}")
            
            # Parse scores and explanation
            scores = {}
            explanation = ""
            current_section = None
            
            for line in eval_response['response'].split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                if line == 'SCORES:':
                    current_section = 'scores'
                    continue
                elif line == 'EXPLANATION:':
                    current_section = 'explanation'
                    continue
                
                if current_section == 'scores':
                    if ':' in line:
                        metric, value = line.split(':')
                        metric = metric.strip().lower()
                        try:
                            value = int(value.strip())
                            if 1 <= value <= 5:
                                scores[metric] = value
                        except ValueError:
                            continue
                elif current_section == 'explanation':
                    explanation += line + '\n'
            
            # Calculate average score
            if scores:
                scores['average'] = sum(scores.values()) / len(scores)
            
            return {
                'scores': scores,
                'explanation': explanation.strip()
            }
            
        except Exception as e:
            logger.error(f"Error evaluating response: {str(e)}")
            return {
                'scores': {},
                'explanation': f"Error during evaluation: {str(e)}"
            }
    
    def run_benchmark(
        self,
        test_cases: List[Tuple[str, str]],
        settings: List[Dict[str, Any]]
    ) -> pd.DataFrame:
        """
        Run benchmark tests with different settings.
        
        Args:
            test_cases: List of (chat_url, prompt) tuples
            settings: List of setting dictionaries containing circ_count and answer_depth
            
        Returns:
            DataFrame containing benchmark results
        """
        results = []
        
        for chat_url, prompt in test_cases:
            for setting in settings:
                logger.info(f"Running test case: {chat_url} with prompt: {prompt}")
                logger.info(f"Settings: {setting}")
                
                result = self.run_test_case(
                    chat_url=chat_url,
                    prompt=prompt,
                    circ_count=setting['circ_count'],
                    answer_depth=setting['answer_depth'],
                    model=setting.get('model', 'gemma3')  # Default to gemma3 if not specified
                )
                
                # Convert result to DataFrame row
                row = {
                    'chat_url': result['chat_url'],
                    'prompt': result['prompt'],
                    'circ_count': setting['circ_count'],
                    'answer_depth': setting['answer_depth'],
                    'model': setting.get('model', 'gemma3'),
                    'total_time': result['timing']['total'],
                    'message_count': result['results'].get('context_message_count', 0),
                    'context_message_count': result['results'].get('context_message_count', 0),
                    'raw_keywords': ', '.join(result['results'].get('keywords', [])),
                    'optimized_keywords': ', '.join(result['results'].get('optimized_keywords', [])),
                    'ai_response': result['results'].get('ai_response', ''),
                    'error': result.get('error')
                }
                
                # Add evaluation scores if available
                if 'evaluation' in result['results']:
                    eval_scores = result['results']['evaluation']['scores']
                    for metric, score in eval_scores.items():
                        row[f'eval_{metric}'] = score
                
                results.append(row)
                
                # Save detailed results to JSON
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                result_file = f'benchmark_results/detailed_{timestamp}.json'
                with open(result_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
        
        # Create DataFrame
        df = pd.DataFrame(results)
        
        # Save results to Excel
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        excel_file = f'benchmark_results/benchmark_results_{timestamp}.xlsx'
        df.to_excel(excel_file, index=False, sheet_name='Results')
        
        # Save summary to CSV
        summary_file = f'benchmark_results/summary_{timestamp}.csv'
        df.to_csv(summary_file, index=False)
        
        return df

def main():
    # Define test cases
    test_cases = [
        ("t.me/vake_tbi", "где купить круассаны?"),
        ("t.me/vake_tbi", "как открыть банковский счет?"),
        ("t.me/vake_tbi", "где купить хорошие стейки?"),
        ("t.me/denizbank_ru", "каковы основные причины закрытия банковских счетов?")
    ]
    
    # Define settings to test
    settings = [
        {'circ_count': 0, 'answer_depth': 2},
        {'circ_count': 0, 'answer_depth': 10},
        {'circ_count': 2, 'answer_depth': 2},
        {'circ_count': 2, 'answer_depth': 10}
    ]
    
    # Run benchmark
    benchmark = Benchmark()
    results_df = benchmark.run_benchmark(test_cases, settings)
    
    # Print summary
    print("\nBenchmark Summary:")
    print(results_df.groupby(['circ_count', 'answer_depth']).agg({
        'total_time': 'mean',
        'message_count': 'mean',
        'context_message_count': 'mean',
        'error': 'count'
    }).round(2))

if __name__ == "__main__":
    main() 