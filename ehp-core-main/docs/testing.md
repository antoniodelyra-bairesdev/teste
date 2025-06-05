# Dev's Guide to Adding Tests

This guide provides step-by-step instructions for adding new tests to the EHP Core project using the established testing infrastructure.

## Prerequisites

Before adding tests, identify which type of test you need to create:
   - **Unit Test**: individual functions or classes
   - **Integration Test**: API endpoints and component interactions
   - **End-to-End Test**: complete user flows

## Step 1: Create the Test File

Create new test file in the appropriate directory:

- Unit tests: `tests/unit/[module]/test_[component].py`
- Integration tests: `tests/integration/[area]/test_[endpoint].py`
- End-to-End tests: `tests/end_to_end/test_[flow].py`

Follow the naming convention `test_*.py` for test files and `test_*` for test functions.

## Step 2: Import Required Dependencies

Import the necessary dependencies for your test. Common imports include:

```python
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import FastAPI

from tests.utils.test_client import EHPTestClient
from tests.utils.mocks import patch_redis, patch_elasticsearch, patch_email

# Import the components you're testing
from ehp.module.component import function_to_test
```

## Step 3: Add Test Markers

Add pytest markers to categorize your test:

```python
@pytest.mark.unit  # For unit tests
@pytest.mark.integration  # For integration tests
@pytest.mark.end_to_end  # For end-to-end tests
def test_function_name():
    ...
```

For async tests, add the asyncio marker:

```python
@pytest.mark.asyncio
async def test_async_function():
    ...
```

## Step 4: Implement the Test

### For Unit Tests

```python
@pytest.mark.unit
def test_function_name():
    # Arrange - set up test data and mocks
    input_data = "test input"
    expected_output = "test output"
    
    # Act - call the function being tested
    result = function_to_test(input_data)
    
    # Assert - verify the function behaved as expected
    assert result == expected_output
```

For async unit tests:

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_function():
    # Arrange
    input_data = "test input"
    expected_output = "test output"
    
    # Act
    result = await async_function_to_test(input_data)
    
    # Assert
    assert result == expected_output
```

### For API/Integration Tests

```python
@pytest.mark.integration
def test_api_endpoint(app: FastAPI):
    # Arrange - set up the test client and any mocks
    client = EHPTestClient(app)
    
    # Mock any dependencies the endpoint uses
    with patch("ehp.module.component.dependency", return_value="mocked_value"):
        # Act - make the request
        response = client.get("/api/endpoint", params={"param": "value"})
        
        # Assert - verify the response
        assert response.status_code == 200
        assert "result" in response.json()
        assert response.json()["result"]["key"] == "expected_value"
```

### For End-to-End Tests

```python
@pytest.mark.end_to_end
def test_user_flow(app: FastAPI):
    # Arrange - set up the test client and any mocks
    client = EHPTestClient(app)
    
    # Setup required mocks
    auth_email_patch, auth_username_patch, mock_auth = client.setup_authentication()
    auth_email_patch.start()
    auth_username_patch.start()
    
    try:
        # Act - perform the steps in the flow
        
        # Step 1
        response1 = client.post("/step1", json={"param": "value"})
        assert response1.status_code == 200
        
        # Step 2
        token = response1.json()["result"]["token"]
        response2 = client.get("/step2", include_auth=True)
        assert response2.status_code == 200
        
        # Step 3
        response3 = client.put("/step3", json={"updated": "value"}, include_auth=True)
        assert response3.status_code == 200
        
    finally:
        # Clean up
        auth_email_patch.stop()
        auth_username_patch.stop()
```

## Step 5: Mock External Dependencies

Use the provided mock utilities to isolate your tests:

```python
from tests.utils.mocks import patch_redis, patch_elasticsearch, patch_email

def test_with_mocks():
    redis_patch, get_redis_patch, mock_redis = patch_redis()
    es_patch, mock_es = patch_elasticsearch()
    
    redis_patch.start()
    get_redis_patch.start()
    es_patch.start()
    
    try:
        # Your test code here
        mock_redis.set("key", "value")
        assert mock_redis.get("key") == "value"
    finally:
        redis_patch.stop()
        get_redis_patch.stop()
        es_patch.stop()
```

Or use the test client, which handles mocking for you:

```python
def test_with_client(app):
    client = EHPTestClient(app)
    
    # Redis, Elasticsearch, and email are already mocked
    response = client.get("/api/endpoint")
    ...
```

## Step 6: Test Database Operations

For tests that involved database operations:

```python
@pytest.mark.asyncio
async def test_database_operation(test_db_session, test_db_manager):
    # Create test data
    model = TestModel(name="Test")
    test_db_session.add(model)
    await test_db_session.flush()
    
    # Test the database operation
    result = await TestModel.get_by_id(model.id)
    assert result is not None
    assert result.name == "Test"
```

## Step 7: Run and Debug Your Tests

Run your specific test:

```bash
# Run a specific test file
pytest tests/path/to/test_file.py

# Run a specific test function
pytest tests/path/to/test_file.py::test_function_name
```

## Step 8: Check Test Coverage

Check that your tests cover all the code paths:

```bash
# Run tests with coverage report
pytest --cov=ehp.module.component tests/path/to/test_file.py
```

## Useful links

1. Pytest docs: https://docs.pytest.org/
2. FastAPI testing docs: https://fastapi.tiangolo.com/tutorial/testing/
