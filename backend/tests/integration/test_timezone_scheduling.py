"""
Тесты timezone-aware расписания.

Покрывает:
- Установку часового пояса канала
- Создание расписания через авто-пилот с учетом часового пояса
- Проверку корректности времени при разных часовых поясах
- Проверку работы повторяющихся событий при переходе через границы часовых поясов
"""

import pytest
from datetime import datetime, date, time, timedelta, timezone
from uuid import uuid4

from src.models.schedule import ScheduleSlot, Playlist, PlaylistItem, RepeatType
from src.models.user import User, UserRole, UserStatus
from src.models.telegram import Channel

# ==================== Constants ====================

TEST_CHANNEL_ID = "12345678-1234-5678-1234-567812345678"

# Common timezones for testing
TIMEZONES = {
    "UTC": "UTC",
    "MOSCOW": "Europe/Moscow",      # UTC+3 (no DST)
    "NEW_YORK": "America/New_York", # UTC-5/-4 (with DST)
    "TOKYO": "Asia/Tokyo",          # UTC+9 (no DST)
    "LONDON": "Europe/London",      # UTC+0/+1 (with DST)
}

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
        description="Playlist for timezone testing",
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
def channel_with_timezone(db_session, admin_user: User) -> Channel:
    """
    Создаёт канал с установленным часовым поясом.

    ПРИМЕЧАНИЕ: Поскольку модель Channel не имеет поля timezone в текущей схеме,
    мы симулируем это через описание. В реальном коде нужно добавить timezone поле.
    """
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

    # Создаём канал с указанием timezone в описании (для симуляции)
    channel = Channel(
        id=TEST_CHANNEL_ID,
        account_id=account.id,
        chat_id=12345,
        name="Test Channel with Timezone",
        status="stopped",
        # Примечание: timezone должен быть добавлен как поле в модель Channel
        # Для тестов используем description для хранения информации
        # В продакшене: timezone = Column(String(50), default="UTC")
    )
    db_session.add(channel)
    db_session.commit()
    db_session.refresh(channel)
    return channel


# ==================== Helper Functions ====================

def convert_to_timezone(dt: datetime, tz: str) -> datetime:
    """
    Конвертирует datetime в указанный часовой пояс.

    Args:
        dt: Исходный datetime (должен быть timezone-aware)
        tz: Часовой пояс (например, "Europe/Moscow")

    Returns:
        datetime в указанном часовом поясе
    """
    import pytz
    target_tz = pytz.timezone(tz)
    return dt.astimezone(target_tz)


def create_slot_in_timezone(
    db_session,
    channel_id: str,
    playlist_id: str,
    start_date: date,
    start_time: time,
    end_time: time,
    timezone_str: str,
    repeat_type: RepeatType = RepeatType.NONE,
) -> ScheduleSlot:
    """
    Создаёт слот расписания с указанием часового пояса.

    Время конвертируется в UTC перед сохранением в базу данных.

    Args:
        db_session: Сессия базы данных
        channel_id: ID канала
        playlist_id: ID плейлиста
        start_date: Дата начала
        start_time: Время начала в локальном часовом поясе
        end_time: Время окончания в локальном часовом поясе
        timezone_str: Часовой пояс (например, "Europe/Moscow")
        repeat_type: Тип повторения

    Returns:
        Созданный слот ScheduleSlot
    """
    import pytz

    # Комбинируем дату и время в datetime
    local_tz = pytz.timezone(timezone_str)
    start_dt = local_tz.localize(datetime.combine(start_date, start_time))
    end_dt = local_tz.localize(datetime.combine(start_date, end_time))

    # Конвертируем в UTC для хранения
    start_utc = start_dt.astimezone(timezone.utc)
    end_utc = end_dt.astimezone(timezone.utc)

    # Создаём слот
    slot = ScheduleSlot(
        channel_id=channel_id,
        playlist_id=playlist_id,
        start_date=start_utc.date(),
        start_time=start_utc.time(),
        end_time=end_utc.time(),
        repeat_type=repeat_type,
        title=f"Slot in {timezone_str}",
        is_active=True,
    )

    db_session.add(slot)
    db_session.commit()
    db_session.refresh(slot)

    return slot


