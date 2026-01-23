"""
Unit tests for A/B Testing API endpoints
Feature: 016-a-b-testing-framework-for-content
"""

import pytest
import uuid
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from src.models.ab_testing import ABTestStatus
from src.schemas.ab_testing import (
    ABTestCreate,
    ABTestUpdate,
    ABTestVariantCreate,
    ABTestMetricCreate,
)


@pytest.fixture(autouse=True)
def cleanup_data(db_session):
    """Clean up data in tables before/after each test."""
    yield


@pytest.fixture
def sample_channel_id(db_session):
    """Create and return a sample channel for testing."""
    from src.models.telegram import Channel
    from src.models.user import User
    import uuid as uuid_lib

    # Create owner
    owner = User(email='channel_owner@example.com', hashed_password='x', role='admin', status='approved')
    db_session.add(owner)
    db_session.commit()
    db_session.refresh(owner)

    # Create channel
    channel_id = uuid_lib.uuid4()
    channel = Channel(
        id=channel_id,
        account_id=None,  # Not needed for tests
        chat_id=12345,
        name='Test Channel for A/B Testing',
    )
    db_session.add(channel)
    db_session.commit()
    db_session.refresh(channel)

    return channel_id


@pytest.fixture
def sample_ab_test_data(sample_channel_id):
    """Sample A/B test creation data."""
    return {
        "channel_id": str(sample_channel_id),
        "name": "Video Engagement Test",
        "description": "Testing two video variants for engagement",
        "hypothesis": "Video B will have 20% higher engagement",
        "planned_duration_hours": 48,
        "traffic_config": {
            "algorithm": "weighted",
            "auto_stop": True,
            "min_sample_size": 1000
        },
        "variants": [
            {
                "name": "Video A - Control",
                "description": "Original video",
                "traffic_allocation": 50,
                "configuration": {
                    "type": "playlist",
                    "playlist_id": str(uuid.uuid4())
                },
                "position": 0,
            },
            {
                "name": "Video B - Test",
                "description": "Optimized video",
                "traffic_allocation": 50,
                "configuration": {
                    "type": "playlist",
                    "playlist_id": str(uuid.uuid4())
                },
                "position": 1,
            },
        ],
    }


