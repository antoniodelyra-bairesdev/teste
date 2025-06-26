import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, MagicMock

from ehp.utils.validation import (
    InputSanitizer,
    RequestValidator,
    ValidatedModel,
    validate_and_sanitize,
)


@pytest.mark.unit
class TestInputSanitizer:
    """Test suite for InputSanitizer class."""

    def test_sanitize_string_basic(self):
        """Test basic string sanitization."""
        sanitizer = InputSanitizer()
        
        # Test normal string
        result = sanitizer.sanitize_string("Hello World")
        assert result == "Hello World"
        
        # Test string with extra whitespace
        result = sanitizer.sanitize_string("  Hello World  ")
        assert result == "Hello World"

    def test_sanitize_string_html_tags(self):
        """Test HTML tag removal."""
        sanitizer = InputSanitizer()
        
        # Test HTML tag removal
        result = sanitizer.sanitize_string("<p>Hello World</p>")
        assert result == "Hello World"
        
        # Test complex HTML
        result = sanitizer.sanitize_string('<div class="test"><p>Hello</p><br/><span>World</span></div>')
        assert result == "HelloWorld"

    def test_sanitize_string_html_escaping(self):
        """Test HTML character escaping."""
        sanitizer = InputSanitizer()
        
        # Test HTML character escaping (after HTML tag removal)
        result = sanitizer.sanitize_string("Hello & World")
        assert "&amp;" in result
        
        # Test that < > are treated as HTML tags and removed
        result = sanitizer.sanitize_string("Hello & World < Test >")
        assert "&amp;" in result
        # < Test > is removed as it's treated as an HTML tag
        assert "Test" not in result

    def test_sanitize_string_dangerous_patterns(self):
        """Test removal of dangerous patterns."""
        sanitizer = InputSanitizer()
        
        dangerous_inputs = [
            "javascript:alert('xss')",
            "onclick=alert('xss')",
            "<script>alert('xss')</script>",
            "vbscript:msgbox('xss')",
            "data:text/html,<script>alert('xss')</script>",
        ]
        
        for dangerous in dangerous_inputs:
            result = sanitizer.sanitize_string(dangerous)
            # Should not contain the dangerous pattern
            assert "javascript:" not in result.lower()
            assert "onclick" not in result.lower()
            assert "<script" not in result.lower()
            assert "vbscript:" not in result.lower()
            assert "data:text/html" not in result.lower()

    def test_sanitize_string_non_string_input(self):
        """Test that non-string inputs are returned as-is."""
        sanitizer = InputSanitizer()
        
        # Test non-string inputs
        assert sanitizer.sanitize_string(123) == 123
        assert sanitizer.sanitize_string(None) is None
        assert sanitizer.sanitize_string([1, 2, 3]) == [1, 2, 3]

    def test_check_sql_injection_should_block(self):
        """Test SQL injection patterns that should be blocked."""
        sanitizer = InputSanitizer()
        
        # These should be flagged as SQL injection
        malicious_inputs = [
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users",
            "UNION ALL SELECT password FROM accounts",
            "1 OR 1=1",
            "test AND 1=2",
            "something UNION SELECT username FROM users",
        ]
        
        for malicious in malicious_inputs:
            assert sanitizer.check_sql_injection(malicious), f"Should block: {malicious}"

    def test_check_sql_injection_should_allow(self):
        """Test legitimate content that should be allowed."""
        sanitizer = InputSanitizer()
        
        # These should NOT be flagged as SQL injection
        legitimate_inputs = [
            "I want to create a new account",
            "Please select the best option", 
            "This will update your profile",
            "Insert your name here",
            "Delete this message",
            "The select function was great",
            "database of information",
            "I need to alter my settings",
            "Drop me a line sometime",
            "Pope Leo XIV says tech companies developing artificial intelligence should abide by an 'ethical criterion'",
            "AI has been used to create harm in the world",
            "We need to select better policies",
            "The union of workers is important",
            "Please update your information",
            "I will insert the data manually",
            "Delete the unnecessary files",
            "The concert alter was beautiful",
            # Real content from your example
            """Pope Leo XIV says tech companies developing artificial intelligence should abide by an 'ethical criterion' that respects human dignity.
            
            AI must take 'into account the well-being of the human person not only materially, but also intellectually and spiritually,' the pope said in a message sent Friday to a gathering on AI attended by Vatican officials and Silicon Valley executives.
            
            'No generation has ever had such quick access to the amount of information now available through AI,' he said. But 'access to data — however extensive — must not be confused with intelligence.'""",
        ]
        
        for legitimate in legitimate_inputs:
            assert not sanitizer.check_sql_injection(legitimate), f"Should allow: {legitimate[:50]}..."

    def test_check_sql_injection_edge_cases(self):
        """Test edge cases for SQL injection detection."""
        sanitizer = InputSanitizer()
        
        # Test non-string inputs
        assert not sanitizer.check_sql_injection(None)
        assert not sanitizer.check_sql_injection(123)
        assert not sanitizer.check_sql_injection([])
        assert not sanitizer.check_sql_injection({})
        
        # Test empty string
        assert not sanitizer.check_sql_injection("")
        
        # Test whitespace only
        assert not sanitizer.check_sql_injection("   ")

    def test_check_sql_injection_case_insensitive(self):
        """Test that SQL injection detection is case insensitive."""
        sanitizer = InputSanitizer()
        
        # Test different cases of the same attack
        attack_variations = [
            "union select * from users",
            "UNION SELECT * FROM USERS", 
            "Union Select * From Users",
            "uNiOn sElEcT * fRoM uSeRs",
        ]
        
        for attack in attack_variations:
            assert sanitizer.check_sql_injection(attack), f"Should block: {attack}"