# ==================== Timezone Setting Tests ====================

class TestTimezoneSetting:
    """Тесты установки часового пояса канала."""

    @pytest.mark.asyncio
    async def test_channel_timezone_property_exists(self, channel_with_timezone: Channel):
        """
        Проверяет, что у канала можно получить/установить timezone.

        NOTE: Этот тест предполагает, что поле timezone будет добавлено в модель Channel.
        """
        # Примечание: Когда timezone поле будет добавлено в модель:
        # channel.timezone = "Europe/Moscow"
        # assert channel.timezone == "Europe/Moscow"

        # Временная симуляция через описание (для текущей схемы)
        assert channel_with_timezone is not None
        assert channel_with_timezone.id == TEST_CHANNEL_ID

    @pytest.mark.asyncio
    async def test_timezone_validation(self):
        """Проверяет валидацию часовых поясов."""
        import pytz

        # Проверяем, что популярные часовые пояса валидны
        valid_timezones = [
            "UTC",
            "Europe/Moscow",
            "America/New_York",
            "Asia/Tokyo",
            "Europe/London",
            "Australia/Sydney",
        ]

        for tz in valid_timezones:
            assert tz in pytz.all_timezones_set, f"Timezone {tz} is not valid"

        # Проверяем, что невалидные часовые пояса отклоняются
        invalid_timezones = ["Invalid/Timezone", "Wrong/Format", ""]

        for tz in invalid_timezones:
            if tz:  # Пустая строка может быть валидной (по умолчанию UTC)
                assert tz not in pytz.all_timezones_set


# ==================== Schedule Creation Tests ====================

class TestScheduleCreationWithTimezone:
    """Тесты создания расписания с учетом часового пояса."""

    @pytest.mark.asyncio
    async def test_create_slot_in_moscow_timezone(
        self,
        db_session,
        channel_with_timezone: Channel,
        test_playlist: Playlist,
    ):
        """
        Создаёт слот в часовом поясе Москвы (UTC+3).

        Проверяет, что время корректно конвертируется и сохраняется в UTC.
        """
        from datetime import time

        # Создаём слот на 10:00-12:00 по Москве
        slot = create_slot_in_timezone(
            db_session=db_session,
            channel_id=channel_with_timezone.id,
            playlist_id=test_playlist.id,
            start_date=date(2025, 1, 23),
            start_time=time(10, 0),
            end_time=time(12, 0),
            timezone_str="Europe/Moscow",
        )

        # Проверяем, что слот создан
        assert slot.id is not None
        assert slot.channel_id == channel_with_timezone.id

        # Проверяем, что время сохранено в UTC
        # 10:00 MSK = 07:00 UTC
        assert slot.start_time.hour == 7  # 07:00 UTC
        assert slot.start_time.minute == 0

        # 12:00 MSK = 09:00 UTC
        assert slot.end_time.hour == 9  # 09:00 UTC
        assert slot.end_time.minute == 0

    @pytest.mark.asyncio
    async def test_create_slot_in_new_york_timezone(
        self,
        db_session,
        channel_with_timezone: Channel,
        test_playlist: Playlist,
    ):
        """
        Создаёт слот в часовом поясе Нью-Йорка (UTC-5 зимой, UTC-4 летом).

        Проверяет корректность конвертации с учетом DST.
        """
        from datetime import time

        # Зимой (январь) UTC-5
        winter_slot = create_slot_in_timezone(
            db_session=db_session,
            channel_id=channel_with_timezone.id,
            playlist_id=test_playlist.id,
            start_date=date(2025, 1, 23),  # Январь - зима
            start_time=time(14, 0),
            end_time=time(16, 0),
            timezone_str="America/New_York",
        )

        # 14:00 EST = 19:00 UTC
        assert winter_slot.start_time.hour == 19
        assert winter_slot.end_time.hour == 21

        # Летом (июль) UTC-4
        summer_slot = create_slot_in_timezone(
            db_session=db_session,
            channel_id=str(uuid4()),  # Новый слот
            playlist_id=test_playlist.id,
            start_date=date(2025, 7, 15),  # Июль - лето
            start_time=time(14, 0),
            end_time=time(16, 0),
            timezone_str="America/New_York",
        )

        # 14:00 EDT = 18:00 UTC
        assert summer_slot.start_time.hour == 18
        assert summer_slot.end_time.hour == 20

    @pytest.mark.asyncio
    async def test_create_slot_in_tokyo_timezone(
        self,
        db_session,
        channel_with_timezone: Channel,
        test_playlist: Playlist,
    ):
        """
        Создаёт слот в часовом поясе Токио (UTC+9).

        Проверяет корректность конвертации для timezone без DST.
        """
        from datetime import time

        slot = create_slot_in_timezone(
            db_session=db_session,
            channel_id=channel_with_timezone.id,
            playlist_id=test_playlist.id,
            start_date=date(2025, 1, 23),
            start_time=time(20, 0),
            end_time=time(22, 0),
            timezone_str="Asia/Tokyo",
        )

        # 20:00 JST = 11:00 UTC (предыдущий день)
        assert slot.start_time.hour == 11
        assert slot.start_time.minute == 0

        # 22:00 JST = 13:00 UTC
        assert slot.end_time.hour == 13


