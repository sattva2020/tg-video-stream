"""
Unit tests for A/B Testing Service
Feature: 016-a-b-testing-framework-for-content
"""

import pytest
import uuid
from unittest.mock import MagicMock, patch, AsyncMock
from decimal import Decimal

from src.services.ab_testing_service import ABTestingService, get_ab_testing_service
from src.models.ab_testing import ABTest, ABTestVariant, ABTestMetric, ABTestStatus
from src.schemas.ab_testing import (
    ABTestCreate,
    ABTestUpdate,
    ABTestVariantCreate,
    ABTestMetricCreate,
)


@pytest.fixture
def mock_db_session():
    """Pytest fixture for a mock SQLAlchemy session."""
    db_session = MagicMock()
    db_session.add = MagicMock()
    db_session.flush = MagicMock()
    db_session.commit = MagicMock()
    db_session.refresh = MagicMock()
    db_session.delete = MagicMock()
    db_session.execute = MagicMock()
    return db_session


@pytest.fixture
def sample_channel_id():
    """Sample channel ID for testing."""
    return uuid.uuid4()


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing."""
    return uuid.uuid4()


@pytest.fixture
def sample_test_create(sample_channel_id):
    """Sample ABTestCreate data."""
    return ABTestCreate(
        channel_id=sample_channel_id,
        name="Test A/B Test",
        description="Testing video variants",
        hypothesis="Variant B will have higher engagement",
        planned_duration_hours=24,
        traffic_config={"algorithm": "weighted", "auto_stop": True},
        variants=[
            ABTestVariantCreate(
                name="Variant A",
                description="Control variant",
                traffic_allocation=50,
                configuration={"type": "playlist", "playlist_id": str(uuid.uuid4())},
                position=0,
            ),
            ABTestVariantCreate(
                name="Variant B",
                description="Test variant",
                traffic_allocation=50,
                configuration={"type": "playlist", "playlist_id": str(uuid.uuid4())},
                position=1,
            ),
        ],
    )


@pytest.fixture
def sample_test(sample_channel_id):
    """Sample ABTest object."""
    test = ABTest(
        id=uuid.uuid4(),
        channel_id=sample_channel_id,
        name="Test A/B Test",
        description="Testing video variants",
        hypothesis="Variant B will have higher engagement",
        status=ABTestStatus.DRAFT,
        planned_duration_hours=24,
        traffic_config={"algorithm": "weighted"},
    )
    return test


@pytest.fixture
def sample_variants(sample_test):
    """Sample ABTestVariant objects."""
    variant1 = ABTestVariant(
        id=uuid.uuid4(),
        test_id=sample_test.id,
        name="Variant A",
        description="Control variant",
        traffic_allocation=50,
        configuration={"type": "playlist"},
        position=0,
    )
    variant2 = ABTestVariant(
        id=uuid.uuid4(),
        test_id=sample_test.id,
        name="Variant B",
        description="Test variant",
        traffic_allocation=50,
        configuration={"type": "playlist"},
        position=1,
    )
    return [variant1, variant2]


class TestABTestingServiceInitialization:
    """Tests for ABTestingService initialization."""

    def test_service_initialization_with_db(self, mock_db_session):
        """Test service initialization with database session."""
        service = ABTestingService(db=mock_db_session, redis_client=None)
        assert service.db == mock_db_session
        assert service.redis is None

    def test_service_initialization_with_redis(self, mock_db_session):
        """Test service initialization with Redis client."""
        mock_redis = MagicMock()
        service = ABTestingService(db=mock_db_session, redis_client=mock_redis)
        assert service.db == mock_db_session
        assert service.redis == mock_redis

    def test_get_ab_testing_service_factory(self, mock_db_session):
        """Test the factory function for creating service."""
        service = get_ab_testing_service(db=mock_db_session, redis_client=None)
        assert isinstance(service, ABTestingService)
        assert service.db == mock_db_session


class TestValidateTrafficAllocation:
    """Tests for traffic allocation validation."""

    def test_valid_traffic_allocation(self, mock_db_session):
        """Test validation of valid traffic allocation."""
        service = ABTestingService(db=mock_db_session, redis_client=None)
        variants = [
            {"traffic_allocation": 50},
            {"traffic_allocation": 50},
        ]
        assert service._validate_traffic_allocation(variants) is True

    def test_traffic_allocation_sum_not_100(self, mock_db_session):
        """Test that traffic allocation sum must equal 100%."""
        service = ABTestingService(db=mock_db_session, redis_client=None)
        variants = [
            {"traffic_allocation": 60},
            {"traffic_allocation": 50},
        ]
        with pytest.raises(ValueError, match="Суммарное распределение трафика должно быть 100%"):
            service._validate_traffic_allocation(variants)

    def test_traffic_allocation_zero_total(self, mock_db_session):
        """Test that traffic allocation cannot be zero total."""
        service = ABTestingService(db=mock_db_session, redis_client=None)
        variants = [
            {"traffic_allocation": 0},
            {"traffic_allocation": 0},
        ]
        with pytest.raises(ValueError, match="Суммарное распределение трафика не может быть 0"):
            service._validate_traffic_allocation(variants)

    def test_traffic_allocation_out_of_range(self, mock_db_session):
        """Test that traffic allocation must be 0-100%."""
        service = ABTestingService(db=mock_db_session, redis_client=None)
        variants = [
            {"traffic_allocation": 150},
            {"traffic_allocation": -50},
        ]
        with pytest.raises(ValueError, match="Распределение трафика должно быть 0-100%"):
            service._validate_traffic_allocation(variants)

    def test_traffic_allocation_empty_variants(self, mock_db_session):
        """Test that at least one variant is required."""
        service = ABTestingService(db=mock_db_session, redis_client=None)
        variants = []
        with pytest.raises(ValueError, match="Должен быть хотя бы один вариант"):
            service._validate_traffic_allocation(variants)


class TestCreateTest:
    """Tests for create_test method."""

    @pytest.mark.asyncio
    async def test_create_test_success(self, mock_db_session, sample_test_create, sample_user_id):
        """Test successful creation of A/B test."""
        # Mock the execute to return None for initial queries
        mock_db_session.execute.return_value.scalar_one_or_none.return_value = None

        service = ABTestingService(db=mock_db_session, redis_client=None)

        # Mock flush to set ID
        test_id = uuid.uuid4()
        variant_ids = [uuid.uuid4(), uuid.uuid4()]

        flush_call_count = [0]

        def mock_flush():
            if flush_call_count[0] == 0:
                # First flush is for test
                sample_test_create.__dict__.setdefault('id', test_id)
            flush_call_count[0] += 1

        mock_db_session.flush.side_effect = mock_flush

        result = await service.create_test(test_data=sample_test_create, created_by=sample_user_id)

        assert result.name == sample_test_create.name
        assert result.channel_id == sample_test_create.channel_id
        assert result.status == ABTestStatus.DRAFT.value
        assert len(result.variants) == 2
        mock_db_session.add.assert_called()
        mock_db_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_create_test_invalid_traffic_allocation(self, mock_db_session):
        """Test that invalid traffic allocation raises error."""
        service = ABTestingService(db=mock_db_session, redis_client=None)

        invalid_test = ABTestCreate(
            channel_id=uuid.uuid4(),
            name="Invalid Test",
            variants=[
                ABTestVariantCreate(
                    name="Variant A",
                    traffic_allocation=150,  # Invalid
                    configuration={},
                    position=0,
                ),
            ],
        )

        with pytest.raises(ValueError, match="Распределение трафика должно быть 0-100%"):
            await service.create_test(test_data=invalid_test)


class TestGetTest:
    """Tests for get_test method."""

    @pytest.mark.asyncio
    async def test_get_test_found(self, mock_db_session, sample_test, sample_variants):
        """Test getting an existing test."""
        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = sample_test
        mock_db_session.execute.return_value = mock_query_result

        # Mock variants query
        mock_variants_result = MagicMock()
        mock_variants_result.scalars.return_value.all.return_value = sample_variants

        execute_results = [mock_query_result, mock_variants_result]
        mock_db_session.execute.side_effect = execute_results

        service = ABTestingService(db=mock_db_session, redis_client=None)
        result = await service.get_test(test_id=sample_test.id)

        assert result is not None
        assert result.id == sample_test.id
        assert result.name == sample_test.name
        assert len(result.variants) == 2

    @pytest.mark.asyncio
    async def test_get_test_not_found(self, mock_db_session):
        """Test getting a non-existent test."""
        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_query_result

        service = ABTestingService(db=mock_db_session, redis_client=None)
        result = await service.get_test(test_id=uuid.uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_get_test_with_cache(self, mock_db_session, sample_test):
        """Test getting test from cache."""
        mock_redis = AsyncMock()
        cached_data = {
            "id": str(sample_test.id),
            "name": sample_test.name,
            "channel_id": str(sample_test.channel_id),
            "status": "draft",
            "variants": [],
        }
        mock_redis.get.return_value = '{"id": "%s", "name": "%s"}' % (sample_test.id, sample_test.name)

        service = ABTestingService(db=mock_db_session, redis_client=mock_redis)

        # Mock json.loads
        with patch('src.services.ab_testing_service.json.loads', return_value=cached_data):
            result = await service.get_test(test_id=sample_test.id)

        assert result is not None


class TestListTests:
    """Tests for list_tests method."""

    @pytest.mark.asyncio
    async def test_list_tests_all(self, mock_db_session, sample_test):
        """Test listing all tests."""
        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        # Mock data query
        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = [sample_test]

        mock_db_session.execute.side_effect = [mock_count_result, mock_data_result]

        service = ABTestingService(db=mock_db_session, redis_client=None)
        result = await service.list_tests()

        assert result.total == 1
        assert len(result.tests) == 1

    @pytest.mark.asyncio
    async def test_list_tests_with_filters(self, mock_db_session, sample_test):
        """Test listing tests with channel and status filters."""
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_data_result = MagicMock()
        mock_data_result.scalars.return_value.all.return_value = [sample_test]

        mock_db_session.execute.side_effect = [mock_count_result, mock_data_result]

        service = ABTestingService(db=mock_db_session, redis_client=None)
        result = await service.list_tests(
            channel_id=sample_test.channel_id,
            status="draft",
            limit=10,
            offset=0,
        )

        assert result.total == 1
        assert len(result.tests) == 1


class TestUpdateTest:
    """Tests for update_test method."""

    @pytest.mark.asyncio
    async def test_update_test_success(self, mock_db_session, sample_test):
        """Test successful update of test."""
        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = sample_test
        mock_db_session.execute.return_value = mock_query_result

        service = ABTestingService(db=mock_db_session, redis_client=None)

        update_data = ABTestUpdate(
            name="Updated Test Name",
            description="Updated description",
        )

        with patch.object(service, 'get_test', return_value=MagicMock()) as mock_get:
            result = await service.update_test(test_id=sample_test.id, test_data=update_data)

        assert sample_test.name == "Updated Test Name"
        assert sample_test.description == "Updated description"
        mock_db_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_update_test_not_found(self, mock_db_session):
        """Test updating non-existent test."""
        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_query_result

        service = ABTestingService(db=mock_db_session, redis_client=None)

        update_data = ABTestUpdate(name="Updated")
        result = await service.update_test(test_id=uuid.uuid4(), test_data=update_data)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_test_non_draft_status(self, mock_db_session, sample_test):
        """Test that non-draft tests cannot be updated."""
        sample_test.status = ABTestStatus.RUNNING

        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = sample_test
        mock_db_session.execute.return_value = mock_query_result

        service = ABTestingService(db=mock_db_session, redis_client=None)

        update_data = ABTestUpdate(name="Updated")

        with pytest.raises(ValueError, match="Можно обновлять только тесты в статусе draft"):
            await service.update_test(test_id=sample_test.id, test_data=update_data)


class TestDeleteTest:
    """Tests for delete_test method."""

    @pytest.mark.asyncio
    async def test_delete_test_success(self, mock_db_session, sample_test):
        """Test successful deletion of test."""
        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = sample_test
        mock_db_session.execute.return_value = mock_query_result

        service = ABTestingService(db=mock_db_session, redis_client=None)
        result = await service.delete_test(test_id=sample_test.id)

        assert result is True
        mock_db_session.delete.assert_called_once_with(sample_test)
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_test_not_found(self, mock_db_session):
        """Test deleting non-existent test."""
        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_query_result

        service = ABTestingService(db=mock_db_session, redis_client=None)
        result = await service.delete_test(test_id=uuid.uuid4())

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_test_running_status(self, mock_db_session, sample_test):
        """Test that running tests cannot be deleted."""
        sample_test.status = ABTestStatus.RUNNING

        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = sample_test
        mock_db_session.execute.return_value = mock_query_result

        service = ABTestingService(db=mock_db_session, redis_client=None)

        with pytest.raises(ValueError, match="Нельзя удалять запущенный тест"):
            await service.delete_test(test_id=sample_test.id)


class TestStartTest:
    """Tests for start_test method."""

    @pytest.mark.asyncio
    async def test_start_test_success(self, mock_db_session, sample_test):
        """Test successful start of test."""
        sample_test.status = ABTestStatus.DRAFT

        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = sample_test
        mock_db_session.execute.return_value = mock_query_result

        # Mock variant count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2

        execute_results = [mock_query_result, mock_count_result]
        mock_db_session.execute.side_effect = execute_results

        service = ABTestingService(db=mock_db_session, redis_client=None)
        result = await service.start_test(test_id=sample_test.id)

        assert result.test_id == sample_test.id
        assert result.status == ABTestStatus.RUNNING.value
        assert sample_test.status == ABTestStatus.RUNNING
        assert sample_test.start_time is not None
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_test_not_found(self, mock_db_session):
        """Test starting non-existent test."""
        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_query_result

        service = ABTestingService(db=mock_db_session, redis_client=None)

        with pytest.raises(ValueError, match="не найден"):
            await service.start_test(test_id=uuid.uuid4())

    @pytest.mark.asyncio
    async def test_start_test_invalid_status(self, mock_db_session, sample_test):
        """Test starting test with invalid status."""
        sample_test.status = ABTestStatus.COMPLETED

        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = sample_test
        mock_db_session.execute.return_value = mock_query_result

        service = ABTestingService(db=mock_db_session, redis_client=None)

        with pytest.raises(ValueError, match="Можно запустить только тест в статусе draft или paused"):
            await service.start_test(test_id=sample_test.id)

    @pytest.mark.asyncio
    async def test_start_test_insufficient_variants(self, mock_db_session, sample_test):
        """Test starting test with less than 2 variants."""
        sample_test.status = ABTestStatus.DRAFT

        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = sample_test

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        execute_results = [mock_query_result, mock_count_result]
        mock_db_session.execute.side_effect = execute_results

        service = ABTestingService(db=mock_db_session, redis_client=None)

        with pytest.raises(ValueError, match="Для запуска теста нужно минимум 2 варианта"):
            await service.start_test(test_id=sample_test.id)


class TestStopTest:
    """Tests for stop_test method."""

    @pytest.mark.asyncio
    async def test_stop_test_success(self, mock_db_session, sample_test):
        """Test successful stop of test."""
        sample_test.status = ABTestStatus.RUNNING

        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = sample_test
        mock_db_session.execute.return_value = mock_query_result

        service = ABTestingService(db=mock_db_session, redis_client=None)

        with patch.object(service, 'analyze_test', return_value=MagicMock(
            winner_variant_id=None,
            confidence_level=0.95,
            is_significant=False
        )):
            result = await service.stop_test(test_id=sample_test.id, select_winner=False)

        assert result.test_id == sample_test.id
        assert result.status == ABTestStatus.STOPPED.value
        assert sample_test.status == ABTestStatus.STOPPED
        assert sample_test.end_time is not None
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_test_not_found(self, mock_db_session):
        """Test stopping non-existent test."""
        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_query_result

        service = ABTestingService(db=mock_db_session, redis_client=None)

        with pytest.raises(ValueError, match="не найден"):
            await service.stop_test(test_id=uuid.uuid4())

    @pytest.mark.asyncio
    async def test_stop_test_invalid_status(self, mock_db_session, sample_test):
        """Test stopping test with invalid status."""
        sample_test.status = ABTestStatus.DRAFT

        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = sample_test
        mock_db_session.execute.return_value = mock_query_result

        service = ABTestingService(db=mock_db_session, redis_client=None)

        with pytest.raises(ValueError, match="Можно остановить только запущенный тест"):
            await service.stop_test(test_id=sample_test.id)


class TestRecordMetric:
    """Tests for record_metric method."""

    @pytest.mark.asyncio
    async def test_record_metric_success(self, mock_db_session, sample_variants):
        """Test successful metric recording."""
        variant = sample_variants[0]

        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = variant
        mock_db_session.execute.return_value = mock_query_result

        service = ABTestingService(db=mock_db_session, redis_client=None)

        metric_data = ABTestMetricCreate(
            variant_id=variant.id,
            metric_type="impressions",
            metric_value=100,
            metadata={"source": "web"},
        )

        result = await service.record_metric(metric_data=metric_data)

        assert result.variant_id == variant.id
        assert result.metric_type == "impressions"
        assert result.metric_value == 100
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_metric_variant_not_found(self, mock_db_session):
        """Test recording metric for non-existent variant."""
        mock_query_result = MagicMock()
        mock_query_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_query_result

        service = ABTestingService(db=mock_db_session, redis_client=None)

        metric_data = ABTestMetricCreate(
            variant_id=uuid.uuid4(),
            metric_type="impressions",
            metric_value=100,
        )

        with pytest.raises(ValueError, match="не найден"):
            await service.record_metric(metric_data=metric_data)


class TestStatisticalCalculations:
    """Tests for statistical calculation methods."""

    def test_get_z_critical_standard_levels(self, mock_db_session):
        """Test Z-critical values for standard confidence levels."""
        service = ABTestingService(db=mock_db_session, redis_client=None)

        assert service._get_z_critical(0.90) == 1.645
        assert service._get_z_critical(0.95) == 1.96
        assert service._get_z_critical(0.99) == 2.576

    def test_get_z_critical_custom_level(self, mock_db_session):
        """Test Z-critical calculation for custom confidence level."""
        service = ABTestingService(db=mock_db_session, redis_client=None)

        z = service._get_z_critical(0.975)
        assert 1.9 < z < 2.0  # Should be around 1.96

    def test_calculate_p_value_two_tailed(self, mock_db_session):
        """Test p-value calculation for two-tailed test."""
        service = ABTestingService(db=mock_db_session, redis_client=None)

        p_value = service._calculate_p_value(1.96, two_tailed=True)
        assert 0.04 < p_value < 0.06  # Should be around 0.05

    def test_calculate_p_value_one_tailed(self, mock_db_session):
        """Test p-value calculation for one-tailed test."""
        service = ABTestingService(db=mock_db_session, redis_client=None)

        p_value = service._calculate_p_value(1.645, two_tailed=False)
        assert 0.04 < p_value < 0.06  # Should be around 0.05

    @pytest.mark.asyncio
    async def test_calculate_statistical_significance_valid(self, mock_db_session):
        """Test statistical significance calculation with valid data."""
        service = ABTestingService(db=mock_db_session, redis_client=None)

        is_significant, p_value, z_score = await service.calculate_statistical_significance(
            control_conversions=100,
            control_total=1000,
            treatment_conversions=120,
            treatment_total=1000,
            confidence_level=0.95,
        )

        assert isinstance(is_significant, bool)
        assert p_value is not None
        assert z_score is not None

    @pytest.mark.asyncio
    async def test_calculate_statistical_significance_invalid_input(self, mock_db_session):
        """Test statistical significance with invalid input."""
        service = ABTestingService(db=mock_db_session, redis_client=None)

        with pytest.raises(ValueError, match="Размер выборки должен быть положительным"):
            await service.calculate_statistical_significance(
                control_conversions=100,
                control_total=0,
                treatment_conversions=120,
                treatment_total=1000,
            )

    @pytest.mark.asyncio
    async def test_calculate_confidence_interval_valid(self, mock_db_session):
        """Test confidence interval calculation with valid data."""
        service = ABTestingService(db=mock_db_session, redis_client=None)

        lower, upper = await service.calculate_confidence_interval(
            conversions=100,
            total=1000,
            confidence_level=0.95,
        )

        assert lower is not None
        assert upper is not None
        assert 0.0 <= lower <= upper <= 1.0

    @pytest.mark.asyncio
    async def test_calculate_confidence_interval_invalid_input(self, mock_db_session):
        """Test confidence interval with invalid input."""
        service = ABTestingService(db=mock_db_session, redis_client=None)

        with pytest.raises(ValueError, match="Размер выборки должен быть положительным"):
            await service.calculate_confidence_interval(
                conversions=100,
                total=0,
                confidence_level=0.95,
            )

    @pytest.mark.asyncio
    async def test_calculate_confidence_interval_zero_conversions(self, mock_db_session):
        """Test confidence interval with zero conversions."""
        service = ABTestingService(db=mock_db_session, redis_client=None)

        lower, upper = await service.calculate_confidence_interval(
            conversions=0,
            total=1000,
            confidence_level=0.95,
        )

        assert lower is not None
        assert upper is not None
        assert lower >= 0.0

    @pytest.mark.asyncio
    async def test_calculate_t_test_valid(self, mock_db_session):
        """Test t-test calculation with valid data."""
        service = ABTestingService(db=mock_db_session, redis_client=None)

        is_significant, p_value, t_score = await service.calculate_t_test(
            control_mean=100.0,
            control_std=15.0,
            control_size=100,
            treatment_mean=105.0,
            treatment_std=15.0,
            treatment_size=100,
            confidence_level=0.95,
        )

        assert isinstance(is_significant, bool)
        assert p_value is not None
        assert t_score is not None

    @pytest.mark.asyncio
    async def test_calculate_t_test_invalid_input(self, mock_db_session):
        """Test t-test with invalid input."""
        service = ABTestingService(db=mock_db_session, redis_client=None)

        with pytest.raises(ValueError, match="Размер выборки должен быть положительным"):
            await service.calculate_t_test(
                control_mean=100.0,
                control_std=15.0,
                control_size=0,
                treatment_mean=105.0,
                treatment_std=15.0,
                treatment_size=100,
            )
