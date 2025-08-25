#!/usr/bin/env python3
"""
Инструмент для сравнения разных версий поисковой системы
Сравнивает результаты из файла истории поиска
"""

import json
import sys
import os
from datetime import datetime
from typing import List, Dict, Any

def load_history(file_path: str = "search_quality_history.json") -> List[Dict]:
    """Загружает историю результатов тестов"""
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def format_timestamp(timestamp_str: str) -> str:
    """Форматирует timestamp для отображения"""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return timestamp_str

def calculate_improvement(old_value: float, new_value: float) -> str:
    """Вычисляет улучшение в процентах"""
    if old_value == 0:
        return "N/A"
    
    improvement = ((new_value - old_value) / old_value) * 100
    if improvement > 0:
        return f"+{improvement:.1f}%"
    else:
        return f"{improvement:.1f}%"

def compare_metrics(old_metrics: Dict, new_metrics: Dict) -> Dict:
    """Сравнивает метрики между двумя версиями"""
    comparison = {}
    
    # Основные метрики
    basic_metrics = ['pass_rate', 'avg_score', 'avg_composite_score', 'avg_execution_time']
    for metric in basic_metrics:
        old_val = old_metrics.get(metric, 0)
        new_val = new_metrics.get(metric, 0)
        comparison[metric] = {
            'old': old_val,
            'new': new_val,
            'change': calculate_improvement(old_val, new_val)
        }
    
    # Расширенные метрики
    if 'aggregated_metrics' in old_metrics and 'aggregated_metrics' in new_metrics:
        old_agg = old_metrics['aggregated_metrics']
        new_agg = new_metrics['aggregated_metrics']
        
        advanced_metrics = ['precision_at_5', 'ndcg_at_5', 'mrr', 'title_match_score', 'diversity_score', 'speed_score']
        for metric in advanced_metrics:
            old_val = old_agg.get(metric, 0)
            new_val = new_agg.get(metric, 0)
            comparison[f'adv_{metric}'] = {
                'old': old_val,
                'new': new_val,
                'change': calculate_improvement(old_val, new_val)
            }
    
    return comparison

