from datetime import datetime
from typing import Any, cast, Dict, List

from elasticsearch import Elasticsearch

from ehp.config import settings


client = Elasticsearch(settings.ELASTICSEARCH_URL)


def _activity_payload(data: Dict[str, Any], index_name: str) -> Dict[str, Any]:
    return {
        "id": data.get("id"),
        "activity_name": data.get("user_name"),
        "house_name": data.get("user_first_name"),
        "character_name": data.get("user_last_name"),
        "category_id": data.get("user_email"),
        "category_name": data.get("user_email"),
        "index_type": data.get("index_type"),
        "url": f"/activity?activity_id={data.get('id')}",
        "_index_id": data.get("id"),
        "_index_name": index_name,
        "_index_created_at": datetime.now(),
    }


def index_content(data: Dict[str, Any]) -> Dict[str, Any]:
    if not data:
        return {}

    index_name = f"{data.get('index_type')}_index"
    if client and not client.indices.exists(index=index_name):
        client.indices.create(index=index_name)

    payload = _activity_payload(data, index_name)
    response = client.index(index=index_name, id=data.get("id"), body=payload)
    assert response is not None
    return cast(Dict[str, Any], response["result"])


def index_update_content(data: Dict[str, Any]) -> Dict[str, Any]:
    if not data:
        return {}

    index_name = f"{data.get('index_type')}_index"
    if client and not client.indices.exists(index=index_name):
        return {"result": index_content(data) is not None}

    payload = {"doc": _activity_payload(data, index_name)}
    response = client.update(index=index_name, id=data.get("id"), body=payload)
    assert response is not None
    assert response["result"] == "updated"
    return cast(Dict[str, Any], response["result"])


def index_delete_content(data: Dict[str, Any]) -> bool:
    if not data:
        return False

    index_name = f"{data.get('index_type')}_index"
    if client and not client.indices.exists(index=index_name):
        return False

    body = {"query": {"term": {"id": data.get("id")}}}

    # Delete documents by query
    response = client.delete_by_query(index=index_name, body=body)
    return cast(bool, response and response["deleted"] > 0)


def search_activity(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not data:
        return []

    index_name = f"{data.get('index_type')}_index"
    if client and not client.indices.exists(index=index_name):
        return []

    page_num = data.get("page_num", 1)
    page_size = data.get("page_size", 20)
    query_from = (page_num - 1) * page_size
    res = client.search(
        index=index_name,
        body={
            "from": query_from,
            "size": page_size,
            "query": {
                "multi_match": {
                    "fields": [
                        "activity_name",
                        "house_name",
                        "character_name",
                        "category_name",
                    ],
                    "query": data.get("text_to_search"),
                    "type": "phrase_prefix",
                }
            },
        },
    )
    return [
        {
            "id": hit["_source"]["id"],
            "activity_name": hit["_source"]["activity_name"],
            "house_name": hit["_source"]["house_name"],
            "character_name": hit["_source"]["character_name"],
            "category_name": hit["_source"]["category_name"],
            "index_type": hit["_source"]["index_type"],
            "url": hit["_source"]["url"],
        }
        for hit in res["hits"]["hits"]
    ]


def clean_index(index_type: str) -> bool:
    if not index_type:
        return False

    index_name = f"{index_type}_index"
    if client and not client.indices.exists(index=index_name):
        return False

    query = {"query": {"match_all": {}}}
    response = client.delete_by_query(index=index_name, body=query)
    return cast(bool, response and response["deleted"] > 0)