@pytest.mark.unit
class TestRequestValidator:
    """Test suite for RequestValidator class."""

    def test_validate_request_data_basic(self):
        """Test basic request data validation."""
        validator = RequestValidator()
        
        data = {
            "title": "Test Title",
            "content": "This is test content",
            "number": 123
        }
        
        result = validator.validate_request_data(data)
        
        assert result["is_valid"] is True
        assert result["errors"] == []
        assert "title" in result["sanitized_data"]
        assert "content" in result["sanitized_data"]
        assert "number" in result["sanitized_data"]

    def test_validate_request_data_with_sql_injection(self):
        """Test validation with SQL injection attempts."""
        validator = RequestValidator()
        
        data = {
            "title": "Test Title",
            "content": "'; DROP TABLE users; --",
            "safe_field": "This is safe"
        }
        
        result = validator.validate_request_data(data)
        
        assert result["is_valid"] is False
        assert len(result["errors"]) > 0
        assert "Security violation in field: content" in result["errors"]

    def test_validate_request_data_legitimate_content(self):
        """Test validation with legitimate content containing SQL keywords."""
        validator = RequestValidator()
        
        data = {
            "title": "Creating a Better World",
            "content": "We need to select the best approach to create meaningful change. This will update society and help us insert positive values into our communities.",
            "url": "https://example.com"
        }
        
        result = validator.validate_request_data(data)
        
        assert result["is_valid"] is True
        assert result["errors"] == []
        assert len(result["sanitized_data"]) == 3

    def test_validate_request_data_html_sanitization(self):
        """Test that HTML content is properly sanitized."""
        validator = RequestValidator()
        
        data = {
            "content": "<p>Hello <strong>World</strong></p>",
            "title": "Test & Title"
        }
        
        result = validator.validate_request_data(data)
        
        assert result["is_valid"] is True
        # HTML tags should be removed
        assert "<p>" not in result["sanitized_data"]["content"]
        assert "<strong>" not in result["sanitized_data"]["content"]
        # HTML entities should be escaped
        assert "&amp;" in result["sanitized_data"]["title"]

    def test_validate_request_data_mixed_types(self):
        """Test validation with mixed data types."""
        validator = RequestValidator()
        
        data = {
            "string_field": "Test string",
            "int_field": 42,
            "float_field": 3.14,
            "bool_field": True,
            "list_field": [1, 2, 3],
            "dict_field": {"key": "value"}
        }
        
        result = validator.validate_request_data(data)
        
        assert result["is_valid"] is True
        assert result["sanitized_data"]["string_field"] == "Test string"
        assert result["sanitized_data"]["int_field"] == 42
        assert result["sanitized_data"]["float_field"] == 3.14
        assert result["sanitized_data"]["bool_field"] is True
        assert result["sanitized_data"]["list_field"] == [1, 2, 3]
        assert result["sanitized_data"]["dict_field"] == {"key": "value"}