def print_comparison_report(history: List[Dict], indices: List[int]):
    """Выводит отчет сравнения"""
    if len(indices) != 2:
        print("❌ Необходимо указать ровно 2 индекса для сравнения")
        return
    
    old_idx, new_idx = indices
    if old_idx >= len(history) or new_idx >= len(history):
        print(f"❌ Индексы должны быть в диапазоне 0-{len(history)-1}")
        return
    
    old_result = history[old_idx]
    new_result = history[new_idx]
    
    old_summary = old_result['summary']
    new_summary = new_result['summary']
    
    print("🔄 СРАВНЕНИЕ ВЕРСИЙ ПОИСКА")
    print("=" * 60)
    
    print(f"📅 Старая версия: {format_timestamp(old_result['timestamp'])}")
    print(f"📅 Новая версия: {format_timestamp(new_result['timestamp'])}")
    
    if 'git_commit' in old_result and 'git_commit' in new_result:
        print(f"🔗 Коммиты: {old_result['git_commit'][:8]} → {new_result['git_commit'][:8]}")
    
    print()
    
    # Сравниваем метрики
    comparison = compare_metrics(old_summary, new_summary)
    
    print("📊 ОСНОВНЫЕ МЕТРИКИ:")
    print("-" * 30)
    
    metrics_display = {
        'pass_rate': ('Процент прохождения', '%'),
        'avg_score': ('Средний скор', '/100'),
        'avg_composite_score': ('Композитный скор', '/100'),
        'avg_execution_time': ('Среднее время', 'с')
    }
    
    for metric, (name, unit) in metrics_display.items():
        if metric in comparison:
            data = comparison[metric]
            change_icon = "📈" if "+" in data['change'] else "📉" if "-" in data['change'] else "➡️"
            print(f"{change_icon} {name}: {data['old']:.2f}{unit} → {data['new']:.2f}{unit} ({data['change']})")
    
    print("\n🎯 РАСШИРЕННЫЕ МЕТРИКИ:")
    print("-" * 30)
    
    advanced_display = {
        'adv_precision_at_5': ('Precision@5', ''),
        'adv_ndcg_at_5': ('NDCG@5', ''),
        'adv_mrr': ('MRR', ''),
        'adv_title_match_score': ('Title Match', ''),
        'adv_diversity_score': ('Diversity', ''),
        'adv_speed_score': ('Speed', '')
    }
    
    for metric, (name, unit) in advanced_display.items():
        if metric in comparison:
            data = comparison[metric]
            change_icon = "📈" if "+" in data['change'] else "📉" if "-" in data['change'] else "➡️"
            print(f"{change_icon} {name}: {data['old']:.3f}{unit} → {data['new']:.3f}{unit} ({data['change']})")
    
    # Анализ категорий
    print("\n📂 ПО КАТЕГОРИЯМ:")
    print("-" * 30)
    
    old_cats = old_summary.get('category_stats', {})
    new_cats = new_summary.get('category_stats', {})
    
    all_categories = set(old_cats.keys()) | set(new_cats.keys())
    for category in sorted(all_categories):
        old_rate = old_cats.get(category, {}).get('pass_rate', 0)
        new_rate = new_cats.get(category, {}).get('pass_rate', 0)
        change = calculate_improvement(old_rate, new_rate)
        change_icon = "📈" if "+" in change else "📉" if "-" in change else "➡️"
        print(f"{change_icon} {category}: {old_rate:.1f}% → {new_rate:.1f}% ({change})")
    
    # Общий вывод
    print("\n🎯 ОБЩИЙ АНАЛИЗ:")
    print("-" * 30)
    
    improvements = 0
    degradations = 0
    
    for metric_data in comparison.values():
        if "+" in metric_data['change']:
            improvements += 1
        elif "-" in metric_data['change']:
            degradations += 1
    
    if improvements > degradations:
        print("✅ Общее улучшение качества поиска")
    elif degradations > improvements:
        print("⚠️ Общее ухудшение качества поиска")
    else:
        print("➡️ Качество поиска осталось на том же уровне")
    
    print(f"📈 Улучшений: {improvements}")
    print(f"📉 Ухудшений: {degradations}")

def print_history_list(history: List[Dict]):
    """Выводит список всех записей в истории"""
    print("📋 ИСТОРИЯ ТЕСТОВ:")
    print("=" * 60)
    
    for i, result in enumerate(history):
        timestamp = format_timestamp(result['timestamp'])
        summary = result['summary']
        pass_rate = summary.get('pass_rate', 0)
        avg_score = summary.get('avg_composite_score', summary.get('avg_score', 0))
        
        commit = result.get('git_commit', 'unknown')[:8]
        branch = result.get('branch', 'unknown')
        
        status_icon = "✅" if pass_rate >= 80 else "⚠️" if pass_rate >= 70 else "❌"
        
        print(f"{i:2d}. {status_icon} {timestamp} | {pass_rate:.1f}% | {avg_score:.1f} | {commit} ({branch})")

def main():
    """Главная функция"""
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python compare_search_versions.py list                    # показать историю")
        print("  python compare_search_versions.py compare <old_idx> <new_idx>  # сравнить версии")
        print("Пример: python compare_search_versions.py compare 0 1")
        return 1
    
    history = load_history()
    if not history:
        print("❌ Файл истории не найден или пуст")
        return 1
    
    command = sys.argv[1]
    
    if command == "list":
        print_history_list(history)
    elif command == "compare":
        if len(sys.argv) != 4:
            print("❌ Для команды compare нужно указать 2 индекса")
            print("Пример: python compare_search_versions.py compare 0 1")
            return 1
        
        try:
            old_idx = int(sys.argv[2])
            new_idx = int(sys.argv[3])
            print_comparison_report(history, [old_idx, new_idx])
        except ValueError:
            print("❌ Индексы должны быть числами")
            return 1
    else:
        print(f"❌ Неизвестная команда: {command}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