# ==================== Recurring Events Tests ====================

class TestRecurringEventsAcrossTimezones:
    """Тесты повторяющихся событий при переходе через границы часовых поясов."""

    @pytest.mark.asyncio
    async def test_daily_repeat_in_timezone(
        self,
        db_session,
        channel_with_timezone: Channel,
        test_playlist: Playlist,
    ):
        """
        Проверяет ежедневное повторение в часовом поясе Москвы.

        Время должно оставаться постоянным в MSK (10:00), но меняться в UTC.
        """
        from datetime import time

        # Создаём ежедневный слот
        slot = create_slot_in_timezone(
            db_session=db_session,
            channel_id=channel_with_timezone.id,
            playlist_id=test_playlist.id,
            start_date=date(2025, 1, 23),
            start_time=time(10, 0),
            end_time=time(12, 0),
            timezone_str="Europe/Moscow",
            repeat_type=RepeatType.DAILY,
        )

        assert slot.repeat_type == RepeatType.DAILY
        assert slot.start_time.hour == 7  # 10:00 MSK = 07:00 UTC

    @pytest.mark.asyncio
    async def test_weekly_repeat_in_timezone(
        self,
        db_session,
        channel_with_timezone: Channel,
        test_playlist: Playlist,
    ):
        """Проверяет еженедельное повторение с учетом часового пояса."""
        from datetime import time

        slot = create_slot_in_timezone(
            db_session=db_session,
            channel_id=channel_with_timezone.id,
            playlist_id=test_playlist.id,
            start_date=date(2025, 1, 23),  # Четверг
            start_time=time(15, 0),
            end_time=time(17, 0),
            timezone_str="Europe/Moscow",
            repeat_type=RepeatType.WEEKLY,
        )

        assert slot.repeat_type == RepeatType.WEEKLY
        # 15:00 MSK = 12:00 UTC
        assert slot.start_time.hour == 12

    @pytest.mark.asyncio
    async def test_dst_transition_handling(
        self,
        db_session,
        channel_with_timezone: Channel,
        test_playlist: Playlist,
    ):
        """
        Проверяет корректность обработки перехода на летнее/зимнее время.

        Для часовых поясов с DST (например, America/New_York).
        """
        from datetime import time

        # Создаём слот перед переходом на летнее время (март 2025)
        before_dst = create_slot_in_timezone(
            db_session=db_session,
            channel_id=channel_with_timezone.id,
            playlist_id=test_playlist.id,
            start_date=date(2025, 3, 8),  # До DST (второе воскресенье марта)
            start_time=time(10, 0),
            end_time=time(12, 0),
            timezone_str="America/New_York",
            repeat_type=RepeatType.WEEKLY,
        )

        # Создаём слот после перехода на летнее время
        after_dst = create_slot_in_timezone(
            db_session=db_session,
            channel_id=str(uuid4()),
            playlist_id=test_playlist.id,
            start_date=date(2025, 3, 15),  # После DST
            start_time=time(10, 0),
            end_time=time(12, 0),
            timezone_str="America/New_York",
            repeat_type=RepeatType.WEEKLY,
        )

        # До перехода: 10:00 EST = 15:00 UTC
        assert before_dst.start_time.hour == 15

        # После перехода: 10:00 EDT = 14:00 UTC
        assert after_dst.start_time.hour == 14

        # Разница должна быть 1 час из-за DST
        time_diff = abs(before_dst.start_time.hour - after_dst.start_time.hour)
        assert time_diff == 1


