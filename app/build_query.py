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
                    {
                        "multi_match": {
                            "query": joined_query,
                            "fields": [
                                "title^4",
                                "book_name^4",
                                "description^3"
                            ],
                            "type": "most_fields",
                            # "fuzziness": "AUTO",
                            "operator": "or"
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
                                "multi_match": {
                                    "query": joined_query,
                                    "fields": [
                                        "pages.book_page_text^8"
                                    ],
                                    "type": "most_fields",
                                    # "fuzziness": "AUTO",
                                    "operator": "and"
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
