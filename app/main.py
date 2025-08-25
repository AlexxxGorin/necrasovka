from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from app.opensearch_client import client
from app.typo_client import fix_typo
from app.utils import transliterate, local_changer, coalesce, detect_publication_type, extract_clean_query
from app.postprocess_hits import postprocess_hits, apply_diversity
from app.logger_config import setup_logger
from app.config import settings
import time
import uvicorn
import asyncio
from app.build_query import build_flat_query, build_nested_query  # добавь nested
from app.interaction_logger import log_interaction

logger = setup_logger("search_service")

app = FastAPI(
    title="FastAPI OpenSearch Service",
    description="Сервис поиска по индексу OpenSearch",
    version="0.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Запуск автотестов при старте приложения
# Автотесты отключены для быстрого старта
# @app.on_event("startup")
# async def startup_event():
#     """Выполняется при запуске приложения"""
#     try:
#         from app.search_tests import run_search_tests
#         logger.info("🚀 Запуск автотестов системы поиска...")
#         await run_search_tests()
#     except Exception as e:
#         logger.warning(f"⚠️ Не удалось выполнить автотесты: {e}")
#         logger.info("Приложение продолжит работу без автотестов")


@app.get("/", tags=["Health"])
async def health_check():
    return {"status": "ok"}


@app.get("/test-search", tags=["Testing"])
async def run_search_quality_tests():
    """Запуск автотестов системы поиска вручную"""
    try:
        from app.search_tests import run_search_tests
        logger.info("🧪 Запуск автотестов по API запросу...")
        summary = await run_search_tests()
        return {
            "status": "completed",
            "summary": summary
        }
    except Exception as e:
        logger.error(f"❌ Ошибка при выполнении автотестов: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка автотестов: {str(e)}")


def merge_hits(flat_hits, nested_hits):
    combined = {}

    for hit in flat_hits:
        _id = hit["_id"]
        combined[_id] = {
            "hit": hit,
            "from_flat": True,
            "from_nested": False
        }

    for hit in nested_hits:
        _id = hit["_id"]
        if _id in combined:
            combined[_id]["from_nested"] = True
            # добавляем inner_hits
            combined[_id]["hit"]["inner_hits"] = hit.get("inner_hits")
        else:
            combined[_id] = {
                "hit": hit,
                "from_flat": False,
                "from_nested": True
            }

    merged: list[dict] = []
    for meta in combined.values():
        hit = meta["hit"]
        if meta["from_flat"] and meta["from_nested"]:
            mb = "both"
        elif meta["from_nested"]:
            mb = "nested"
        else:
            mb = "flat"
        # кладём в _source, чтобы постпроцесс и UI его увидели
        hit["_source"]["matched_by"] = mb
        merged.append(hit)

    def scoring_key(hit):
        mb = hit["_source"].get("matched_by", "")
        score = hit.get("_score", 0)
        
        # Проверяем, есть ли все слова запроса в заголовке
        title = hit["_source"].get("title", "").lower()
        book_name = hit["_source"].get("book_name", "").lower()
        
        # Получаем оригинальный запрос из контекста (если доступен)
        # Пока используем простую эвристику
        
        if mb == "nested":
            # Nested результаты (с совпадениями в тексте) получают буст
            score *= 1.4
        elif mb == "both":
            # Результаты из обоих источников - максимальный буст
            score *= 1.6
        elif mb == "flat":
            # Flat результаты получают буст только если скор действительно высокий
            # Это означает хорошее совпадение в заголовке
            if score > 200:  # Повышаем порог для flat буста
                score *= 1.2
            else:
                # Понижаем приоритет частичных совпадений в заголовках
                score *= 0.9

        return score

    return sorted(merged, key=scoring_key, reverse=True)



likes = []

@app.post("/like", tags=["Feedback"])
async def like_card(
    doc_id: str = Body(..., embed=True),
    query: str = Body(..., embed=True)
):
    logger.info(f"❤️ Лайк получен: doc_id={doc_id}, query='{query}'")
    log_interaction(query=query, result_ids=[], doc_id=doc_id)
    return {"status": "ok"}

@app.get("/search", tags=["Search"])
async def search(
    index: str = Query(...),
    q: str = Query(...),
    start_year: int = Query(None, ge=1000, le=2100),
    end_year: int = Query(None, ge=1000, le=2100),
    diversity: bool = Query(False),  # опциональный флаг
    search_mode: str = Query("both", regex="^(both|titles|text)$")  # новый параметр
):
    logger.info(f"New search query: {q}")
    start = time.time()
    diversity=True
    try:
        # Определяем тип издания из запроса
        publication_types = detect_publication_type(q)
        clean_query = extract_clean_query(q)
        
        # Используем очищенный запрос для генерации вариантов
        query_list = coalesce(clean_query, transliterate(clean_query), local_changer(clean_query), fix_typo(clean_query))
        
        logger.info(f"🔍 Search request: index={index}, original='{q}', clean='{clean_query}', types={publication_types}, variants={query_list}, mode={search_mode}")

        # Выполняем запросы в зависимости от режима поиска
        flat_resp = None
        nested_resp = None
        
        if search_mode in ["both", "titles"]:
            flat_query = build_flat_query(query_list, start_year, end_year)
            flat_resp = client.search(index=index, body=flat_query)
        
        if search_mode in ["both", "text"]:
            nested_query = build_nested_query(query_list, start_year, end_year)
            nested_resp = client.search(index=index, body=nested_query)

        # Объединяем результаты
        flat_hits = flat_resp["hits"]["hits"] if flat_resp else []
        nested_hits = nested_resp["hits"]["hits"] if nested_resp else []
        combined_hits = merge_hits(flat_hits, nested_hits)

        # Постпроцесс с matched_pages
        results = postprocess_hits({"hits": {"hits": combined_hits}}, require_inner_hits=False)
        print([hit["path_index"] for hit in results])


        # Применим diversity, если включен
        if diversity:
            results = apply_diversity(results, max_per_type=6)

        for h in results:
            logger.info(f"📄 hit {h['path_index']} {h['book_id']} {h['id']} {h['book_code']}")

        total = {"value": len(results), "relation": "eq"}
        elapsed = round(time.time() - start, 3)
        logger.info(f"✅ Search complete: total={total}, time={elapsed}s")
        log_interaction(query=q, result_ids=[hit["id"] for hit in results])

        return {
            "original_query": q,
            "corrected_variants": query_list,
            "total": total,
            "results": results
        }

    except Exception as e:
        logger.exception(f"❌ Search failed for q='{q}': {e}")
        raise HTTPException(status_code=500, detail=f"OpenSearch error: {type(e).__name__} - {e}")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8076, reload=True)