"""
Автотесты для системы поиска
Проверяют релевантность и качество ранжирования результатов поиска
"""

import asyncio
import json
import time
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from app.opensearch_client import client
from app.build_query import build_flat_query, build_nested_query
from app.main import merge_hits
from app.postprocess_hits import postprocess_hits, apply_diversity
from app.utils import coalesce, transliterate, local_changer, detect_publication_type, extract_clean_query
from app.typo_client import fix_typo
from app.logger_config import setup_logger
from app.search_metrics import AdvancedSearchEvaluator, SearchMetrics, format_metrics_report

logger = setup_logger("search_tests")

@dataclass
class TestCase:
    """Тестовый случай для поиска"""
    query: str
    description: str
    expected_titles: List[str]  # Ожидаемые заголовки в топе
    expected_in_top: int = 10   # В каком топе должны быть результаты
    min_score_threshold: float = 100.0  # Минимальный скор для релевантных результатов

@dataclass
class TestResult:
    """Результат выполнения теста"""
    query: str
    description: str
    passed: bool
    score: float  # Метрика качества (0-100%)
    found_positions: Dict[str, int]  # Позиции найденных ожидаемых результатов
    total_results: int
    execution_time: float
    details: str
    # Новые расширенные метрики
    advanced_metrics: SearchMetrics = None
    composite_score: float = 0.0

# Тестовые данные на основе коллекций
TEST_CASES = [
    # Московское метро
    TestCase(
        query="Московское метро",
        description="Поиск по точному названию коллекции",
        expected_titles=[
            "Московское метро",
            "Московский метрополитен", 
            "История московского метро",
            "Метро Москвы"
        ]
    ),
    TestCase(
        query="Московский метрополитен", 
        description="Альтернативное название метро",
        expected_titles=[
            "Московский метрополитен",
            "Московское метро",
            "История московского метро"
        ]
    ),
    TestCase(
        query="История метро",
        description="Тематический поиск по метро",
        expected_titles=[
            "История московского метро",
            "Московское метро",
            "Московский метрополитен"
        ]
    ),
    TestCase(
        query="Первая линия московского метро",
        description="Специфический запрос о первой линии",
        expected_titles=[
            "История московского метро",
            "Первая линия метро",
            "Московское метро"
        ]
    ),
    TestCase(
        query="Первая станция московского метро", 
        description="Запрос о первой станции",
        expected_titles=[
            "История московского метро",
            "Московское метро",
            "Сокольники"
        ]
    ),

    # Слово о полку Игореве  
    TestCase(
        query="Слово о полку Игореве",
        description="Классическое произведение - точное название",
        expected_titles=[
            "Слово о полку Игореве",
            "Слово о походе Игоревом",
            "Игорь"
        ]
    ),
    TestCase(
        query="Князь Игорь",
        description="Поиск по главному герою",
        expected_titles=[
            "Слово о полку Игореве",
            "Князь Игорь",
            "Игорь"
        ]
    ),
    TestCase(
        query="Поход на половцев",
        description="Тематический поиск по сюжету",
        expected_titles=[
            "Слово о полку Игореве",
            "Поход Игоря",
            "Половцы"
        ]
    ),
    TestCase(
        query="Мусин-Пушкин",
        description="Поиск по исследователю памятника",
        expected_titles=[
            "Слово о полку Игореве",
            "Мусин-Пушкин",
            "Рукопись"
        ]
    ),
    TestCase(
        query="Рукопись Мусина-Пушкина",
        description="Специфический запрос о рукописи",
        expected_titles=[
            "Слово о полку Игореве",
            "Мусин-Пушкин",
            "Рукопись"
        ]
    ),

    # Палех
    TestCase(
        query="Искусство палеха",
        description="Тематический поиск по палехскому искусству",
        expected_titles=[
            "Палех",
            "Искусство Палеха",
            "Палехская миниатюра"
        ]
    ),
    TestCase(
        query="Палешане", 
        description="Поиск по жителям Палеха",
        expected_titles=[
            "Палех",
            "Палешане",
            "Искусство Палеха"
        ]
    ),
    TestCase(
        query="Палехская миниатюра",
        description="Специфический вид искусства",
        expected_titles=[
            "Палехская миниатюра",
            "Палех",
            "Миниатюра"
        ]
    ),

    # Дополнительные тесты для проверки системы
    TestCase(
        query="Архитектурные памятники Москвы",
        description="Тест на улучшенное ранжирование заголовков",
        expected_titles=[
            "Архитектурные памятники Москвы",
            "Памятники Москвы",
            "Архитектура Москвы"
        ],
        expected_in_top=5  # Должно быть в топ-5
    ),
    TestCase(
        query="Маяковский открытка",
        description="Тест распознавания типа издания",
        expected_titles=[
            "Маяковский",
            "В. В. Маяковский",
            "Дом в селе Маяковски"
        ]
    ),
]