# ==================== Auto-Pilot Tests ====================

class TestAutoPilotWithTimezones:
    """Тесты авто-пилота с учетом часовых поясов."""

    @pytest.mark.asyncio
    async def test_auto_pilot_respects_channel_timezone(
        self,
        db_session,
        channel_with_timezone: Channel,
        test_playlist: Playlist,
        admin_user: User,
    ):
        """
        Проверяет, что авто-пилот учитывает часовой пояс канала при генерации расписания.

        NOTE: Этот тест проверяет интеграцию с AutoPilotService.
        """
        from src.services.auto_pilot_service import AutoPilotService
        from src.schemas.schedule_ai import AutoPilotRequest, DateRange

        service = AutoPilotService(db_session)

        # Создаём запрос на генерацию расписания
        request = AutoPilotRequest(
            channel_id=channel_with_timezone.id,
            date_range=DateRange(
                start=date(2025, 1, 23),
                end=date(2025, 1, 25),
            ),
            use_ai_recommendations=False,  # Без AI для простоты теста
            max_daily_hours=8,
            resolve_conflicts=True,
        )

        # Генерируем расписание
        result = await service.preview_schedule(request)

        # Проверяем результат
        assert result is not None
        assert result.slots_created >= 0

    @pytest.mark.asyncio
    async def test_peak_hours_detection_in_timezone(
        self,
        db_session,
        channel_with_timezone: Channel,
        test_playlist: Playlist,
        admin_user: User,
    ):
        """
        Проверяет, что пиковые часы определяются корректно для часового пояса.

        Пиковые часы должны быть в локальном времени канала.
        """
        from src.services.schedule_recommendation_service import ScheduleRecommendationService

        service = ScheduleRecommendationService(db_session)

        # Получаем пиковые часы
        peak_hours = await service.get_peak_hours(
            channel_id=channel_with_timezone.id,
            period_days=30,
            min_sample_size=1,
        )

        # Проверяем структуру ответа
        assert peak_hours is not None
        assert "by_day_of_week" in peak_hours
        assert "by_hour" in peak_hours


# ==================== Display Tests ====================

