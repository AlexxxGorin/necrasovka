from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from app.opensearch_client import client
from app.typo_client import fix_typo
from app.utils import transliterate, local_changer, coalesce
from app.postprocess_hits import postprocess_hits, apply_diversity
from app.logger_config import setup_logger
from app.config import settings
import time
import uvicorn
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


@app.get("/", tags=["Health"])
async def health_check():
    return {"status": "ok"}


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
        return (mb in ("nested", "both"), score)

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
    diversity: bool = Query(False)  # опциональный флаг
):
    logger.info(f"New search query: {q}")
    start = time.time()
    diversity=True
    try:
        query_list = coalesce(q, transliterate(q), local_changer(q), fix_typo(q))
        logger.info(f"🔍 Search request: index={index}, q='{q}', variants={query_list}")

        flat_query = build_flat_query(query_list, start_year, end_year)
        nested_query = build_nested_query(query_list, start_year, end_year)

        flat_resp = client.search(index=index, body=flat_query)
        nested_resp = client.search(index=index, body=nested_query)

        combined_hits = merge_hits(flat_resp["hits"]["hits"], nested_resp["hits"]["hits"])

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