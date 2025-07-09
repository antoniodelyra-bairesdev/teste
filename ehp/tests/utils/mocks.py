from typing import Any, Dict
from unittest.mock import MagicMock, patch

from fakeredis import FakeRedis

from ehp.base.session import SessionData
from ehp.core.models.db.authentication import Authentication


class MockElasticsearch:
    """Mock Elasticsearch client for testing."""

    def __init__(self):
        self.indices = MagicMock()
        self.indices.exists.return_value = True
        self.indices.create.return_value = {"acknowledged": True}

        self.data = {}
        self.index_data = {}

    def index(self, index: str, id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Mock indexing a document."""
        if index not in self.index_data:
            self.index_data[index] = {}

        self.index_data[index][id] = body
        return {"result": "created"}

    def update(self, index: str, id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Mock updating a document."""
        if index not in self.index_data or id not in self.index_data[index]:
            return {"result": "not_found"}

        if "doc" in body:
            self.index_data[index][id].update(body["doc"])

        return {"result": "updated"}

    def delete_by_query(self, index: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Mock deleting documents by query."""
        if index not in self.index_data:
            return {"deleted": 0}

        if "query" in body and "match_all" in body["query"]:
            # Delete all documents
            count = len(self.index_data[index])
            self.index_data[index] = {}
            return {"deleted": count}

        if "query" in body and "term" in body["query"]:
            # Delete by term
            field = list(body["query"]["term"].keys())[0]
            value = body["query"]["term"][field]

            deleted = 0
            to_delete = []

            for doc_id, doc in self.index_data[index].items():
                if doc.get(field) == value:
                    to_delete.append(doc_id)
                    deleted += 1

            for doc_id in to_delete:
                del self.index_data[index][doc_id]

            return {"deleted": deleted}

        return {"deleted": 0}

    def search(self, index: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Mock searching for documents."""
        if index not in self.index_data:
            return {"hits": {"hits": []}}

        # Simplified search implementation
        results = []

        for doc_id, doc in self.index_data[index].items():
            if "query" in body and "multi_match" in body["query"]:
                query = body["query"]["multi_match"]["query"]
                fields = body["query"]["multi_match"]["fields"]

                for field in fields:
                    if field in doc and str(query).lower() in str(doc[field]).lower():
                        results.append({"_id": doc_id, "_source": doc})
                        break
            else:
                # Return all documents if no specific query
                results.append({"_id": doc_id, "_source": doc})

        # Handle pagination
        from_idx = body.get("from", 0)
        size = body.get("size", 10)
        paginated = results[from_idx : from_idx + size]

        return {"hits": {"hits": paginated}}


# Patch functions
def patch_redis():
    """Patch Redis client with mock implementation."""
    mock_redis = FakeRedis(decode_responses=True)

    # Patch the Redis client initialization
    redis_patch = patch("ehp.base.redis_storage.redis_client", mock_redis)

    # Patch the get_redis_client function
    get_redis_patch = patch(
        "ehp.base.redis_storage.get_redis_client", return_value=mock_redis
    )

    return redis_patch, get_redis_patch, mock_redis


def patch_elasticsearch():
    """Patch Elasticsearch client with mock implementation."""
    mock_es = MockElasticsearch()

    # Patch the Elasticsearch client initialization
    es_patch = patch("ehp.utils.search.client", mock_es)

    return es_patch, mock_es


def patch_email():
    """Patch email sending functions."""
    # Patch SMTP
    smtp_patch = patch("smtplib.SMTP")

    # Patch send_notification
    send_notification_patch = patch(
        "ehp.utils.email.send_notification", return_value=True
    )

    return smtp_patch, send_notification_patch


def setup_mock_authentication(db_session, user_data=None):
    """Setup mock authentication data in the database."""
    from ehp.utils.authentication import hash_password

    if user_data is None:
        user_data = {
            "id": 1,
            "user_name": "testuser",
            "user_email": "test@example.com",
            "user_pwd": hash_password("Te$tPassword123"),
            "is_active": "1",
            "is_confirmed": "1",
            "profile_id": 1,
        }

    # Create a mock Authentication object
    mock_auth = MagicMock(spec=Authentication)
    mock_auth.retry_count = 0  # Default retry count
    for key, value in user_data.items():
        setattr(mock_auth, key, value)

    # Setup the to_dict method
    async def mock_to_dict():
        return user_data

    mock_auth.to_dict = mock_to_dict

    # Patch Authentication.get_by_email and Authentication.get_by_user_name
    auth_email_patch = patch(
        "ehp.core.repositories.authentication.AuthenticationRepository.get_by_email",
        return_value=mock_auth,
    )

    auth_username_patch = patch(
        "ehp.core.repositories.authentication.AuthenticationRepository.get_by_username",
        return_value=mock_auth,
    )

    return auth_email_patch, auth_username_patch, mock_auth


def mock_session_data(session_id="test-session-id", user_data=None) -> SessionData:
    """Create mock session data."""
    return SessionData(
        session_id="test-session-id", session_token="test-token", metadata={}
    )
