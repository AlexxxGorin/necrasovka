#!/usr/bin/env python3
"""
Скрипт для мониторинга качества поиска в CI/CD
Сохраняет результаты тестов в файл для отслеживания динамики
"""

import asyncio
import json
import sys
import os
from datetime import datetime

# Добавляем путь к модулям приложения
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.search_tests import run_search_tests

RESULTS_FILE = "search_quality_history.json"

def load_history():
    """Загружает историю результатов тестов"""
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []

def save_result(summary):
    """Сохраняет результат теста в историю"""
    history = load_history()
    
    # Добавляем метаинформацию
    result = {
        "timestamp": datetime.now().isoformat(),
        "git_commit": os.environ.get("GIT_COMMIT", "unknown"),
        "branch": os.environ.get("GIT_BRANCH", "unknown"),
        "summary": summary
    }
    
    history.append(result)
    
    # Храним только последние 50 результатов
    history = history[-50:]
    
    with open(RESULTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=2, ensure_ascii=False)

def analyze_trends(history):
    """Анализирует тренды качества поиска"""
    if len(history) < 2:
        return "Недостаточно данных для анализа трендов"
    
    current = history[-1]["summary"]
    previous = history[-2]["summary"]
    
    pass_rate_change = current["pass_rate"] - previous["pass_rate"]
    score_change = current["avg_score"] - previous["avg_score"]
    
    trend_msg = []
    
    if pass_rate_change > 0:
        trend_msg.append(f"📈 Процент прохождения вырос на {pass_rate_change:.1f}%")
    elif pass_rate_change < 0:
        trend_msg.append(f"📉 Процент прохождения упал на {abs(pass_rate_change):.1f}%")
    else:
        trend_msg.append("➡️ Процент прохождения не изменился")
    
    if score_change > 0:
        trend_msg.append(f"📈 Средний скор вырос на {score_change:.1f}")
    elif score_change < 0:
        trend_msg.append(f"📉 Средний скор упал на {abs(score_change):.1f}")
    else:
        trend_msg.append("➡️ Средний скор не изменился")
    
    return "; ".join(trend_msg)

async def main():
    """Главная функция мониторинга"""
    print("🔍 Мониторинг качества поиска...")
    
    try:
        # Запускаем тесты
        summary = await run_search_tests()
        
        # Загружаем историю и анализируем тренды
        history = load_history()
        if history:
            trends = analyze_trends(history)
            print(f"\n📊 Тренды: {trends}")
        
        # Сохраняем результат
        save_result(summary)
        
        # Выводим краткую сводку для CI/CD
        print(f"\n📋 Краткая сводка:")
        print(f"   Пройдено тестов: {summary['passed_tests']}/{summary['total_tests']}")
        print(f"   Процент прохождения: {summary['pass_rate']:.1f}%")
        print(f"   Средний скор: {summary['avg_score']:.1f}/100")
        
        # Определяем код выхода
        if summary['pass_rate'] >= 80:
            print("✅ Качество поиска отличное!")
            return 0
        elif summary['pass_rate'] >= 70:
            print("⚠️ Качество поиска хорошее, но есть место для улучшений")
            return 0
        elif summary['pass_rate'] >= 50:
            print("⚠️ Качество поиска удовлетворительное, требуются улучшения")
            return 1
        else:
            print("❌ Качество поиска неудовлетворительное!")
            return 2
            
    except Exception as e:
        print(f"💥 Ошибка при мониторинге: {e}")
        return 3

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
