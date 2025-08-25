"""
Расширенные метрики качества поиска
Включает различные алгоритмы оценки релевантности
"""

import math
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class SearchMetrics:
    """Метрики качества поиска"""
    # Основные метрики
    precision_at_k: Dict[int, float]  # P@K для разных K
    recall_at_k: Dict[int, float]     # R@K для разных K
    ndcg_at_k: Dict[int, float]       # NDCG@K для разных K
    
    # Дополнительные метрики
    mrr: float                        # Mean Reciprocal Rank
    map_score: float                  # Mean Average Precision
    
    # Пользовательские метрики
    title_match_score: float          # Скор совпадений в заголовках
    diversity_score: float            # Разнообразие результатов
    speed_score: float                # Скор скорости ответа
    
    # Категориальные метрики
    category_scores: Dict[str, float] # Скоры по категориям

class AdvancedSearchEvaluator:
    """Продвинутый оценщик качества поиска"""
    
    def __init__(self):
        self.relevance_levels = {
            "perfect": 3,      # Точное совпадение
            "excellent": 2,    # Очень релевантно
            "good": 1,         # Релевантно
            "irrelevant": 0    # Нерелевантно
        }
    
    def calculate_precision_at_k(self, relevant_items: List[bool], k: int) -> float:
        """Вычисляет Precision@K"""
        if k == 0 or len(relevant_items) == 0:
            return 0.0
        
        top_k = relevant_items[:k]
        return sum(top_k) / len(top_k)
    
    def calculate_recall_at_k(self, relevant_items: List[bool], total_relevant: int, k: int) -> float:
        """Вычисляет Recall@K"""
        if total_relevant == 0 or k == 0:
            return 0.0
        
        top_k = relevant_items[:k]
        return sum(top_k) / total_relevant
    
    def calculate_ndcg_at_k(self, relevance_scores: List[int], k: int) -> float:
        """Вычисляет NDCG@K (Normalized Discounted Cumulative Gain)"""
        if k == 0 or not relevance_scores:
            return 0.0
        
        # DCG@K
        dcg = 0.0
        for i, score in enumerate(relevance_scores[:k]):
            if score > 0:
                dcg += score / math.log2(i + 2)  # +2 потому что log2(1) = 0
        
        # IDCG@K (идеальный DCG)
        ideal_scores = sorted(relevance_scores, reverse=True)
        idcg = 0.0
        for i, score in enumerate(ideal_scores[:k]):
            if score > 0:
                idcg += score / math.log2(i + 2)
        
        return dcg / idcg if idcg > 0 else 0.0
    
    def calculate_mrr(self, first_relevant_positions: List[int]) -> float:
        """Вычисляет Mean Reciprocal Rank"""
        if not first_relevant_positions:
            return 0.0
        
        reciprocal_ranks = []
        for pos in first_relevant_positions:
            if pos > 0:
                reciprocal_ranks.append(1.0 / pos)
            else:
                reciprocal_ranks.append(0.0)
        
        return sum(reciprocal_ranks) / len(reciprocal_ranks)
    
    def calculate_map(self, relevant_items_per_query: List[List[bool]]) -> float:
        """Вычисляет Mean Average Precision"""
        if not relevant_items_per_query:
            return 0.0
        
        average_precisions = []
        for relevant_items in relevant_items_per_query:
            if not any(relevant_items):
                average_precisions.append(0.0)
                continue
            
            precisions = []
            relevant_count = 0
            
            for i, is_relevant in enumerate(relevant_items):
                if is_relevant:
                    relevant_count += 1
                    precision = relevant_count / (i + 1)
                    precisions.append(precision)
            
            if precisions:
                average_precisions.append(sum(precisions) / len(precisions))
            else:
                average_precisions.append(0.0)
        
        return sum(average_precisions) / len(average_precisions)
    
    def calculate_title_match_score(self, results: List[Dict], expected_titles: List[str]) -> float:
        """Оценивает качество совпадений в заголовках"""
        if not expected_titles or not results:
            return 0.0
        
        title_scores = []
        for expected in expected_titles:
            best_score = 0.0
            expected_words = set(expected.lower().split())
            
            for i, result in enumerate(results[:10]):  # Смотрим только топ-10
                title = result.get('title', '').lower()
                book_name = result.get('book_name', '').lower()
                
                # Точное совпадение
                if expected.lower() in title or expected.lower() in book_name:
                    score = 3.0 / (i + 1)  # Буст за позицию
                # Частичное совпадение по словам
                elif expected_words.intersection(set(title.split() + book_name.split())):
                    word_overlap = len(expected_words.intersection(set(title.split() + book_name.split())))
                    score = (word_overlap / len(expected_words)) * 2.0 / (i + 1)
                else:
                    score = 0.0
                
                best_score = max(best_score, score)
            
            title_scores.append(best_score)
        
        return sum(title_scores) / len(title_scores) if title_scores else 0.0
    
    def calculate_diversity_score(self, results: List[Dict]) -> float:
        """Оценивает разнообразие результатов"""
        if not results:
            return 0.0
        
        # Группируем по path_index (типу источника)
        path_counts = defaultdict(int)
        for result in results[:20]:  # Смотрим топ-20
            path_counts[result.get('path_index', 'unknown')] += 1
        
        # Вычисляем энтропию Шеннона
        total = sum(path_counts.values())
        if total <= 1:
            return 0.0
        
        entropy = 0.0
        for count in path_counts.values():
            if count > 0:
                p = count / total
                entropy -= p * math.log2(p)
        
        # Нормализуем к [0, 1]
        max_entropy = math.log2(min(len(path_counts), total))
        return entropy / max_entropy if max_entropy > 0 else 0.0
    
    def calculate_speed_score(self, execution_time: float) -> float:
        """Оценивает скорость выполнения запроса"""
        # Логарифмическая шкала: быстрые запросы получают высокий скор
        if execution_time <= 0:
            return 1.0
        
        # Идеальное время: 0.5с = 1.0, 2с = 0.5, 5с = 0.2
        return max(0.0, min(1.0, 1.0 / (1.0 + execution_time)))
    
    def evaluate_search_quality(self, 
                               query: str,
                               results: List[Dict], 
                               expected_titles: List[str],
                               execution_time: float,
                               category: str = "general") -> SearchMetrics:
        """Комплексная оценка качества поиска"""
        
        # Определяем релевантность каждого результата
        relevance_scores = []
        relevant_items = []
        
        for i, result in enumerate(results[:20]):  # Анализируем топ-20
            title = result.get('title', '').lower()
            book_name = result.get('book_name', '').lower()
            
            # Определяем уровень релевантности
            relevance = 0
            is_relevant = False
            
            for expected in expected_titles:
                expected_lower = expected.lower()
                expected_words = set(expected_lower.split())
                result_words = set(title.split() + book_name.split())
                
                # Точное совпадение
                if expected_lower in title or expected_lower in book_name:
                    relevance = max(relevance, 3)
                    is_relevant = True
                # Высокое частичное совпадение
                elif len(expected_words.intersection(result_words)) >= len(expected_words) * 0.8:
                    relevance = max(relevance, 2)
                    is_relevant = True
                # Среднее частичное совпадение
                elif len(expected_words.intersection(result_words)) >= len(expected_words) * 0.5:
                    relevance = max(relevance, 1)
                    is_relevant = True
            
            relevance_scores.append(relevance)
            relevant_items.append(is_relevant)
        
        # Вычисляем метрики для разных K
        k_values = [1, 3, 5, 10, 20]
        precision_at_k = {}
        recall_at_k = {}
        ndcg_at_k = {}
        
        total_relevant = len(expected_titles)
        
        for k in k_values:
            precision_at_k[k] = self.calculate_precision_at_k(relevant_items, k)
            recall_at_k[k] = self.calculate_recall_at_k(relevant_items, total_relevant, k)
            ndcg_at_k[k] = self.calculate_ndcg_at_k(relevance_scores, k)
        
        # MRR - позиция первого релевантного результата
        first_relevant_pos = 0
        for i, is_relevant in enumerate(relevant_items):
            if is_relevant:
                first_relevant_pos = i + 1
                break
        
        mrr = 1.0 / first_relevant_pos if first_relevant_pos > 0 else 0.0
        
        # MAP - для одного запроса это просто AP
        map_score = self.calculate_map([relevant_items])
        
        # Дополнительные метрики
        title_match_score = self.calculate_title_match_score(results, expected_titles)
        diversity_score = self.calculate_diversity_score(results)
        speed_score = self.calculate_speed_score(execution_time)
        
        return SearchMetrics(
            precision_at_k=precision_at_k,
            recall_at_k=recall_at_k,
            ndcg_at_k=ndcg_at_k,
            mrr=mrr,
            map_score=map_score,
            title_match_score=title_match_score,
            diversity_score=diversity_score,
            speed_score=speed_score,
            category_scores={category: (precision_at_k[5] + ndcg_at_k[5]) / 2}
        )
    
    def aggregate_metrics(self, metrics_list: List[SearchMetrics]) -> SearchMetrics:
        """Агрегирует метрики по множеству запросов"""
        if not metrics_list:
            return SearchMetrics(
                precision_at_k={}, recall_at_k={}, ndcg_at_k={},
                mrr=0.0, map_score=0.0, title_match_score=0.0,
                diversity_score=0.0, speed_score=0.0, category_scores={}
            )
        
        n = len(metrics_list)
        
        # Агрегируем precision@k
        k_values = list(metrics_list[0].precision_at_k.keys())
        precision_at_k = {}
        recall_at_k = {}
        ndcg_at_k = {}
        
        for k in k_values:
            precision_at_k[k] = sum(m.precision_at_k[k] for m in metrics_list) / n
            recall_at_k[k] = sum(m.recall_at_k[k] for m in metrics_list) / n
            ndcg_at_k[k] = sum(m.ndcg_at_k[k] for m in metrics_list) / n
        
        # Агрегируем остальные метрики
        mrr = sum(m.mrr for m in metrics_list) / n
        map_score = sum(m.map_score for m in metrics_list) / n
        title_match_score = sum(m.title_match_score for m in metrics_list) / n
        diversity_score = sum(m.diversity_score for m in metrics_list) / n
        speed_score = sum(m.speed_score for m in metrics_list) / n
        
        # Агрегируем категориальные метрики
        category_scores = defaultdict(list)
        for m in metrics_list:
            for category, score in m.category_scores.items():
                category_scores[category].append(score)
        
        aggregated_category_scores = {}
        for category, scores in category_scores.items():
            aggregated_category_scores[category] = sum(scores) / len(scores)
        
        return SearchMetrics(
            precision_at_k=precision_at_k,
            recall_at_k=recall_at_k,
            ndcg_at_k=ndcg_at_k,
            mrr=mrr,
            map_score=map_score,
            title_match_score=title_match_score,
            diversity_score=diversity_score,
            speed_score=speed_score,
            category_scores=aggregated_category_scores
        )
    
    def calculate_composite_score(self, metrics: SearchMetrics) -> float:
        """Вычисляет композитный скор качества"""
        # Веса для разных компонентов
        weights = {
            'precision': 0.25,
            'ndcg': 0.25,
            'title_match': 0.20,
            'mrr': 0.15,
            'diversity': 0.10,
            'speed': 0.05
        }
        
        score = (
            weights['precision'] * metrics.precision_at_k.get(5, 0.0) * 100 +
            weights['ndcg'] * metrics.ndcg_at_k.get(5, 0.0) * 100 +
            weights['title_match'] * metrics.title_match_score * 100 +
            weights['mrr'] * metrics.mrr * 100 +
            weights['diversity'] * metrics.diversity_score * 100 +
            weights['speed'] * metrics.speed_score * 100
        )
        
        return min(100.0, score)

def format_metrics_report(metrics: SearchMetrics, query: str = "") -> str:
    """Форматирует отчет по метрикам"""
    report = []
    
    if query:
        report.append(f"📊 Метрики для запроса: '{query}'")
        report.append("=" * 50)
    
    # Precision@K
    report.append("🎯 Precision@K:")
    for k, score in sorted(metrics.precision_at_k.items()):
        report.append(f"   P@{k}: {score:.3f}")
    
    # NDCG@K
    report.append("\n🏆 NDCG@K:")
    for k, score in sorted(metrics.ndcg_at_k.items()):
        report.append(f"   NDCG@{k}: {score:.3f}")
    
    # Остальные метрики
    report.append(f"\n⚡ MRR: {metrics.mrr:.3f}")
    report.append(f"📈 MAP: {metrics.map_score:.3f}")
    report.append(f"📝 Title Match: {metrics.title_match_score:.3f}")
    report.append(f"🎨 Diversity: {metrics.diversity_score:.3f}")
    report.append(f"🚀 Speed: {metrics.speed_score:.3f}")
    
    if metrics.category_scores:
        report.append("\n📂 По категориям:")
        for category, score in metrics.category_scores.items():
            report.append(f"   {category}: {score:.3f}")
    
    return "\n".join(report)
