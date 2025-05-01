from benchmark import Benchmark
from datetime import timedelta
import pandas as pd
import os

def main():
    # Define test cases
    test_cases = [
        ("t.me/vake_tbi", "Где купить круассаны?"),
        ("t.me/vake_tbi", "Где купить хорошие стейки?"),
        ("t.me/denizbank_ru", "Каковы основные причины закрытия банковских счетов?"),
        ("t.me/denizbank_ru", "В каких отделениях более лояльные условия открытия счёта?"),
        ("t.me/paravaingeorgia", "Сколько времени занимает получение водительских прав в Грузии?"),
        ("t.me/paravaingeorgia", "Можно ли обменять российские права на грузинские?"),
        ("t.me/bog_users", "По каким причинам банк отказывает в открытии счета?"),
        ("t.me/bog_users", "Как часто банк отказывает россиянам в открытии счетов?"),
        ("t.me/bog_users", "Какая комиссия за отправку свифтов?"),
        ("t.me/bog_users", "В чём разница между разными тарифами в SOLO?"),
        ("t.me/ski_ge", "Как проще всего добраться из Тбилиси до Гудаури?"),
        ("t.me/ski_ge", "Что сейчас со снегом в Гудаури?"),
        ("t.me/shengen_am", "Какие документы нужны чтобы получить шенгенскую визу?"),
        ("t.me/shengen_am", "Сколько ждать получения визы?"),

    ]
    
    # Define settings to test
    settings = [
        {'circ_count': 0, 'answer_depth': 2, 'model': 'gemma3', 'max_length': 15000},  # Use Gemma3 model with smaller context
        {'circ_count': 0, 'answer_depth': 2, 'model': 'deepseek'},  # Compare with DeepSeek
        #{'circ_count': 0, 'answer_depth': 10},
        #{'circ_count': 2, 'answer_depth': 2},
        #{'circ_count': 0, 'answer_depth': 10}
    ]
    
    # Create results directory if it doesn't exist
    os.makedirs('benchmark_results', exist_ok=True)
    
    # Run benchmark
    benchmark = Benchmark()
    results_df = benchmark.run_benchmark(test_cases, settings)
    
    # Print summary
    print("\nBenchmark Summary:")
    print("\nPerformance Metrics:")
    print(results_df.groupby(['circ_count', 'answer_depth', 'model']).agg({
        'total_time': 'mean',
        'message_count': 'mean',
        'context_message_count': 'mean',
        'error': 'count'
    }).round(2))
    
    print("\nResponse Quality Metrics:")
    eval_columns = [col for col in results_df.columns if col.startswith('eval_')]
    if eval_columns:
        print(results_df.groupby(['circ_count', 'answer_depth', 'model'])[eval_columns].mean().round(2))
    
    # Print detailed results for each test case
    print("\nDetailed Results:")
    for _, row in results_df.iterrows():
        print(f"\nChat: {row['chat_url']}")
        print(f"Prompt: {row['prompt']}")
        print(f"Settings: circ_count={row['circ_count']}, answer_depth={row['answer_depth']}, model={row['model']}")
        if 'error' in row and pd.notna(row['error']):
            print(f"Error: {row['error']}")
        else:
            print("Evaluation Scores:")
            for col in eval_columns:
                if pd.notna(row[col]):
                    print(f"- {col.replace('eval_', '')}: {row[col]:.2f}")
    
    # Print information about saved files
    print("\nResults have been saved to:")
    print("- Excel file with detailed results in 'benchmark_results/benchmark_results_*.xlsx'")
    print("- Summary CSV file in 'benchmark_results/summary_*.csv'")
    print("- Individual JSON files for each test case in 'benchmark_results/detailed_*.json'")

if __name__ == '__main__':
    main() 