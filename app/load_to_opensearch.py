import pandas as pd
import json
import os
from opensearchpy import OpenSearch, helpers
from dotenv import load_dotenv
from app.index_body import get_index_body
import logging

# --- ЛОГГЕР ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler("load_to_opensearch.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# --- CONFIG ---
load_dotenv()
INDEX_NAME = "electrodb.books"

client = OpenSearch(
    hosts=[os.getenv("OPENSEARCH_URL")],
    http_auth=(os.getenv("OPENSEARCH_USERNAME"), os.getenv("OPENSEARCH_PASSWORD")),
    use_ssl=True,
    verify_certs=False
)

# --- INDEX CREATION ---
if not client.indices.exists(INDEX_NAME):
    log.info(f"Создание индекса {INDEX_NAME}...")
    client.indices.create(index=INDEX_NAME, body=get_index_body())
else:
    log.info(f"Индекс {INDEX_NAME} уже существует.")

# --- LOAD DATA ---
try:
    books = pd.read_csv("books.csv")
    pages = pd.read_csv("data.csv")
    log.info(f"Прочитано книг: {len(books)}, страниц: {len(pages)}")

    # джойн
    merged = pd.merge(pages, books, on="book_id", suffixes=("_page", "_meta"))
    log.info(f"Совмещённых записей: {len(merged)}")

    # пробная выборка
    sample = merged.head(100)

    def to_doc(row):
        return {
            "_index": INDEX_NAME,
            "_id": f"{row['book_id']}_{row['book_page']}",
            "_source": {
                "title": row["book_name"],
                "description": row.get("book_page_text_updated") or row.get("book_page_text"),
                "filter_name": row.get("book_author"),
                "book_code": row.get("book_code"),
                "book_page_image": row.get("book_page_image"),
                "book_path": row.get("book_path"),
            }
        }

    actions = [to_doc(row) for _, row in sample.iterrows()]
    helpers.bulk(client, actions)
    log.info(f"Загружено {len(actions)} документов в индекс {INDEX_NAME}")

except Exception as e:
    log.exception("Ошибка при загрузке данных в OpenSearch")