class TestCreateABTest:
    """Tests for POST /ab-tests endpoint."""

    def test_create_ab_test_success(self, client, admin_auth_headers, sample_ab_test_data):
        """Test successful creation of A/B test."""
        response = client.post(
            "/api/ab-tests",
            json=sample_ab_test_data,
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == sample_ab_test_data["name"]
        assert data["status"] == ABTestStatus.DRAFT.value
        assert data["channel_id"] == sample_ab_test_data["channel_id"]
        assert len(data["variants"]) == 2

    def test_create_ab_test_unauthorized(self, client, sample_ab_test_data):
        """Test that unauthorized users cannot create A/B tests."""
        response = client.post(
            "/api/ab-tests",
            json=sample_ab_test_data,
        )

        assert response.status_code == 401

    def test_create_ab_test_forbidden_user_role(self, client, user_auth_headers, sample_ab_test_data):
        """Test that regular users cannot create A/B tests."""
        response = client.post(
            "/api/ab-tests",
            json=sample_ab_test_data,
            headers=user_auth_headers,
        )

        assert response.status_code == 403

    def test_create_ab_test_invalid_traffic_allocation(self, client, admin_auth_headers, sample_ab_test_data, sample_channel_id):
        """Test that invalid traffic allocation is rejected."""
        invalid_data = sample_ab_test_data.copy()
        invalid_data["variants"] = [
            {
                "name": "Variant A",
                "traffic_allocation": 150,  # Invalid
                "configuration": {},
                "position": 0,
            },
        ]

        response = client.post(
            "/api/ab-tests",
            json=invalid_data,
            headers=admin_auth_headers,
        )

        assert response.status_code == 400

    def test_create_ab_test_missing_variants(self, client, admin_auth_headers, sample_channel_id):
        """Test that missing variants are rejected."""
        invalid_data = {
            "channel_id": str(sample_channel_id),
            "name": "Test",
            "variants": [],  # Invalid - need at least 2
        }

        response = client.post(
            "/api/ab-tests",
            json=invalid_data,
            headers=admin_auth_headers,
        )

        assert response.status_code == 422  # Validation error

    def test_create_ab_test_missing_name(self, client, admin_auth_headers, sample_channel_id):
        """Test that missing name is rejected."""
        invalid_data = {
            "channel_id": str(sample_channel_id),
            "variants": [
                {
                    "name": "Variant A",
                    "traffic_allocation": 50,
                    "configuration": {},
                    "position": 0,
                },
                {
                    "name": "Variant B",
                    "traffic_allocation": 50,
                    "configuration": {},
                    "position": 1,
                },
            ],
        }

        response = client.post(
            "/api/ab-tests",
            json=invalid_data,
            headers=admin_auth_headers,
        )

        assert response.status_code == 422  # Validation error


class TestListABTests:
    """Tests for GET /ab-tests endpoint."""

    def test_list_ab_tests_success(self, client, admin_auth_headers):
        """Test successful listing of A/B tests."""
        response = client.get(
            "/api/ab-tests",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "tests" in data
        assert "total" in data
        assert isinstance(data["tests"], list)

    def test_list_ab_tests_unauthorized(self, client):
        """Test that unauthorized users cannot list A/B tests."""
        response = client.get("/api/ab-tests")

        assert response.status_code == 401

    def test_list_ab_tests_with_channel_filter(self, client, admin_auth_headers, sample_channel_id):
        """Test listing A/B tests filtered by channel."""
        response = client.get(
            f"/api/ab-tests?channel_id={sample_channel_id}",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "tests" in data

    def test_list_ab_tests_with_status_filter(self, client, admin_auth_headers):
        """Test listing A/B tests filtered by status."""
        response = client.get(
            "/api/ab-tests?status=draft",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "tests" in data

    def test_list_ab_tests_with_pagination(self, client, admin_auth_headers):
        """Test listing A/B tests with pagination."""
        response = client.get(
            "/api/ab-tests?limit=10&offset=0",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "tests" in data


class TestGetABTest:
    """Tests for GET /ab-tests/{test_id} endpoint."""

    def test_get_ab_test_success(self, client, admin_auth_headers, db_session, sample_channel_id):
        """Test successful retrieval of A/B test."""
        # First create a test
        from src.services.ab_testing_service import get_ab_testing_service

        create_data = ABTestCreate(
            channel_id=sample_channel_id,
            name="Test Get",
            variants=[
                ABTestVariantCreate(
                    name="A",
                    traffic_allocation=50,
                    configuration={},
                    position=0,
                ),
                ABTestVariantCreate(
                    name="B",
                    traffic_allocation=50,
                    configuration={},
                    position=1,
                ),
            ],
        )

        service = get_ab_testing_service(db=db_session, redis_client=None)
        test = await service.create_test(test_data=create_data)

        # Then get it
        response = client.get(
            f"/api/ab-tests/{test.id}",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test.id)
        assert data["name"] == "Test Get"

    def test_get_ab_test_not_found(self, client, admin_auth_headers):
        """Test getting non-existent A/B test."""
        response = client.get(
            f"/api/ab-tests/{uuid.uuid4()}",
            headers=admin_auth_headers,
        )

        assert response.status_code == 404

    def test_get_ab_test_unauthorized(self, client, db_session, sample_channel_id):
        """Test that unauthorized users cannot get A/B test."""
        from src.services.ab_testing_service import get_ab_testing_service

        create_data = ABTestCreate(
            channel_id=sample_channel_id,
            name="Test Get",
            variants=[
                ABTestVariantCreate(
                    name="A",
                    traffic_allocation=50,
                    configuration={},
                    position=0,
                ),
                ABTestVariantCreate(
                    name="B",
                    traffic_allocation=50,
                    configuration={},
                    position=1,
                ),
            ],
        )

        service = get_ab_testing_service(db=db_session, redis_client=None)
        test = await service.create_test(test_data=create_data)

        response = client.get(f"/api/ab-tests/{test.id}")

        assert response.status_code == 401


class TestUpdateABTest:
    """Tests for PATCH /ab-tests/{test_id} endpoint."""

    def test_update_ab_test_success(self, client, admin_auth_headers, db_session, sample_channel_id):
        """Test successful update of A/B test."""
        from src.services.ab_testing_service import get_ab_testing_service

        # Create a test
        create_data = ABTestCreate(
            channel_id=sample_channel_id,
            name="Original Name",
            variants=[
                ABTestVariantCreate(
                    name="A",
                    traffic_allocation=50,
                    configuration={},
                    position=0,
                ),
                ABTestVariantCreate(
                    name="B",
                    traffic_allocation=50,
                    configuration={},
                    position=1,
                ),
            ],
        )

        service = get_ab_testing_service(db=db_session, redis_client=None)
        test = await service.create_test(test_data=create_data)

        # Update it
        update_data = {
            "name": "Updated Name",
            "description": "Updated description",
        }

        response = client.patch(
            f"/api/ab-tests/{test.id}",
            json=update_data,
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"

    def test_update_ab_test_not_found(self, client, admin_auth_headers):
        """Test updating non-existent A/B test."""
        update_data = {"name": "Updated"}

        response = client.patch(
            f"/api/ab-tests/{uuid.uuid4()}",
            json=update_data,
            headers=admin_auth_headers,
        )

        assert response.status_code == 404

    def test_update_ab_test_non_draft_status(self, client, admin_auth_headers, db_session, sample_channel_id):
        """Test that non-draft tests cannot be updated."""
        from src.services.ab_testing_service import get_ab_testing_service
        from src.models.ab_testing import ABTest

        # Create and start a test
        create_data = ABTestCreate(
            channel_id=sample_channel_id,
            name="Test Update",
            variants=[
                ABTestVariantCreate(
                    name="A",
                    traffic_allocation=50,
                    configuration={},
                    position=0,
                ),
                ABTestVariantCreate(
                    name="B",
                    traffic_allocation=50,
                    configuration={},
                    position=1,
                ),
            ],
        )

        service = get_ab_testing_service(db=db_session, redis_client=None)
        test = await service.create_test(test_data=create_data)

        # Update status to RUNNING directly in DB
        db_session.execute(
            f"UPDATE ab_tests SET status = 'running' WHERE id = '{test.id}'"
        )
        db_session.commit()

        # Try to update
        update_data = {"name": "Updated"}

        response = client.patch(
            f"/api/ab-tests/{test.id}",
            json=update_data,
            headers=admin_auth_headers,
        )

        assert response.status_code == 400


class TestDeleteABTest:
    """Tests for DELETE /ab-tests/{test_id} endpoint."""

    def test_delete_ab_test_success(self, client, admin_auth_headers, db_session, sample_channel_id):
        """Test successful deletion of A/B test."""
        from src.services.ab_testing_service import get_ab_testing_service

        # Create a test
        create_data = ABTestCreate(
            channel_id=sample_channel_id,
            name="Test Delete",
            variants=[
                ABTestVariantCreate(
                    name="A",
                    traffic_allocation=50,
                    configuration={},
                    position=0,
                ),
                ABTestVariantCreate(
                    name="B",
                    traffic_allocation=50,
                    configuration={},
                    position=1,
                ),
            ],
        )

        service = get_ab_testing_service(db=db_session, redis_client=None)
        test = await service.create_test(test_data=create_data)

        # Delete it
        response = client.delete(
            f"/api/ab-tests/{test.id}",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_delete_ab_test_not_found(self, client, admin_auth_headers):
        """Test deleting non-existent A/B test."""
        response = client.delete(
            f"/api/ab-tests/{uuid.uuid4()}",
            headers=admin_auth_headers,
        )

        assert response.status_code == 404

    def test_delete_ab_test_running_status(self, client, admin_auth_headers, db_session, sample_channel_id):
        """Test that running tests cannot be deleted."""
        from src.services.ab_testing_service import get_ab_testing_service

        # Create a test
        create_data = ABTestCreate(
            channel_id=sample_channel_id,
            name="Test Delete Running",
            variants=[
                ABTestVariantCreate(
                    name="A",
                    traffic_allocation=50,
                    configuration={},
                    position=0,
                ),
                ABTestVariantCreate(
                    name="B",
                    traffic_allocation=50,
                    configuration={},
                    position=1,
                ),
            ],
        )

        service = get_ab_testing_service(db=db_session, redis_client=None)
        test = await service.create_test(test_data=create_data)

        # Start it
        await service.start_test(test_id=test.id)

        # Try to delete
        response = client.delete(
            f"/api/ab-tests/{test.id}",
            headers=admin_auth_headers,
        )

        assert response.status_code == 400


class TestStartABTest:
    """Tests for POST /ab-tests/{test_id}/start endpoint."""

    def test_start_ab_test_success(self, client, admin_auth_headers, db_session, sample_channel_id):
        """Test successful start of A/B test."""
        from src.services.ab_testing_service import get_ab_testing_service

        # Create a test
        create_data = ABTestCreate(
            channel_id=sample_channel_id,
            name="Test Start",
            variants=[
                ABTestVariantCreate(
                    name="A",
                    traffic_allocation=50,
                    configuration={},
                    position=0,
                ),
                ABTestVariantCreate(
                    name="B",
                    traffic_allocation=50,
                    configuration={},
                    position=1,
                ),
            ],
        )

        service = get_ab_testing_service(db=db_session, redis_client=None)
        test = await service.create_test(test_data=create_data)

        # Start it
        response = client.post(
            f"/api/ab-tests/{test.id}/start",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == ABTestStatus.RUNNING.value
        assert data["start_time"] is not None

    def test_start_ab_test_not_found(self, client, admin_auth_headers):
        """Test starting non-existent A/B test."""
        response = client.post(
            f"/api/ab-tests/{uuid.uuid4()}/start",
            headers=admin_auth_headers,
        )

        assert response.status_code == 400

    def test_start_ab_test_invalid_status(self, client, admin_auth_headers, db_session, sample_channel_id):
        """Test starting test with invalid status."""
        from src.services.ab_testing_service import get_ab_testing_service

        # Create and complete a test
        create_data = ABTestCreate(
            channel_id=sample_channel_id,
            name="Test Start Invalid",
            variants=[
                ABTestVariantCreate(
                    name="A",
                    traffic_allocation=50,
                    configuration={},
                    position=0,
                ),
                ABTestVariantCreate(
                    name="B",
                    traffic_allocation=50,
                    configuration={},
                    position=1,
                ),
            ],
        )

        service = get_ab_testing_service(db=db_session, redis_client=None)
        test = await service.create_test(test_data=create_data)
        await service.start_test(test_id=test.id)
        await service.stop_test(test_id=test.id, select_winner=False)

        # Try to start again
        response = client.post(
            f"/api/ab-tests/{test.id}/start",
            headers=admin_auth_headers,
        )

        assert response.status_code == 400


class TestStopABTest:
    """Tests for POST /ab-tests/{test_id}/stop endpoint."""

    def test_stop_ab_test_success(self, client, admin_auth_headers, db_session, sample_channel_id):
        """Test successful stop of A/B test."""
        from src.services.ab_testing_service import get_ab_testing_service

        # Create and start a test
        create_data = ABTestCreate(
            channel_id=sample_channel_id,
            name="Test Stop",
            variants=[
                ABTestVariantCreate(
                    name="A",
                    traffic_allocation=50,
                    configuration={},
                    position=0,
                ),
                ABTestVariantCreate(
                    name="B",
                    traffic_allocation=50,
                    configuration={},
                    position=1,
                ),
            ],
        )

        service = get_ab_testing_service(db=db_session, redis_client=None)
        test = await service.create_test(test_data=create_data)
        await service.start_test(test_id=test.id)

        # Stop it
        response = client.post(
            f"/api/ab-tests/{test.id}/stop",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == ABTestStatus.STOPPED.value
        assert data["end_time"] is not None

    def test_stop_ab_test_not_found(self, client, admin_auth_headers):
        """Test stopping non-existent A/B test."""
        response = client.post(
            f"/api/ab-tests/{uuid.uuid4()}/stop",
            headers=admin_auth_headers,
        )

        assert response.status_code == 400

    def test_stop_ab_test_with_manual_winner(self, client, admin_auth_headers, db_session, sample_channel_id):
        """Test stopping test with manual winner selection."""
        from src.services.ab_testing_service import get_ab_testing_service

        # Create and start a test
        create_data = ABTestCreate(
            channel_id=sample_channel_id,
            name="Test Stop Manual",
            variants=[
                ABTestVariantCreate(
                    name="A",
                    traffic_allocation=50,
                    configuration={},
                    position=0,
                ),
                ABTestVariantCreate(
                    name="B",
                    traffic_allocation=50,
                    configuration={},
                    position=1,
                ),
            ],
        )

        service = get_ab_testing_service(db=db_session, redis_client=None)
        test = await service.create_test(test_data=create_data)
        await service.start_test(test_id=test.id)

        # Get variant ID
        test_response = await service.get_test(test_id=test.id)
        winner_id = test_response.variants[0].id

        # Stop with manual winner
        response = client.post(
            f"/api/ab-tests/{test.id}/stop?winner_variant_id={winner_id}&select_winner=false",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["winner_variant_id"] == str(winner_id)


class TestAnalyzeABTest:
    """Tests for GET /ab-tests/{test_id}/analysis endpoint."""

    def test_analyze_ab_test_success(self, client, admin_auth_headers, db_session, sample_channel_id):
        """Test successful analysis of A/B test."""
        from src.services.ab_testing_service import get_ab_testing_service

        # Create and start a test
        create_data = ABTestCreate(
            channel_id=sample_channel_id,
            name="Test Analyze",
            variants=[
                ABTestVariantCreate(
                    name="A",
                    traffic_allocation=50,
                    configuration={},
                    position=0,
                ),
                ABTestVariantCreate(
                    name="B",
                    traffic_allocation=50,
                    configuration={},
                    position=1,
                ),
            ],
        )

        service = get_ab_testing_service(db=db_session, redis_client=None)
        test = await service.create_test(test_data=create_data)
        await service.start_test(test_id=test.id)

        # Analyze it
        response = client.get(
            f"/api/ab-tests/{test.id}/analysis",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "test_id" in data
        assert "variants" in data
        assert "confidence_level" in data

    def test_analyze_ab_test_with_custom_confidence(self, client, admin_auth_headers, db_session, sample_channel_id):
        """Test analysis with custom confidence level."""
        from src.services.ab_testing_service import get_ab_testing_service

        # Create a test
        create_data = ABTestCreate(
            channel_id=sample_channel_id,
            name="Test Analyze Confidence",
            variants=[
                ABTestVariantCreate(
                    name="A",
                    traffic_allocation=50,
                    configuration={},
                    position=0,
                ),
                ABTestVariantCreate(
                    name="B",
                    traffic_allocation=50,
                    configuration={},
                    position=1,
                ),
            ],
        )

        service = get_ab_testing_service(db=db_session, redis_client=None)
        test = await service.create_test(test_data=create_data)

        # Analyze with custom confidence
        response = client.get(
            f"/api/ab-tests/{test.id}/analysis?confidence_level=0.99",
            headers=admin_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["confidence_level"] == 99.0

    def test_analyze_ab_test_invalid_confidence(self, client, admin_auth_headers, db_session, sample_channel_id):
        """Test analysis with invalid confidence level."""
        from src.services.ab_testing_service import get_ab_testing_service

        # Create a test
        create_data = ABTestCreate(
            channel_id=sample_channel_id,
            name="Test Analyze Invalid",
            variants=[
                ABTestVariantCreate(
                    name="A",
                    traffic_allocation=50,
                    configuration={},
                    position=0,
                ),
                ABTestVariantCreate(
                    name="B",
                    traffic_allocation=50,
                    configuration={},
                    position=1,
                ),
            ],
        )

        service = get_ab_testing_service(db=db_session, redis_client=None)
        test = await service.create_test(test_data=create_data)

        # Try invalid confidence
        response = client.get(
            f"/api/ab-tests/{test.id}/analysis?confidence_level=1.5",
            headers=admin_auth_headers,
        )

        assert response.status_code == 422  # Validation error


class TestRecordMetric:
    """Tests for POST /ab-tests/metrics endpoint."""

    def test_record_metric_success(self, client, admin_auth_headers, db_session, sample_channel_id):
        """Test successful metric recording."""
        from src.services.ab_testing_service import get_ab_testing_service

        # Create a test
        create_data = ABTestCreate(
            channel_id=sample_channel_id,
            name="Test Metric",
            variants=[
                ABTestVariantCreate(
                    name="A",
                    traffic_allocation=50,
                    configuration={},
                    position=0,
                ),
                ABTestVariantCreate(
                    name="B",
                    traffic_allocation=50,
                    configuration={},
                    position=1,
                ),
            ],
        )

        service = get_ab_testing_service(db=db_session, redis_client=None)
        test = await service.create_test(test_data=create_data)

        # Get variant ID
        variant_id = test.variants[0].id

        # Record metric
        metric_data = {
            "variant_id": str(variant_id),
            "metric_type": "impressions",
            "metric_value": 100,
            "metadata": {"source": "web"},
        }

        response = client.post(
            "/api/ab-tests/metrics",
            json=metric_data,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["variant_id"] == str(variant_id)
        assert data["metric_type"] == "impressions"
        assert data["metric_value"] == 100

    def test_record_metric_invalid_variant(self, client):
        """Test recording metric for non-existent variant."""
        metric_data = {
            "variant_id": str(uuid.uuid4()),
            "metric_type": "impressions",
            "metric_value": 100,
        }

        response = client.post(
            "/api/ab-tests/metrics",
            json=metric_data,
        )

        assert response.status_code == 400

    def test_record_metric_invalid_metric_type(self, client, admin_auth_headers, db_session, sample_channel_id):
        """Test recording metric with invalid type."""
        from src.services.ab_testing_service import get_ab_testing_service

        # Create a test
        create_data = ABTestCreate(
            channel_id=sample_channel_id,
            name="Test Metric Invalid",
            variants=[
                ABTestVariantCreate(
                    name="A",
                    traffic_allocation=50,
                    configuration={},
                    position=0,
                ),
                ABTestVariantCreate(
                    name="B",
                    traffic_allocation=50,
                    configuration={},
                    position=1,
                ),
            ],
        )

        service = get_ab_testing_service(db=db_session, redis_client=None)
        test = await service.create_test(test_data=create_data)
        variant_id = test.variants[0].id

        # Try invalid metric type
        metric_data = {
            "variant_id": str(variant_id),
            "metric_type": "invalid_type",
            "metric_value": 100,
        }

        response = client.post(
            "/api/ab-tests/metrics",
            json=metric_data,
        )

        assert response.status_code == 422  # Validation error

    def test_record_metric_negative_value(self, client, admin_auth_headers, db_session, sample_channel_id):
        """Test recording metric with negative value."""
        from src.services.ab_testing_service import get_ab_testing_service

        # Create a test
        create_data = ABTestCreate(
            channel_id=sample_channel_id,
            name="Test Metric Negative",
            variants=[
                ABTestVariantCreate(
                    name="A",
                    traffic_allocation=50,
                    configuration={},
                    position=0,
                ),
                ABTestVariantCreate(
                    name="B",
                    traffic_allocation=50,
                    configuration={},
                    position=1,
                ),
            ],
        )

        service = get_ab_testing_service(db=db_session, redis_client=None)
        test = await service.create_test(test_data=create_data)
        variant_id = test.variants[0].id

        # Try negative value
        metric_data = {
            "variant_id": str(variant_id),
            "metric_type": "impressions",
            "metric_value": -10,
        }

        response = client.post(
            "/api/ab-tests/metrics",
            json=metric_data,
        )

        assert response.status_code == 422  # Validation error