class SearchQualityTester:
    """Класс для тестирования качества поиска"""
    
    def __init__(self, index_name: str = "my-books-index"):
        self.index_name = index_name
        self.results: List[TestResult] = []
        self.evaluator = AdvancedSearchEvaluator()
    
    async def run_search(self, query: str) -> Tuple[List[Dict], float]:
        """Выполняет поиск и возвращает результаты с временем выполнения"""
        start_time = time.time()
        
        try:
            # Обработка запроса как в main.py
            publication_types = detect_publication_type(query)
            clean_query = extract_clean_query(query)
            query_list = coalesce(clean_query, transliterate(clean_query), local_changer(clean_query), fix_typo(clean_query))
            
            # Выполнение поисковых запросов
            flat_query = build_flat_query(query_list, None, None)
            nested_query = build_nested_query(query_list, None, None)
            
            flat_resp = client.search(index=self.index_name, body=flat_query)
            nested_resp = client.search(index=self.index_name, body=nested_query)
            
            # Объединение результатов
            combined_hits = merge_hits(flat_resp["hits"]["hits"], nested_resp["hits"]["hits"])
            results = postprocess_hits({"hits": {"hits": combined_hits}}, require_inner_hits=False)
            results = apply_diversity(results, max_per_type=6)
            
            execution_time = time.time() - start_time
            return results, execution_time
            
        except Exception as e:
            logger.error(f"Ошибка при выполнении поиска '{query}': {e}")
            execution_time = time.time() - start_time
            return [], execution_time
    
    def calculate_test_score(self, test_case: TestCase, results: List[Dict]) -> Tuple[float, Dict[str, int], str]:
        """Вычисляет метрику качества для тестового случая"""
        found_positions = {}
        details_parts = []
        
        # Ищем ожидаемые заголовки в результатах
        for i, result in enumerate(results[:test_case.expected_in_top], 1):
            title = result.get('title', '').lower()
            book_name = result.get('book_name', '').lower()
            
            for expected_title in test_case.expected_titles:
                expected_lower = expected_title.lower()
                
                # Проверяем точное совпадение или частичное включение
                if (expected_lower in title or expected_lower in book_name or
                    any(word in title or word in book_name for word in expected_lower.split() if len(word) > 3)):
                    
                    if expected_title not in found_positions:
                        found_positions[expected_title] = i
                        details_parts.append(f"✓ '{expected_title}' найден на позиции {i}")
        
        # Вычисляем скор
        if not test_case.expected_titles:
            return 100.0, found_positions, "Нет ожидаемых результатов"
        
        # Базовый скор за найденные результаты
        found_count = len(found_positions)
        expected_count = len(test_case.expected_titles)
        base_score = (found_count / expected_count) * 100
        
        # Бонус за позиции в топе
        position_bonus = 0
        for expected_title, position in found_positions.items():
            if position <= 3:
                position_bonus += 20  # Топ-3
            elif position <= 5:
                position_bonus += 10  # Топ-5
            elif position <= test_case.expected_in_top:
                position_bonus += 5   # В пределах ожидаемого топа
        
        # Штраф за отсутствующие результаты
        missing_count = expected_count - found_count
        for i, expected_title in enumerate(test_case.expected_titles):
            if expected_title not in found_positions:
                details_parts.append(f"✗ '{expected_title}' НЕ НАЙДЕН")
        
        final_score = min(100.0, base_score + position_bonus)
        details = "; ".join(details_parts) if details_parts else "Нет совпадений"
        
        return final_score, found_positions, details
    
    async def run_test(self, test_case: TestCase) -> TestResult:
        """Выполняет один тест"""
        logger.info(f"Выполняется тест: {test_case.description}")
        
        results, execution_time = await self.run_search(test_case.query)
        score, found_positions, details = self.calculate_test_score(test_case, results)
        
        # Определяем категорию теста
        category = "general"
        if "метро" in test_case.query.lower():
            category = "metro"
        elif any(word in test_case.query.lower() for word in ["игор", "полк", "мусин"]):
            category = "literature"
        elif "палех" in test_case.query.lower():
            category = "art"
        elif any(word in test_case.query.lower() for word in ["архитектур", "маяковский"]):
            category = "system_test"
        
        # Вычисляем расширенные метрики
        advanced_metrics = self.evaluator.evaluate_search_quality(
            query=test_case.query,
            results=results,
            expected_titles=test_case.expected_titles,
            execution_time=execution_time,
            category=category
        )
        
        composite_score = self.evaluator.calculate_composite_score(advanced_metrics)
        
        # Используем композитный скор для определения прохождения теста
        passed = composite_score >= 70.0 and len(found_positions) > 0
        
        test_result = TestResult(
            query=test_case.query,
            description=test_case.description,
            passed=passed,
            score=score,  # Оставляем старый скор для совместимости
            found_positions=found_positions,
            total_results=len(results),
            execution_time=execution_time,
            details=details,
            advanced_metrics=advanced_metrics,
            composite_score=composite_score
        )
        
        return test_result
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Выполняет все тесты и возвращает сводную статистику"""
        logger.info("🧪 Запуск автотестов системы поиска...")
        start_time = time.time()
        
        self.results = []
        for test_case in TEST_CASES:
            result = await self.run_test(test_case)
            self.results.append(result)
        
        total_time = time.time() - start_time
        
        # Вычисляем статистику
        passed_tests = sum(1 for r in self.results if r.passed)
        total_tests = len(self.results)
        pass_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        avg_score = sum(r.score for r in self.results) / total_tests if total_tests > 0 else 0
        avg_composite_score = sum(r.composite_score for r in self.results) / total_tests if total_tests > 0 else 0
        avg_execution_time = sum(r.execution_time for r in self.results) / total_tests if total_tests > 0 else 0
        
        # Агрегируем расширенные метрики
        all_metrics = [r.advanced_metrics for r in self.results if r.advanced_metrics]
        aggregated_metrics = self.evaluator.aggregate_metrics(all_metrics) if all_metrics else None
        
        # Группируем по категориям
        categories = {
            "Московское метро": [r for r in self.results if "метро" in r.query.lower()],
            "Слово о полку Игореве": [r for r in self.results if any(word in r.query.lower() for word in ["игор", "полк", "мусин"])],
            "Палех": [r for r in self.results if "палех" in r.query.lower()],
            "Системные тесты": [r for r in self.results if r not in sum([
                [r for r in self.results if "метро" in r.query.lower()],
                [r for r in self.results if any(word in r.query.lower() for word in ["игор", "полк", "мусин"])],
                [r for r in self.results if "палех" in r.query.lower()]
            ], [])]
        }
        
        category_stats = {}
        for category, tests in categories.items():
            if tests:
                category_passed = sum(1 for t in tests if t.passed)
                category_avg_score = sum(t.score for t in tests) / len(tests)
                category_stats[category] = {
                    "passed": category_passed,
                    "total": len(tests),
                    "pass_rate": (category_passed / len(tests)) * 100,
                    "avg_score": category_avg_score
                }
        
        summary = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "pass_rate": pass_rate,
            "avg_score": avg_score,
            "avg_composite_score": avg_composite_score,
            "avg_execution_time": avg_execution_time,
            "total_execution_time": total_time,
            "category_stats": category_stats,
            "aggregated_metrics": {
                "precision_at_5": aggregated_metrics.precision_at_k.get(5, 0.0) if aggregated_metrics else 0.0,
                "ndcg_at_5": aggregated_metrics.ndcg_at_k.get(5, 0.0) if aggregated_metrics else 0.0,
                "mrr": aggregated_metrics.mrr if aggregated_metrics else 0.0,
                "title_match_score": aggregated_metrics.title_match_score if aggregated_metrics else 0.0,
                "diversity_score": aggregated_metrics.diversity_score if aggregated_metrics else 0.0,
                "speed_score": aggregated_metrics.speed_score if aggregated_metrics else 0.0
            },
            "failed_tests_details": [
                {
                    "query": r.query,
                    "description": r.description,
                    "score": r.score,
                    "composite_score": r.composite_score,
                    "details": r.details
                }
                for r in self.results if not r.passed
            ]
        }
        
        return summary
    
    def print_results(self, summary: Dict[str, Any]):
        """Выводит результаты тестов в консоль"""
        print("\n" + "="*80)
        print("🧪 РЕЗУЛЬТАТЫ АВТОТЕСТОВ СИСТЕМЫ ПОИСКА")
        print("="*80)
        
        print(f"📊 Общая статистика:")
        print(f"   • Всего тестов: {summary['total_tests']}")
        print(f"   • Пройдено: {summary['passed_tests']} ✅")
        print(f"   • Провалено: {summary['failed_tests']} ❌")
        print(f"   • Процент прохождения: {summary['pass_rate']:.1f}%")
        print(f"   • Средний скор качества: {summary['avg_score']:.1f}/100")
        print(f"   • Композитный скор: {summary['avg_composite_score']:.1f}/100")
        print(f"   • Среднее время выполнения: {summary['avg_execution_time']:.3f}с")
        print(f"   • Общее время тестирования: {summary['total_execution_time']:.1f}с")
        
        # Расширенные метрики
        metrics = summary['aggregated_metrics']
        print(f"\n🎯 Расширенные метрики:")
        print(f"   • Precision@5: {metrics['precision_at_5']:.3f}")
        print(f"   • NDCG@5: {metrics['ndcg_at_5']:.3f}")
        print(f"   • MRR: {metrics['mrr']:.3f}")
        print(f"   • Title Match: {metrics['title_match_score']:.3f}")
        print(f"   • Diversity: {metrics['diversity_score']:.3f}")
        print(f"   • Speed: {metrics['speed_score']:.3f}")
        
        print(f"\n📈 Статистика по категориям:")
        for category, stats in summary['category_stats'].items():
            status = "✅" if stats['pass_rate'] >= 70 else "⚠️" if stats['pass_rate'] >= 50 else "❌"
            print(f"   {status} {category}: {stats['passed']}/{stats['total']} ({stats['pass_rate']:.1f}%, скор: {stats['avg_score']:.1f})")
        
        if summary['failed_tests_details']:
            print(f"\n❌ Детали проваленных тестов:")
            for i, test in enumerate(summary['failed_tests_details'], 1):
                print(f"   {i}. '{test['query']}' (скор: {test['score']:.1f}, композитный: {test['composite_score']:.1f})")
                print(f"      {test['description']}")
                print(f"      {test['details']}")
        
        # Общая оценка системы
        if summary['pass_rate'] >= 80:
            grade = "🟢 ОТЛИЧНО"
        elif summary['pass_rate'] >= 70:
            grade = "🟡 ХОРОШО"
        elif summary['pass_rate'] >= 50:
            grade = "🟠 УДОВЛЕТВОРИТЕЛЬНО"
        else:
            grade = "🔴 ТРЕБУЕТ УЛУЧШЕНИЯ"
        
        print(f"\n🎯 Общая оценка системы поиска: {grade}")
        print("="*80)

async def run_search_tests():
    """Основная функция для запуска тестов"""
    tester = SearchQualityTester()
    summary = await tester.run_all_tests()
    tester.print_results(summary)
    return summary

if __name__ == "__main__":
    asyncio.run(run_search_tests())
