"""
Тесты обнаружения и разрешения конфликтов в расписании.

Покрывает:
- Создание пересекающихся слотов расписания
- Обнаружение конфликтов
- Разрешение конфликтов на основе приоритетов
- Предложение альтернативного времени для перемещаемых слотов
- Проверку работы системы приоритетов
"""

import pytest
from datetime import datetime, date, time, timedelta
from uuid import uuid4

from src.models.schedule import ScheduleSlot, Playlist, PlaylistItem, RepeatType
from src.models.user import User, UserRole, UserStatus
from src.models.telegram import Channel
from src.services.schedule_optimization_service import ScheduleOptimizationService
from src.schemas.schedule_ai import ConflictDetectionRequest

# ==================== Constants ====================

TEST_CHANNEL_ID = "12345678-1234-5678-1234-567812345678"

# ==================== Fixtures ====================

@pytest.fixture
def admin_user(db_session) -> User:
    """Создаёт администратора для тестов."""
    user = User(
        email="admin@test.com",
        hashed_password="hashed",
        role=UserRole.ADMIN,
        status=UserStatus.APPROVED,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_playlist(db_session, admin_user: User) -> Playlist:
    """Создаёт тестовый плейлист."""
    playlist = Playlist(
        name="Test Playlist",
        description="Playlist for conflict testing",
        user_id=admin_user.id,
    )
    db_session.add(playlist)
    db_session.commit()
    db_session.refresh(playlist)

    # Добавляем треки в плейлист
    items = [
        PlaylistItem(
            id=uuid4(),
            playlist_id=playlist.id,
            url=f"https://youtube.com/watch?v={i}",
            title=f"Track {i}",
            duration=180,
            position=i,
        ) for i in range(1, 4)
    ]
    db_session.add_all(items)
    db_session.commit()

    return playlist


@pytest.fixture
def test_channel(db_session, admin_user: User) -> Channel:
    """Создаёт тестовый канал."""
    from src.models.telegram import TelegramAccount

    # Создаём TelegramAccount
    account = TelegramAccount(
        user_id=admin_user.id,
        phone="000000",
        encrypted_session="x",
        tg_user_id=12345,
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)

    # Создаём канал
    channel = Channel(
        id=uuid4(),
        account_id=account.id,
        chat_id=-1001234567890,
        title="Test Channel",
        username="testchannel",
    )
    db_session.add(channel)
    db_session.commit()
    db_session.refresh(channel)

    return channel


@pytest.fixture
def optimization_service(db_session):
    """Создаёт экземпляр ScheduleOptimizationService для тестов."""
    return ScheduleOptimizationService(db_session)


# ==================== Helper Functions ====================

def create_overlapping_slots(
    db_session,
    channel_id: str,
    playlist_id: str,
    test_date: date,
    priority_high: int = 10,
    priority_low: int = 5
) -> tuple[ScheduleSlot, ScheduleSlot]:
    """
    Создаёт два пересекающихся слота с разными приоритетами.

    Args:
        db_session: Сессия базы данных
        channel_id: ID канала
        playlist_id: ID плейлиста
        test_date: Дата для создания слотов
        priority_high: Приоритет для первого слота (высокий)
        priority_low: Приоритет для второго слота (низкий)

    Returns:
        Кортеж из двух созданных слотов
    """
    # Первый слот: 10:00 - 12:00 (высокий приоритет)
    slot1 = ScheduleSlot(
        id=uuid4(),
        channel_id=uuid4() if isinstance(channel_id, str) else channel_id,
        playlist_id=playlist_id,
        start_date=test_date,
        start_time=time(10, 0),
        end_time=time(12, 0),
        title="High Priority Slot",
        priority=priority_high,
        is_active=True,
        repeat_type=RepeatType.NONE,
        created_by=uuid4(),
    )
    db_session.add(slot1)

    # Второй слот: 11:00 - 13:00 (низкий приоритет, пересекается с первым)
    slot2 = ScheduleSlot(
        id=uuid4(),
        channel_id=slot1.channel_id,
        playlist_id=playlist_id,
        start_date=test_date,
        start_time=time(11, 0),
        end_time=time(13, 0),
        title="Low Priority Slot",
        priority=priority_low,
        is_active=True,
        repeat_type=RepeatType.NONE,
        created_by=uuid4(),
    )
    db_session.add(slot2)

    db_session.commit()
    db_session.refresh(slot1)
    db_session.refresh(slot2)

    return slot1, slot2


def create_multiple_conflicts(
    db_session,
    channel_id: str,
    playlist_id: str,
    test_date: date
) -> list[ScheduleSlot]:
    """
    Создаёт несколько слотов с различными конфликтами.

    Создаёт 3 слота:
    - Slot 1: 08:00 - 10:00 (priority 10)
    - Slot 2: 09:00 - 11:00 (priority 5) - конфликтует с Slot 1
    - Slot 3: 10:00 - 12:00 (priority 7) - конфликтует с Slot 2

    Args:
        db_session: Сессия базы данных
        channel_id: ID канала
        playlist_id: ID плейлиста
        test_date: Дата для создания слотов

    Returns:
        Список созданных слотов
    """
    channel_uuid = uuid4() if isinstance(channel_id, str) else channel_id

    slots = [
        ScheduleSlot(
            id=uuid4(),
            channel_id=channel_uuid,
            playlist_id=playlist_id,
            start_date=test_date,
            start_time=time(8, 0),
            end_time=time(10, 0),
            title=f"Slot {i+1}",
            priority=priority,
            is_active=True,
            repeat_type=RepeatType.NONE,
            created_by=uuid4(),
        )
        for i, priority in enumerate([10, 5, 7])
    ]

    db_session.add_all(slots)
    db_session.commit()

    for slot in slots:
        db_session.refresh(slot)

    return slots


# ==================== Test Classes ====================

class TestConflictDetection:
    """Тесты обнаружения конфликтов."""

    @pytest.mark.asyncio
    async def test_detect_conflicts_with_overlapping_slots(
        self, db_session, optimization_service, test_channel, test_playlist
    ):
        """
        Тест обнаружения конфликтов при наличии пересекающихся слотов.

        Создаёт два пересекающихся слота и проверяет, что конфликт обнаружен.
        """
        # Создаём пересекающиеся слоты
        test_date = date(2025, 1, 25)
        slot1, slot2 = create_overlapping_slots(
            db_session,
            str(test_channel.id),
            test_playlist.id,
            test_date,
            priority_high=10,
            priority_low=5
        )

        # Запускаем обнаружение конфликтов
        request = ConflictDetectionRequest(
            channel_id=str(test_channel.id),
            start_date=test_date,
            end_date=test_date
        )

        response = await optimization_service.detect_conflicts(request)

        # Проверяем результаты
        assert response.total_conflicts == 1, "Должен быть обнаружен 1 конфликт"
        assert len(response.conflicts) == 1, "Должна быть 1 группа конфликтов"

        conflict_group = response.conflicts[0]
        assert conflict_group.date == test_date, "Дата конфликта должна совпадать"
        assert len(conflict_group.conflicts) == 2, "В группе должно быть 2 конфликтующих слота"

        # Проверяем информацию о конфликтах
        slot_ids = {c.slot_id for c in conflict_group.conflicts}
        assert str(slot1.id) in slot_ids, "ID первого слота должен быть в конфликте"
        assert str(slot2.id) in slot_ids, "ID второго слота должен быть в конфликте"

    @pytest.mark.asyncio
    async def test_detect_conflicts_no_conflicts(
        self, db_session, optimization_service, test_channel, test_playlist
    ):
        """
        Тест обнаружения конфликтов при отсутствии пересечений.

        Создаёт два непересекающихся слота и проверяет, что конфликты не обнаружены.
        """
        test_date = date(2025, 1, 25)
        channel_uuid = test_channel.id

        # Создаём непересекающиеся слоты
        slot1 = ScheduleSlot(
            id=uuid4(),
            channel_id=channel_uuid,
            playlist_id=test_playlist.id,
            start_date=test_date,
            start_time=time(10, 0),
            end_time=time(12, 0),
            title="Non-overlapping 1",
            priority=5,
            is_active=True,
            repeat_type=RepeatType.NONE,
            created_by=uuid4(),
        )
        db_session.add(slot1)

        slot2 = ScheduleSlot(
            id=uuid4(),
            channel_id=channel_uuid,
            playlist_id=test_playlist.id,
            start_date=test_date,
            start_time=time(14, 0),
            end_time=time(16, 0),
            title="Non-overlapping 2",
            priority=5,
            is_active=True,
            repeat_type=RepeatType.NONE,
            created_by=uuid4(),
        )
        db_session.add(slot2)
        db_session.commit()

        # Запускаем обнаружение конфликтов
        request = ConflictDetectionRequest(
            channel_id=str(test_channel.id),
            start_date=test_date,
            end_date=test_date
        )

        response = await optimization_service.detect_conflicts(request)

        # Проверяем результаты
        assert response.total_conflicts == 0, "Конфликты не должны быть обнаружены"
        assert len(response.conflicts) == 0, "Список конфликтов должен быть пустым"

    @pytest.mark.asyncio
    async def test_detect_conflicts_multiple_days(
        self, db_session, optimization_service, test_channel, test_playlist
    ):
        """
        Тест обнаружения конфликтов за несколько дней.

        Создаёт конфликты на разные дни и проверяет, что все обнаружены.
        """
        # Создаём конфликты на два дня
        date1 = date(2025, 1, 25)
        date2 = date(2025, 1, 26)

        slot1_date1, slot2_date1 = create_overlapping_slots(
            db_session, str(test_channel.id), test_playlist.id, date1
        )
        slot1_date2, slot2_date2 = create_overlapping_slots(
            db_session, str(test_channel.id), test_playlist.id, date2
        )

        # Запускаем обнаружение конфликтов за период
        request = ConflictDetectionRequest(
            channel_id=str(test_channel.id),
            start_date=date1,
            end_date=date2
        )

        response = await optimization_service.detect_conflicts(request)

        # Проверяем результаты
        assert response.total_conflicts == 2, "Должно быть обнаружено 2 конфликта (по одному на каждый день)"
        assert len(response.conflicts) == 2, "Должны быть 2 группы конфликтов"

        # Проверяем, что конфликты на разные дни
        conflict_dates = {c.date for c in response.conflicts}
        assert date1 in conflict_dates, "Конфликт на первую дату должен быть обнаружен"
        assert date2 in conflict_dates, "Конфликт на вторую дату должен быть обнаружен"


class TestConflictResolution:
    """Тесты разрешения конфликтов."""

    @pytest.mark.asyncio
    async def test_resolve_conflicts_priority_system(
        self, db_session, optimization_service, test_channel, test_playlist
    ):
        """
        Тест разрешения конфликтов на основе приоритетов.

        Проверяет, что слот с более высоким приоритетом сохраняется,
        а слот с более низким приоритетом помечается для перемещения/удаления.
        """
        test_date = date(2025, 1, 25)
        slot1, slot2 = create_overlapping_slots(
            db_session,
            str(test_channel.id),
            test_playlist.id,
            test_date,
            priority_high=10,
            priority_low=5
        )

        # Запускаем разрешение конфликтов
        request = ConflictDetectionRequest(
            channel_id=str(test_channel.id),
            start_date=test_date,
            end_date=test_date
        )

        response = await optimization_service.resolve_conflicts(request)

        # Проверяем результаты
        assert response.total_conflicts == 1, "Должен быть 1 конфликт"

        conflict_group = response.conflicts[0]
        assert len(conflict_group.conflicts) == 2, "Должны быть оба слота в конфликте"

        # Находим победителя и проигравшего
        winner = next((c for c in conflict_group.conflicts if c.priority == 10), None)
        loser = next((c for c in conflict_group.conflicts if c.priority == 5), None)

        assert winner is not None, "Должен быть определён победитель с приоритетом 10"
        assert loser is not None, "Должен быть определён проигравший с приоритетом 5"
        assert winner.slot_id == str(slot1.id), "Победителем должен быть слот с более высоким приоритетом"
        assert loser.slot_id == str(slot2.id), "Проигравшим должен быть слот с более низким приоритетом"

    @pytest.mark.asyncio
    async def test_resolve_conflicts_equal_priority(
        self, db_session, optimization_service, test_channel, test_playlist
    ):
        """
        Тест разрешения конфликтов при равных приоритетах.

        При равных приоритетах первым в списке должен быть тот, кто был создан раньше
        (или с меньшим ID, в зависимости от реализации сортировки).
        """
        test_date = date(2025, 1, 25)
        slot1, slot2 = create_overlapping_slots(
            db_session,
            str(test_channel.id),
            test_playlist.id,
            test_date,
            priority_high=5,
            priority_low=5  # Равные приоритеты
        )

        # Запускаем разрешение конфликтов
        request = ConflictDetectionRequest(
            channel_id=str(test_channel.id),
            start_date=test_date,
            end_date=test_date
        )

        response = await optimization_service.resolve_conflicts(request)

        # Проверяем, что конфликт обнаружен
        assert response.total_conflicts == 1, "Конфликт должен быть обнаружен"

        # При равных приоритетах оба слота должны быть в конфликте
        conflict_group = response.conflicts[0]
        assert len(conflict_group.conflicts) == 2, "Оба слота должны быть в конфликте"

        # Все слоты должны иметь одинаковый приоритет
        priorities = {c.priority for c in conflict_group.conflicts}
        assert priorities == {5}, "Все приоритеты должны быть равны 5"

    @pytest.mark.asyncio
    async def test_resolve_conflicts_multiple_slots(
        self, db_session, optimization_service, test_channel, test_playlist
    ):
        """
        Тест разрешения конфликтов с несколькими слотами.

        Создаёт цепочку конфликтов и проверяет правильность разрешения.
        """
        test_date = date(2025, 1, 25)
        slots = create_multiple_conflicts(
            db_session,
            str(test_channel.id),
            test_playlist.id,
            test_date
        )

        # Запускаем разрешение конфликтов
        request = ConflictDetectionRequest(
            channel_id=str(test_channel.id),
            start_date=test_date,
            end_date=test_date
        )

        response = await optimization_service.resolve_conflicts(request)

        # Проверяем результаты
        assert response.total_conflicts >= 1, "Должен быть хотя бы 1 конфликт"

        # Проверяем, что слот с наивысшим приоритетом (10) является победителем
        all_conflicts = []
        for group in response.conflicts:
            all_conflicts.extend(group.conflicts)

        highest_priority_slot = next((c for c in all_conflicts if c.priority == 10), None)
        assert highest_priority_slot is not None, "Слот с приоритетом 10 должен быть в списке"

    @pytest.mark.asyncio
    async def test_alternative_time_suggestions(
        self, db_session, optimization_service, test_channel, test_playlist
    ):
        """
        Тест предложений альтернативного времени.

        Проверяет, что для перемещаемых слотов предлагаются альтернативные временные слоты.
        """
        test_date = date(2025, 1, 25)

        # Создаём слот, занимающий всё утро (08:00 - 12:00)
        channel_uuid = test_channel.id

        morning_slot = ScheduleSlot(
            id=uuid4(),
            channel_id=channel_uuid,
            playlist_id=test_playlist.id,
            start_date=test_date,
            start_time=time(8, 0),
            end_time=time(12, 0),
            title="Morning Slot",
            priority=10,
            is_active=True,
            repeat_type=RepeatType.NONE,
            created_by=uuid4(),
        )
        db_session.add(morning_slot)

        # Создаём конфликтующий слот (09:00 - 11:00)
        conflict_slot = ScheduleSlot(
            id=uuid4(),
            channel_id=channel_uuid,
            playlist_id=test_playlist.id,
            start_date=test_date,
            start_time=time(9, 0),
            end_time=time(11, 0),
            title="Conflict Slot",
            priority=5,
            is_active=True,
            repeat_type=RepeatType.NONE,
            created_by=uuid4(),
        )
        db_session.add(conflict_slot)
        db_session.commit()

        # Запускаем разрешение конфликтов
        request = ConflictDetectionRequest(
            channel_id=str(test_channel.id),
            start_date=test_date,
            end_date=test_date
        )

        response = await optimization_service.resolve_conflicts(request)

        # Проверяем, что конфликт обнаружен
        assert response.total_conflicts == 1, "Должен быть обнаружен 1 конфликт"


class TestConflictDetectionEdgeCases:
    """Тесты граничных случаев обнаружения конфликтов."""

    @pytest.mark.asyncio
    async def test_conflict_slot_boundary_touching(
        self, db_session, optimization_service, test_channel, test_playlist
    ):
        """
        Тест конфликта при граничном касании слотов.

        Если один слот заканчивается в 10:00, а другой начинается в 10:00,
        это не считается конфликтом (тест касания границ).
        """
        test_date = date(2025, 1, 25)
        channel_uuid = test_channel.id

        # Первый слот: 10:00 - 12:00
        slot1 = ScheduleSlot(
            id=uuid4(),
            channel_id=channel_uuid,
            playlist_id=test_playlist.id,
            start_date=test_date,
            start_time=time(10, 0),
            end_time=time(12, 0),
            title="Slot 1",
            priority=5,
            is_active=True,
            repeat_type=RepeatType.NONE,
            created_by=uuid4(),
        )
        db_session.add(slot1)

        # Второй слот: 12:00 - 14:00 (точно начинается, когда заканчивается первый)
        slot2 = ScheduleSlot(
            id=uuid4(),
            channel_id=channel_uuid,
            playlist_id=test_playlist.id,
            start_date=test_date,
            start_time=time(12, 0),
            end_time=time(14, 0),
            title="Slot 2",
            priority=5,
            is_active=True,
            repeat_type=RepeatType.NONE,
            created_by=uuid4(),
        )
        db_session.add(slot2)
        db_session.commit()

        # Запускаем обнаружение конфликтов
        request = ConflictDetectionRequest(
            channel_id=str(test_channel.id),
            start_date=test_date,
            end_date=test_date
        )

        response = await optimization_service.detect_conflicts(request)

        # Касание границ не считается конфликтом
        assert response.total_conflicts == 0, "Касание границ слотов не должно считаться конфликтом"

    @pytest.mark.asyncio
    async def test_conflict_one_minute_overlap(
        self, db_session, optimization_service, test_channel, test_playlist
    ):
        """
        Тест конфликта при пересечении в 1 минуту.

        Даже пересечение в 1 минуту должно считаться конфликтом.
        """
        test_date = date(2025, 1, 25)
        channel_uuid = test_channel.id

        # Первый слот: 10:00 - 12:00
        slot1 = ScheduleSlot(
            id=uuid4(),
            channel_id=channel_uuid,
            playlist_id=test_playlist.id,
            start_date=test_date,
            start_time=time(10, 0),
            end_time=time(12, 0),
            title="Slot 1",
            priority=5,
            is_active=True,
            repeat_type=RepeatType.NONE,
            created_by=uuid4(),
        )
        db_session.add(slot1)

        # Второй слот: 11:59 - 13:00 (пересечение в 1 минуту)
        slot2 = ScheduleSlot(
            id=uuid4(),
            channel_id=channel_uuid,
            playlist_id=test_playlist.id,
            start_date=test_date,
            start_time=time(11, 59),
            end_time=time(13, 0),
            title="Slot 2",
            priority=5,
            is_active=True,
            repeat_type=RepeatType.NONE,
            created_by=uuid4(),
        )
        db_session.add(slot2)
        db_session.commit()

        # Запускаем обнаружение конфликтов
        request = ConflictDetectionRequest(
            channel_id=str(test_channel.id),
            start_date=test_date,
            end_date=test_date
        )

        response = await optimization_service.detect_conflicts(request)

        # Пересечение в 1 минуту должно считаться конфликтом
        assert response.total_conflicts == 1, "Пересечение в 1 минуту должно считаться конфликтом"

    @pytest.mark.asyncio
    async def test_conflict_with_inactive_slots(
        self, db_session, optimization_service, test_channel, test_playlist
    ):
        """
        Тест обнаружения конфликтов с неактивными слотами.

        Неактивные слоты (is_active=False) не должны участвовать в проверке конфликтов.
        """
        test_date = date(2025, 1, 25)
        channel_uuid = test_channel.id

        # Первый активный слот
        slot1 = ScheduleSlot(
            id=uuid4(),
            channel_id=channel_uuid,
            playlist_id=test_playlist.id,
            start_date=test_date,
            start_time=time(10, 0),
            end_time=time(12, 0),
            title="Active Slot",
            priority=5,
            is_active=True,
            repeat_type=RepeatType.NONE,
            created_by=uuid4(),
        )
        db_session.add(slot1)

        # Второй НЕактивный слот, пересекающийся с первым
        slot2 = ScheduleSlot(
            id=uuid4(),
            channel_id=channel_uuid,
            playlist_id=test_playlist.id,
            start_date=test_date,
            start_time=time(11, 0),
            end_time=time(13, 0),
            title="Inactive Slot",
            priority=5,
            is_active=False,  # Неактивен
            repeat_type=RepeatType.NONE,
            created_by=uuid4(),
        )
        db_session.add(slot2)
        db_session.commit()

        # Запускаем обнаружение конфликтов
        request = ConflictDetectionRequest(
            channel_id=str(test_channel.id),
            start_date=test_date,
            end_date=test_date
        )

        response = await optimization_service.detect_conflicts(request)

        # Неактивные слоты не должны вызывать конфликт
        assert response.total_conflicts == 0, "Неактивные слоты не должны участвовать в проверке конфликтов"


class TestConflictResolutionIntegration:
    """Интеграционные тесты разрешения конфликтов."""

    @pytest.mark.asyncio
    async def test_full_conflict_resolution_workflow(
        self, db_session, optimization_service, test_channel, test_playlist
    ):
        """
        Полный сценарий разрешения конфликтов.

        1. Создаём конфликтующие слоты
        2. Обнаруживаем конфликты
        3. Разрешаем конфликты
        4. Проверяем приоритетную систему
        """
        test_date = date(2025, 1, 25)

        # Шаг 1: Создаём конфликтующие слоты
        slot1, slot2 = create_overlapping_slots(
            db_session,
            str(test_channel.id),
            test_playlist.id,
            test_date,
            priority_high=10,
            priority_low=5
        )

        # Шаг 2: Обнаруживаем конфликты
        detect_request = ConflictDetectionRequest(
            channel_id=str(test_channel.id),
            start_date=test_date,
            end_date=test_date
        )

        detect_response = await optimization_service.detect_conflicts(detect_request)
        assert detect_response.total_conflicts == 1, "Конфликт должен быть обнаружен"

        # Шаг 3: Разрешаем конфликты
        resolve_response = await optimization_service.resolve_conflicts(detect_request)
        assert resolve_response.total_conflicts == 1, "Конфликт должен быть разрешён"

        # Шаг 4: Проверяем приоритетную систему
        conflict_group = resolve_response.conflicts[0]
        priorities = {c.priority for c in conflict_group.conflicts}
        assert priorities == {10, 5}, "Должны быть оба приоритета"

        # Находим слот с высоким приоритетом
        high_priority = next(
            (c for c in conflict_group.conflicts if c.priority == 10),
            None
        )
        assert high_priority is not None, "Должен быть слот с приоритетом 10"
        assert high_priority.slot_id == str(slot1.id), "Высокий приоритет должен быть у первого слота"
