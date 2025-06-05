import pytest
import json
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch, MagicMock

from sqlalchemy import Column, Integer, String, DateTime, Numeric, Text
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from ehp.core.models.db.base import BaseModel
from ehp.db import Base


# Create a test model class
class TestModel(BaseModel):
    __tablename__ = "test_model"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    amount = Column(Numeric(10, 2), default=0)
    status = Column(String(1), default="1")
    active = Column(String(1), default="1")


@pytest.mark.unit
class TestBaseModel:

    @pytest.mark.asyncio
    async def test_to_dict(self):
        """Test that to_dict serializes model attributes correctly."""
        # Create model instance
        model = TestModel()
        model.id = 1
        model.name = "Test Model"
        model.description = "Test Description"
        model.created_at = datetime(2023, 1, 1, 12, 0, 0)
        model.amount = Decimal("123.45")
        model.status = "1"

        # Test serialization
        result = await model.to_dict()

        assert isinstance(result, dict)
        assert result["id"] == 1
        assert result["name"] == "Test Model"
        assert result["description"] == "Test Description"
        assert result["created_at"] == "2023-01-01T12:00:00"
        assert result["amount"] == "123.45"
        assert result["status"] == "1"

    @pytest.mark.asyncio
    async def test_serialize(self):
        """Test that serialize is an alias for to_dict."""
        model = TestModel()
        model.id = 1
        model.name = "Test Model"

        # Mock to_dict to verify it's called by serialize
        with patch.object(model, 'to_dict') as mock_to_dict:
            mock_to_dict.return_value = {"id": 1, "name": "Test Model"}
            result = await model.serialize()

        mock_to_dict.assert_called_once()
        assert result == {"id": 1, "name": "Test Model"}

    @pytest.mark.asyncio
    async def test_to_json(self):
        """Test that to_json converts model to JSON-compatible dict."""
        model = TestModel()
        model.id = 1
        model.name = "Test Model"
        model.created_at = datetime(2023, 1, 1, 12, 0, 0)

        result = await model.to_json()

        assert isinstance(result, dict)
        assert result["id"] == 1
        assert result["name"] == "Test Model"
        assert result["created_at"] == "2023-01-01T12:00:00"

        # Verify it can be serialized to JSON
        json_str = json.dumps(result)
        assert json_str == '{"id": 1, "name": "Test Model", "description": null, "created_at": "2023-01-01T12:00:00", "amount": null, "status": null, "active": null}'

    @pytest.mark.asyncio
    async def test_get_db_manager(self, test_db_manager):
        """Test that get_db_manager returns the DBManager from request."""
        # Mock get_current_request
        mock_request = MagicMock()
        mock_request.state.request_config = {"db_manager": test_db_manager}

        with patch("ehp.core.models.db.base.get_current_request", return_value=mock_request):
            result = await TestModel.get_db_manager()
            assert result == test_db_manager

    @pytest.mark.asyncio
    async def test_exists(self, test_db_session):
        """Test that exists checks if a model exists by ID."""
        # Create a mock DBManager
        db_manager = MagicMock()
        db_manager.transaction.return_value.__aenter__.return_value = test_db_session

        # Setup mock session.scalar to return True
        test_db_session.scalar = MagicMock()
        test_db_session.scalar.return_value = True

        # Mock get_db_manager to return our mock DB manager
        with patch.object(TestModel, 'get_db_manager', return_value=db_manager):
            # Test with valid ID
            result = await TestModel.exists(1)
            assert result is True

            # Test with invalid ID
            test_db_session.scalar.return_value = False
            result = await TestModel.exists(999)
            assert result is False

            # Test with None ID
            result = await TestModel.exists(None)
            assert result is False

    @pytest.mark.asyncio
    async def test_get_by_id(self, test_db_session):
        """Test that get_by_id retrieves a model by ID."""
        # Create a mock DBManager
        db_manager = MagicMock()
        db_manager.transaction.return_value.__aenter__.return_value = test_db_session

        # Create test model
        model = TestModel()
        model.id = 1
        model.name = "Test Model"

        # Setup mock session.get to return our model
        test_db_session.get = MagicMock()
        test_db_session.get.return_value = model

        # Mock get_db_manager to return our mock DB manager
        with patch.object(TestModel, 'get_db_manager', return_value=db_manager):
            # Test with valid ID
            result = await TestModel.get_by_id(1)
            assert result == model
            test_db_session.get.assert_called_with(TestModel, 1)

            # Test with invalid ID
            test_db_session.get.return_value = None
            result = await TestModel.get_by_id(999)
            assert result is None

            # Test with None ID
            result = await TestModel.get_by_id(None)
            assert result is None

    @pytest.mark.asyncio
    async def test_list(self, test_db_session):
        """Test that list retrieves all model instances."""
        # Create a mock DBManager
        db_manager = MagicMock()
        db_manager.transaction.return_value.__aenter__.return_value = test_db_session

        # Create test models
        model1 = TestModel(id=1, name="Model 1")
        model2 = TestModel(id=2, name="Model 2")

        # Setup mock session.scalars to return our models
        mock_result = MagicMock()
        mock_result.all.return_value = [model1, model2]

        test_db_session.scalars = MagicMock()
        test_db_session.scalars.return_value = mock_result

        # Mock get_db_manager to return our mock DB manager
        with patch.object(TestModel, 'get_db_manager', return_value=db_manager):
            result = await TestModel.list()
            assert len(result) == 2
            assert result[0] == model1
            assert result[1] == model2

    @pytest.mark.asyncio
    async def test_obj_delete(self, test_db_session):
        """Test that obj_delete deletes a model instance by ID."""
        # Create a mock DBManager
        db_manager = MagicMock()
        db_manager.transaction.return_value.__aenter__.return_value = test_db_session

        # Create test model
        model = TestModel()
        model.id = 1
        model.name = "Test Model"

        # Setup mock session.get and session.delete
        test_db_session.get = MagicMock(return_value=model)
        test_db_session.delete = MagicMock()
        test_db_session.flush = MagicMock()

        # Mock get_db_manager to return our mock DB manager
        with patch.object(TestModel, 'get_db_manager', return_value=db_manager):
            # Test with valid ID
            result = await TestModel.obj_delete(1)
            assert result is True
            test_db_session.get.assert_called_with(TestModel, 1)
            test_db_session.delete.assert_called_with(model)
            test_db_session.flush.assert_called_once()

            # Test with non-existent ID
            test_db_session.get.return_value = None
            result = await TestModel.obj_delete(999)
            assert result is False

            # Test with None ID
            result = await TestModel.obj_delete(None)
            assert result is False
