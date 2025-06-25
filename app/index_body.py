def get_better_index_body():
    return {
        "settings": {
            "analysis": {
                "filter": {
                    "russian_stemmer": {
                        "type": "stemmer",
                        "language": "russian"
                    },
                    "edge_ngram_filter": {
                        "type": "edge_ngram",
                        "min_gram": 2,
                        "max_gram": 20
                    }
                },
                "analyzer": {
                    "index_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": [
                            "lowercase",
                            "russian_stemmer",
                            "edge_ngram_filter"
                        ]
                    },
                    "search_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": [
                            "lowercase",
                            "russian_stemmer",
                            "icu_transform"
                        ]
                    }
                }
            },
            "number_of_shards": 3
        },
        "mappings": {
            "properties": {
                "title": {
                    "type": "text",
                    "analyzer": "index_analyzer",
                    "search_analyzer": "search_analyzer",
                    "fields": {
                        "keyword": { "type": "keyword", "ignore_above": 256 }
                    }
                },
                "book_name": {
                    "type": "text",
                    "analyzer": "index_analyzer",
                    "search_analyzer": "search_analyzer"
                },
                "referat": {
                    "type": "text",
                    "analyzer": "index_analyzer",
                    "search_analyzer": "search_analyzer"
                },
                "description": {
                    "type": "text",
                    "analyzer": "index_analyzer",
                    "search_analyzer": "search_analyzer"
                },
                "book_page_text": {
                    "type": "text",
                    "analyzer": "index_analyzer",
                    "search_analyzer": "search_analyzer"
                },
                "filter_name": {
                    "type": "keyword"
                },
                "book_year": {
                    "type": "date"
                },
                "lang": {
                    "type": "keyword"
                },
                "pages": {
                    "type": "nested",
                    "properties": {
                        "book_page": {"type": "long"},
                        "book_page_text": {
                            "type": "text",
                            "analyzer": "index_analyzer",
                            "search_analyzer": "search_analyzer"
                        },
                        "book_page_image": {"type": "keyword"},
                        "cover_book_page": {"type": "long"}
                    }
                }
            }
        }
    }