@pytest.mark.unit
class TestValidatedModel:
    """Test suite for ValidatedModel class."""

    def test_validated_model_success(self):
        """Test ValidatedModel with clean data."""
        
        class TestModel(ValidatedModel):
            title: str
            content: str
        
        data = {
            "title": "Test Title",
            "content": "This is clean content"
        }
        
        # Should not raise exception
        model = TestModel(**data)
        assert model.title == "Test Title"
        assert model.content == "This is clean content"

    def test_validated_model_with_sql_injection(self):
        """Test ValidatedModel rejects SQL injection."""
        
        class TestModel(ValidatedModel):
            title: str
            content: str
        
        data = {
            "title": "Test Title",
            "content": "'; DROP TABLE users; --"
        }
        
        # Should raise ValueError
        with pytest.raises(ValueError) as excinfo:
            TestModel(**data)
        
        assert "Dangerous pattern detected in content" in str(excinfo.value)

    def test_validated_model_with_html_content(self):
        """Test ValidatedModel sanitizes HTML content."""
        
        class TestModel(ValidatedModel):
            title: str
            content: str
        
        data = {
            "title": "<script>alert('xss')</script>Safe Title",
            "content": "<p>Hello <strong>World</strong></p>"
        }
        
        # Should sanitize but not reject
        model = TestModel(**data)
        assert "<script>" not in model.title
        assert "<p>" not in model.content
        assert "Hello World" in model.content


@pytest.mark.unit 
class TestValidateAndSanitizeDecorator:
    """Test suite for validate_and_sanitize dependency."""

    @pytest.mark.asyncio
    async def test_validate_and_sanitize_success(self):
        """Test successful validation and sanitization."""
        
        # Mock request
        mock_request = MagicMock()
        mock_request.query_params = {}
        mock_request.method = "POST"
        mock_request.json = AsyncMock(return_value={
            "title": "Test Title",
            "content": "Clean content"
        })
        mock_request.state = MagicMock()
        
        validator_func = validate_and_sanitize()
        result = await validator_func(mock_request)
        
        assert "title" in result
        assert "content" in result
        assert result["title"] == "Test Title"

    @pytest.mark.asyncio
    async def test_validate_and_sanitize_sql_injection(self):
        """Test validation rejection of SQL injection."""
        
        # Mock request
        mock_request = MagicMock()
        mock_request.query_params = {}
        mock_request.method = "POST"
        mock_request.json = AsyncMock(return_value={
            "title": "Test Title",
            "content": "'; DROP TABLE users; --"
        })
        
        validator_func = validate_and_sanitize()
        
        # Should raise HTTPException
        with pytest.raises(HTTPException) as excinfo:
            await validator_func(mock_request)
        
        assert excinfo.value.status_code == 400
        assert "Request validation failed" in excinfo.value.detail["message"]

    @pytest.mark.asyncio
    async def test_validate_and_sanitize_legitimate_keywords(self):
        """Test validation allows legitimate SQL keyword usage."""
        
        # Mock request
        mock_request = MagicMock()
        mock_request.query_params = {}
        mock_request.method = "POST"
        mock_request.json = AsyncMock(return_value={
            "title": "Creating Better Solutions",
            "content": "We need to select the right approach and create positive change. This will update our community and help insert good values."
        })
        mock_request.state = MagicMock()
        
        validator_func = validate_and_sanitize()
        result = await validator_func(mock_request)
        
        # Should succeed
        assert "title" in result
        assert "content" in result
        assert "Creating Better Solutions" in result["title"]

    @pytest.mark.asyncio
    async def test_validate_and_sanitize_query_params(self):
        """Test validation of query parameters."""
        
        # Mock request
        mock_request = MagicMock()
        mock_request.query_params = {"search": "test query", "page": "1"}
        mock_request.method = "GET"
        mock_request.state = MagicMock()
        
        validator_func = validate_and_sanitize()
        result = await validator_func(mock_request)
        
        assert "search" in result
        assert "page" in result
        assert result["search"] == "test query"
        assert result["page"] == "1"

    @pytest.mark.asyncio
    async def test_validate_and_sanitize_invalid_json(self):
        """Test validation handles invalid JSON gracefully."""
        
        # Mock request with invalid JSON
        mock_request = MagicMock()
        mock_request.query_params = {}
        mock_request.method = "POST" 
        mock_request.json = AsyncMock(side_effect=Exception("Invalid JSON"))
        mock_request.state = MagicMock()
        
        validator_func = validate_and_sanitize()
        result = await validator_func(mock_request)
        
        # Should return empty dict when JSON parsing fails
        assert result == {}