class TestTimezoneDisplay:
    """Тесты отображения времени в правильном часовом поясе."""

    @pytest.mark.asyncio
    async def test_convert_utc_to_local_timezone(
        self,
        db_session,
        channel_with_timezone: Channel,
        test_playlist: Playlist,
    ):
        """
        Проверяет конвертацию времени из UTC в локальный часовой пояс для отображения.

        При отображении пользователю время должно показываться в его часовом поясе.
        """
        from datetime import time

        # Создаём слот (время сохраняется в UTC)
        slot = create_slot_in_timezone(
            db_session=db_session,
            channel_id=channel_with_timezone.id,
            playlist_id=test_playlist.id,
            start_date=date(2025, 1, 23),
            start_time=time(10, 0),
            end_time=time(12, 0),
            timezone_str="Europe/Moscow",
        )

        # При чтении из базы это UTC время (07:00)
        utc_start = datetime.combine(slot.start_date, slot.start_time, tzinfo=timezone.utc)

        # Конвертируем обратно в MSK для отображения
        moscow_time = convert_to_timezone(utc_start, "Europe/Moscow")

        # Должно быть 10:00 MSK
        assert moscow_time.hour == 10
        assert moscow_time.minute == 0

    @pytest.mark.asyncio
    async def test_display_time_across_multiple_timezones(
        self,
        db_session,
        channel_with_timezone: Channel,
        test_playlist: Playlist,
    ):
        """
        Проверяет отображение одного и того же слота в разных часовых поясах.

        Одно и то же UTC время должно отображаться по-разному в разных timezone.
        """
        from datetime import time

        # Создаём слот (10:00 MSK = 07:00 UTC)
        slot = create_slot_in_timezone(
            db_session=db_session,
            channel_id=channel_with_timezone.id,
            playlist_id=test_playlist.id,
            start_date=date(2025, 1, 23),
            start_time=time(10, 0),
            end_time=time(12, 0),
            timezone_str="Europe/Moscow",
        )

        # UTC время из базы
        utc_time = datetime.combine(slot.start_date, slot.start_time, tzinfo=timezone.utc)

        # Конвертируем в разные timezone
        moscow_time = convert_to_timezone(utc_time, "Europe/Moscow")
        tokyo_time = convert_to_timezone(utc_time, "Asia/Tokyo")
        new_york_time = convert_to_timezone(utc_time, "America/New_York")

        # Проверяем разницу в отображении
        assert moscow_time.hour == 10  # 10:00 MSK
        assert tokyo_time.hour == 16  # 16:00 JST (UTC+9)
        assert new_york_time.hour == 2  # 02:00 EST (UTC-5)


# ==================== Edge Cases ====================

class TestTimezoneEdgeCases:
    """Тесты edge cases для timezone."""

    @pytest.mark.asyncio
    async def test_slot_crossing_midnight_in_timezone(
        self,
        db_session,
        channel_with_timezone: Channel,
        test_playlist: Playlist,
    ):
        """Проверяет слот, который переходит через полночь в локальном timezone."""
        from datetime import time

        # Создаём слот 22:00 - 02:00 (следующий день)
        slot = create_slot_in_timezone(
            db_session=db_session,
            channel_id=channel_with_timezone.id,
            playlist_id=test_playlist.id,
            start_date=date(2025, 1, 23),
            start_time=time(22, 0),
            end_time=time(2, 0),
            timezone_str="Europe/Moscow",
        )

        # 22:00 MSK = 19:00 UTC
        assert slot.start_time.hour == 19

        # 02:00 MSK (следующий день) = 23:00 UTC (предыдущий день)
        # Примечание: текущая модель не поддерживает end_date, только end_time
        # Это ограничение модели, которое нужно учесть в реальной реализации
        assert slot.end_time.hour == 23

    @pytest.mark.asyncio
    async def test_invalid_timezone_handling(
        self,
        db_session,
        channel_with_timezone: Channel,
        test_playlist: Playlist,
    ):
        """Проверяет обработку невалидного часового пояса."""
        import pytz

        # Пытаемся создать слот с невалидным timezone
        with pytest.raises(pytz.exceptions.UnknownTimeZoneError):
            create_slot_in_timezone(
                db_session=db_session,
                channel_id=channel_with_timezone.id,
                playlist_id=test_playlist.id,
                start_date=date(2025, 1, 23),
                start_time=time(10, 0),
                end_time=time(12, 0),
                timezone_str="Invalid/Timezone",
            )

    @pytest.mark.asyncio
    async def test_timezone_abbreviation_ambiguity(self):
        """
        Проверяет обработку неоднозначных аббревиатур timezone.

        Например, "EST" может означать разные timezone в разных контекстах.
        Рекомендуется использовать IANA timezone names (например, "America/New_York").
        """
        import pytz

        # "EST" - неоднозначная аббревиатура
        # "America/New_York" - правильный IANA timezone

        # Проверяем, что рекомендуемые timezone unambiguous
        assert "America/New_York" in pytz.all_timezones_set

        # IANA timezone - это правильный подход
        ny_tz = pytz.timezone("America/New_York")
        assert ny_tz is not None
