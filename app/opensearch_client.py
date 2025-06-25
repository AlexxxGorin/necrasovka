# app/opensearch_client.py
from opensearchpy import OpenSearch, RequestsHttpConnection
from app.config import settings

# OpenSearch
# OPENSEARCH_URL=rc1b-5el6fevs7qim0oss.mdb.yandexcloud.net
OPENSEARCH_URL="rc1b-5el6fevs7qim0oss.mdb.yandexcloud.net"
OPENSEARCH_USERNAME="admin"
# OPENSEARCH_PASSWORD=lucius_fox
OPENSEARCH_PASSWORD="lucius_fox"

host = settings.opensearch_url.replace("https://", "").replace("https://", "")
client = OpenSearch(
    hosts=[{"host": OPENSEARCH_URL, "port": 9200, 'scheme': 'https'}],
    http_auth=(OPENSEARCH_USERNAME, OPENSEARCH_PASSWORD),
    use_ssl=True,
    verify_certs=False,
    connection_class=RequestsHttpConnection
)
