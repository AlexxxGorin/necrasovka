import json
from collections import defaultdict

def extract_matched_pages(hit: dict) -> list[dict]:
    matched_pages = []

    inner_hits_dict = hit.get("inner_hits", {})

    for inner_key, inner in inner_hits_dict.items():
        pages_hits = inner.get("hits", {}).get("hits", [])
        for page_hit in pages_hits:
            source = page_hit.get("_source", {})
            highlight = (
                page_hit.get("highlight", {}).get("pages.book_page_text") or
                page_hit.get("highlight", {}).get("book_page_text") or
                []
            )
            snippet = highlight[0] if highlight else source.get("book_page_text", "")[:300]
            matched_pages.append({
                "page": source.get("book_page"),
                "image": source.get("book_page_image"),
                "snippet": snippet
            })

    return matched_pages


def apply_diversity(results: list[dict], max_per_type: int = 3) -> list[dict]:
    grouped = defaultdict(list)
    for hit in results:
        key = hit.get("path_index", "unknown")
        grouped[key].append(hit)

    diverse_results = []
    for hits in grouped.values():
        diverse_results.extend(hits[:max_per_type])

    return sorted(diverse_results, key=lambda x: x["score"], reverse=True)


def postprocess_hits(hits: dict, min_score=0.0, require_inner_hits=False) -> list[dict]:
    processed = []

    for hit in hits["hits"]["hits"]:
        if require_inner_hits and "inner_hits" not in hit:
            continue

        score = float(hit.get("_score", 0.0))
        if score < min_score:
            continue

        source = hit.get("_source", {})
        matched_by = source.get("matched_by", "flat")
        highlight = hit.get("highlight", {})
        matched_pages = extract_matched_pages(hit)

        # 🔍 Обложка: приоритетная страница → fallback на любую с картинкой
        cover_page = next(
            (p for p in source.get("pages", []) if p.get("cover_book_page") == 1),
            next((p for p in source.get("pages", []) if p.get("book_page_image")), None)
        )
        if cover_page:
            cover_page = {
                "page": cover_page.get("book_page"),
                "image": cover_page.get("book_page_image")
            }

        # Буст за плотные совпадения (если matched_pages много)
        if len(matched_pages) >= 2:
            score += 40.0

        processed.append({
            "title": source.get("title"),
            "book_name": source.get("book_name"),
            "description": source.get("description") or source.get("referat") or "Нет описания",
            "book_year": source.get("book_year"),
            "lang": source.get("lang"),
            "filter_name": source.get("filter_name"),
            "path_index": source.get("path_index"),
            "pdf_url": source.get("pdf_url"),
            "pdf_opac_001": source.get("pdf_opac_001"),
            "id": hit["_id"],
            "score": score,
            "matched_by": matched_by,
            "highlight_fields": list(highlight.keys()),
            "highlight": highlight,
            "matched_pages": matched_pages,
            "cover_page": cover_page,
            "book_code": source.get("book_code"),
            "book_id": source.get("book_id"),
            "url": f"https://api.electro.nekrasovka.ru/api/books/{source.get('book_id')}/pages/1/img/medium"
        })

    return sorted(processed, key=lambda x: x["score"], reverse=True)
