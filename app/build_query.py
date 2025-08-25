def build_flat_query(query_list: list[str], start_year: str = None, end_year: str = None) -> dict:
    must_filters = []
    if start_year and end_year:
        must_filters.append({
            "range": {
                "book_year": {
                    "gte": f"{start_year}-01-01",
                    "lte": f"{end_year}-12-31"
                }
            }
        })

    joined_query = " ".join(query_list)

    return {
        "size": 50,
        # Вот тут важный фикс:
        "_source": [
            "book_id",
            "title",
            "book_name",
            "description",
            "referat",
            "book_year",
            "lang",
            "filter_name",
            "path_index",
            "pdf_url",
            "pdf_opac_001",
            "pages",
            "book_code"
        ],

        "query": {
            "bool": {
                "must": must_filters,
                        "should": [
            # Точное фразовое совпадение в заголовке - максимальный буст только если ВСЕ слова есть
            {
                "multi_match": {
                    "query": joined_query,
                    "fields": [
                        "title^25",
                        "book_name^25"
                    ],
                    "type": "phrase",
                    "boost": 10.0
                }
            },
            # Все слова должны присутствовать в заголовке (AND)
            {
                "multi_match": {
                    "query": joined_query,
                    "fields": [
                        "title^15",
                        "book_name^15"
                    ],
                    "type": "best_fields",
                    "operator": "and",
                    "boost": 5.0
                }
            },
            # Все слова должны присутствовать где-то в документе
            {
                "multi_match": {
                    "query": joined_query,
                    "fields": [
                        "title^8",
                        "book_name^8",
                        "description^4"
                    ],
                    "type": "cross_fields",
                    "operator": "and",
                    "boost": 3.0
                }
            },
            # Частичное совпадение в заголовках (с пониженным бустом)
            {
                "multi_match": {
                    "query": joined_query,
                    "fields": [
                        "title^4",
                        "book_name^4",
                        "description^2"
                    ],
                    "type": "best_fields",
                    "operator": "or",
                    "boost": 1.0
                }
            }
        ],
                "minimum_should_match": 1
            }
        },
        "highlight": {
            "fields": {
                "title": {},
                "book_name": {},
                "book_page_text": {}
            },
            "number_of_fragments": 1,
            "fragment_size": 150
        }
    }


def build_nested_query(query_list: list[str], start_year: str = None, end_year: str = None) -> dict:
    must_filters = []
    if start_year and end_year:
        must_filters.append({
            "range": {
                "book_year": {
                    "gte": f"{start_year}-01-01",
                    "lte": f"{end_year}-12-31"
                }
            }
        })

    joined_query = " ".join(query_list)

    return {
        "size": 50,
        # Вот тут важный фикс:
        "_source": [
            "book_id",
            "title",
            "book_name",
            "description",
            "referat",
            "book_year",
            "lang",
            "filter_name",
            "path_index",
            "pdf_url",
            "pdf_opac_001",
            "pages",
            "book_code"
        ],

        "query": {
            "bool": {
                "must": must_filters,
                "should": [
                    {
                        "nested": {
                            "path": "pages",
                            "query": {
                                "bool": {
                                    "should": [
                                        # Точная фраза в тексте - максимальный буст
                                        {
                                            "multi_match": {
                                                "query": joined_query,
                                                "fields": ["pages.book_page_text^15"],
                                                "type": "phrase",
                                                "boost": 3.0
                                            }
                                        },
                                        # Все слова должны быть в тексте страницы
                                        {
                                            "multi_match": {
                                                "query": joined_query,
                                                "fields": ["pages.book_page_text^10"],
                                                "type": "best_fields",
                                                "operator": "and",
                                                "boost": 2.0
                                            }
                                        },
                                        # Частичное совпадение в тексте
                                        {
                                            "multi_match": {
                                                "query": joined_query,
                                                "fields": ["pages.book_page_text^5"],
                                                "type": "best_fields",
                                                "operator": "or"
                                            }
                                        }
                                    ],
                                    "minimum_should_match": 1
                                }
                            },
                            "inner_hits": {
                                "name": "matched_pages",
                                "size": 5,
                                "highlight": {
                                    "fields": {
                                        "pages.book_page_text": {}
                                    },
                                    "number_of_fragments": 1,
                                    "fragment_size": 150
                                }
                            }
                        }
                    }
                ],
                "minimum_should_match": 1
            }
        }
    }
