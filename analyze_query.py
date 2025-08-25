#!/usr/bin/env python3
"""
Инструмент для детального анализа качества отдельного поискового запроса
Использование: python analyze_query.py "ваш запрос"
"""

import asyncio
import sys
import os

# Добавляем путь к модулям приложения
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.search_tests import SearchQualityTester
from app.search_metrics import format_metrics_report

async def analyze_single_query(query: str, expected_titles: list = None):
    """Анализирует качество одного запроса"""
    if expected_titles is None:
        expected_titles = []
    
    print(f"🔍 Анализ запроса: '{query}'")
    print("=" * 60)
    
    tester = SearchQualityTester()
    
    try:
        # Выполняем поиск
        results, execution_time = await tester.run_search(query)
        
        if not results:
            print("❌ Результаты не найдены")
            return
        
        print(f"⏱️ Время выполнения: {execution_time:.3f}с")
        print(f"📊 Найдено результатов: {len(results)}")
        print()
        
        # Показываем топ-10 результатов
        print("🎯 Топ-10 результатов:")
        for i, result in enumerate(results[:10], 1):
            title = result.get('title', 'Без названия')
            score = result.get('score', 0)
            matched_by = result.get('matched_by', 'unknown')
            path_index = result.get('path_index', 'unknown')
            
            print(f"   {i:2d}. {title[:80]}")
            print(f"       Скор: {score:.1f} | Тип: {matched_by} | Источник: {path_index}")
            
            # Показываем highlights если есть
            highlight = result.get('highlight', {})
            if highlight:
                for field, highlights in highlight.items():
                    if highlights:
                        snippet = highlights[0][:100] + "..." if len(highlights[0]) > 100 else highlights[0]
                        print(f"       {field}: {snippet}")
            print()
        
        # Если есть ожидаемые результаты, вычисляем метрики
        if expected_titles:
            print("📈 Расширенные метрики:")
            print("-" * 30)
            
            # Вычисляем расширенные метрики
            advanced_metrics = tester.evaluator.evaluate_search_quality(
                query=query,
                results=results,
                expected_titles=expected_titles,
                execution_time=execution_time
            )
            
            # Выводим подробный отчет
            report = format_metrics_report(advanced_metrics, query)
            print(report)
            
            composite_score = tester.evaluator.calculate_composite_score(advanced_metrics)
            print(f"\n🎯 Композитный скор качества: {composite_score:.1f}/100")
            
            # Анализ найденных ожидаемых результатов
            print(f"\n🔎 Анализ ожидаемых результатов:")
            for expected in expected_titles:
                found = False
                for i, result in enumerate(results[:20], 1):
                    title = result.get('title', '').lower()
                    book_name = result.get('book_name', '').lower()
                    
                    if (expected.lower() in title or expected.lower() in book_name or
                        any(word in title or word in book_name for word in expected.lower().split() if len(word) > 3)):
                        print(f"   ✅ '{expected}' найден на позиции {i}")
                        found = True
                        break
                
                if not found:
                    print(f"   ❌ '{expected}' НЕ НАЙДЕН в топ-20")
        
        else:
            print("💡 Подсказка: Добавьте ожидаемые результаты для получения метрик качества")
            print("   Пример: python analyze_query.py 'московское метро' 'Московское метро,История метро'")
        
    except Exception as e:
        print(f"💥 Ошибка при анализе: {e}")
        return 1
    
    return 0

def main():
    """Главная функция"""
    if len(sys.argv) < 2:
        print("Использование: python analyze_query.py 'запрос' ['ожидаемый1,ожидаемый2']")
        print("Пример: python analyze_query.py 'Архитектурные памятники Москвы'")
        print("Пример с ожидаемыми результатами:")
        print("  python analyze_query.py 'московское метро' 'Московское метро,История метро'")
        return 1
    
    query = sys.argv[1]
    expected_titles = []
    
    if len(sys.argv) > 2:
        expected_titles = [title.strip() for title in sys.argv[2].split(',')]
    
    return asyncio.run(analyze_single_query(query, expected_titles))

if __name__ == "__main__":
    sys.exit(main())
