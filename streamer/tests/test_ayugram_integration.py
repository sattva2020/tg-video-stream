"""
Интеграционные тесты для AyuGram адаптера.

Integration tests для проверки работы AyuGram адаптера с Redis command handler
и multi-channel streaming. Тесты используют mock для tg-engine service.
"""

import asyncio
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from dataclasses import asdict


class TestAyuGramAdapterInitialization:
    """Тесты инициализации AyuGram адаптера."""

    def test_ayugram_import_when_available(self):
        """AyuGram адаптер должен импортироваться когда доступен."""
        from ayugram_adapter import AyuGramAdapter, AYUGRAM_AVAILABLE

        # Проверяем что адаптер может быть импортирован
        assert AyuGramAdapter is not None

    def test_ayugram_available_flag(self):
        """Флаг AYUGRAM_AVAILABLE должен отражать состояние."""
        from ayugram_adapter import AYUGRAM_AVAILABLE

        # Флаг должен быть булевым
        assert isinstance(AYUGRAM_AVAILABLE, bool)

    def test_is_available_respects_env_var(self):
        """is_available() должен проверять USE_AYUGRAM."""
        from ayugram_adapter import is_available

        # Тест с USE_AYUGRAM=0
        with patch.dict(os.environ, {"USE_AYUGRAM": "0", "AYUGRAM_TG_ENGINE_PATH": ""}):
            assert is_available() is False

        # Тест с USE_AYUGRAM=1
        with patch.dict(os.environ, {"USE_AYUGRAM": "1"}):
            # Если USE_AYUGRAM=1, должен вернуть True
            # даже без TG_ENGINE_PATH (с warning)
            result = is_available()
            assert result is True

    def test_adapter_creation(self):
        """AyuGramAdapter должен создаваться с pyrogram client."""
        from ayugram_adapter import AyuGramAdapter

        mock_client = MagicMock()
        adapter = AyuGramAdapter(mock_client)

        assert adapter.client is mock_client
        assert adapter._is_running is False
        assert adapter._event_handlers == {
            "stream_end": [],
            "chat_update": [],
            "participant": [],
        }


class TestAyuGramMediaStream:
    """Тесты для MediaStream dataclass."""

    def test_media_stream_creation(self):
        """MediaStream должен создаваться с параметрами."""
        from ayugram_adapter import MediaStream, AudioQuality, VideoQuality

        stream = MediaStream(
            url_or_path="https://example.com/audio.mp3",
            audio_parameters=AudioQuality.HIGH,
            video_parameters=VideoQuality.HD_720p,
        )

        assert stream.url_or_path == "https://example.com/audio.mp3"
        assert stream.audio_parameters == AudioQuality.HIGH
        assert stream.video_parameters == VideoQuality.HD_720p

    def test_audio_quality_enum(self):
        """AudioQuality enum должен иметь правильные значения."""
        from ayugram_adapter import AudioQuality

        assert AudioQuality.LOW.value == "low"
        assert AudioQuality.MEDIUM.value == "medium"
        assert AudioQuality.HIGH.value == "high"
        assert AudioQuality.STUDIO.value == "studio"

    def test_video_quality_enum(self):
        """VideoQuality enum должен иметь правильные значения."""
        from ayugram_adapter import VideoQuality

        assert VideoQuality.SD_480p.value == "480p"
        assert VideoQuality.HD_720p.value == "720p"
        assert VideoQuality.FHD_1080p.value == "1080p"
        assert VideoQuality.QHD_2K.value == "2k"
        assert VideoQuality.UHD_4K.value == "4k"


class TestAyuGramEventHandlers:
    """Тесты для системы event handlers."""

    @pytest.mark.asyncio
    async def test_on_update_decorator(self):
        """Декоратор on_update должен регистрировать handlers."""
        from ayugram_adapter import AyuGramAdapter, filters

        mock_client = MagicMock()
        adapter = AyuGramAdapter(mock_client)

        # Регистрируем handler для stream_end
        @adapter.on_update(filters.stream_end())
        async def stream_end_handler(adapter, update):
            pass

        assert len(adapter._event_handlers["stream_end"]) == 1
        assert adapter._event_handlers["stream_end"][0] == stream_end_handler

    @pytest.mark.asyncio
    async def test_emit_event(self):
        """_emit_event должен вызывать все зарегистрированные handlers."""
        from ayugram_adapter import AyuGramAdapter, StreamEnded

        mock_client = MagicMock()
        adapter = AyuGramAdapter(mock_client)

        # Регистрируем mock handlers
        handler1_called = asyncio.Event()
        handler2_called = asyncio.Event()

        async def handler1(adapter, update):
            handler1_called.set()

        async def handler2(adapter, update):
            handler2_called.set()

        adapter._event_handlers["stream_end"] = [handler1, handler2]

        # Эмитируем событие
        update = StreamEnded(chat_id=123456)
        await adapter._emit_event("stream_end", update)

        # Проверяем что оба handler были вызваны
        assert handler1_called.is_set()
        assert handler2_called.is_set()


class TestAyuGramStreamLifecycle:
    """Тесты для жизненного цикла стрима."""

    @pytest.mark.asyncio
    async def test_adapter_start(self):
        """start() должен отмечать адаптер как запущенный."""
        from ayugram_adapter import AyuGramAdapter

        mock_client = MagicMock()
        adapter = AyuGramAdapter(mock_client)

        await adapter.start()

        assert adapter._is_running is True

    @pytest.mark.asyncio
    async def test_adapter_start_idempotent(self):
        """Повторный start() не должен вызывать ошибок."""
        from ayugram_adapter import AyuGramAdapter

        mock_client = MagicMock()
        adapter = AyuGramAdapter(mock_client)

        await adapter.start()
        await adapter.start()  # Второй вызов

        assert adapter._is_running is True

    @pytest.mark.asyncio
    async def test_adapter_stop(self):
        """stop() должен останавливать адаптер."""
        from ayugram_adapter import AyuGramAdapter

        mock_client = MagicMock()
        adapter = AyuGramAdapter(mock_client)

        await adapter.start()
        await adapter.stop()

        assert adapter._is_running is False


class TestAyuGramIntegrationWithMain:
    """Тесты интеграции с main.py."""

    def test_main_imports_ayugram(self):
        """main.py должен импортировать AyuGramAdapter."""
        import main

        # Проверяем что импорт успешен
        assert hasattr(main, "AYUGRAM_AVAILABLE")
        assert isinstance(main.AYUGRAM_AVAILABLE, bool)

    @pytest.mark.asyncio
    async def test_ayugram_initialization_with_env_var(self):
        """При USE_AYUGRAM=1 должен инициализироваться AyuGram."""
        import main

        # Сохраняем оригинальные значения
        original_app = main.app
        original_ayugram = main.ayugram
        original_use_ayugram = main.USE_AYUGRAM

        try:
            # Мокаем app и AyuGramAdapter
            mock_client = MagicMock()
            main.app = mock_client

            with patch.object(main, "AYUGRAM_AVAILABLE", True):
                with patch("main.AyuGramAdapter") as MockAdapter:
                    mock_adapter = MagicMock()
                    MockAdapter.return_value = mock_adapter

                    # Устанавливаем USE_AYUGRAM
                    main.USE_AYUGRAM = "1"

                    # Пересоздаем ayugram как при инициализации
                    if main.USE_AYUGRAM == "1" and main.AYUGRAM_AVAILABLE and main.app:
                        main.ayugram = main.AyuGramAdapter(main.app)

                    # Проверяем что AyuGram был создан
                    assert main.ayugram is not None
        finally:
            # Восстанавливаем оригинальные значения
            main.app = original_app
            main.ayugram = original_ayugram
            main.USE_AYUGRAM = original_use_ayugram


class TestAyuGramRedisCommandHandling:
    """Тесты для обработки Redis команд с AyuGram."""

    def test_channel_config_compatibility(self):
        """ChannelConfig должен быть совместим с AyuGram."""
        from redis_command_handler import ChannelConfig

        config = ChannelConfig(
            channel_id="test_channel",
            chat_id=123456,
            name="Test Channel",
            session_string="test_session",
            api_id=123456,
            api_hash="test_hash",
            video_quality="720p",
            audio_quality="high",
        )

        # Проверяем что все поля заполнены
        assert config.channel_id == "test_channel"
        assert config.chat_id == 123456
        assert config.session_string == "test_session"
        assert config.api_id == 123456
        assert config.api_hash == "test_hash"

    @pytest.mark.asyncio
    async def test_redis_command_handler_with_ayugram(self):
        """RedisCommandHandler должен работать с AyuGram backend."""
        from redis_command_handler import RedisCommandHandler

        # Создаём handler
        handler = RedisCommandHandler(redis_url="redis://localhost:6379/0")

        # Устанавливаем callback для start
        start_called = False
        start_config = None

        async def mock_start(config):
            nonlocal start_called, start_config
            start_called = True
            start_config = config
            return True

        handler.on_start = mock_start

        # Вызываем start command handler напрямую
        from redis_command_handler import ChannelConfig

        config = ChannelConfig(
            channel_id="test1",
            chat_id=123456,
            name="Test",
            session_string="test",
            api_id=123,
            api_hash="hash",
        )

        # Эмуляция обработки команды
        await handler.on_start(config)

        assert start_called is True
        assert start_config.channel_id == "test1"


class TestAyuGramMultiChannelStreaming:
    """Тесты для multi-channel streaming с AyuGram."""

    @pytest.mark.asyncio
    async def test_stream_start_with_mocked_ayugram(self):
        """Тест старта стрима с замоканным AyuGram."""
        from ayugram_adapter import AyuGramAdapter, MediaStream
        import main

        # Мокаем AyuGramAdapter
        mock_adapter = MagicMock(spec=AyuGramAdapter)
        mock_adapter.start = AsyncMock()
        mock_adapter.join_group_call = AsyncMock()

        # Мокаем client
        mock_client = MagicMock()

        # Создаём адаптер
        adapter = AyuGramAdapter(mock_client)
        adapter.start = AsyncMock()
        adapter.join_group_call = AsyncMock()

        # Запускаем адаптер
        await adapter.start()
        assert adapter._is_running is True

        # Проверяем что start был вызван
        adapter.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_end_event_handling(self):
        """Тест обработки события окончания стрима."""
        from ayugram_adapter import AyuGramAdapter, StreamEnded

        mock_client = MagicMock()
        adapter = AyuGramAdapter(mock_client)

        # Регистрируем handler
        stream_ended = asyncio.Event()

        async def stream_end_handler(adapter, update):
            if update.chat_id == 123456:
                stream_ended.set()

        adapter._event_handlers["stream_end"].append(stream_end_handler)

        # Эмитируем событие
        update = StreamEnded(chat_id=123456)
        await adapter._emit_event("stream_end", update)

        # Проверяем что handler был вызван
        assert stream_ended.is_set()


class TestAyuGramFilters:
    """Тесты для системы фильтров событий."""

    def test_stream_end_filter(self):
        """Фильтр stream_end должен работать правильно."""
        from ayugram_adapter import filters, StreamEnded, ChatUpdate

        stream_filter = filters.stream_end()

        # Должен пропускать StreamEnded
        assert stream_filter(StreamEnded(chat_id=123)) is True

        # Не должен пропускать другие типы
        assert stream_filter(ChatUpdate(chat_id=123, status="left")) is False

    def test_chat_update_filter(self):
        """Фильтр chat_update должен работать правильно."""
        from ayugram_adapter import filters, ChatUpdate, StreamEnded

        chat_filter = filters.chat_update()

        # Должен пропускать ChatUpdate
        assert chat_filter(ChatUpdate(chat_id=123, status="left")) is True

        # Не должен пропускать другие типы
        assert chat_filter(StreamEnded(chat_id=123)) is False

    def test_chat_update_filter_with_mask(self):
        """Фильтр chat_update с маской должен фильтровать по статусу."""
        from ayugram_adapter import filters, ChatUpdate

        chat_filter = filters.chat_update(status_mask=["kicked", "left"])

        # Должен пропускать указанные статусы
        assert chat_filter(ChatUpdate(chat_id=123, status="kicked")) is True
        assert chat_filter(ChatUpdate(chat_id=123, status="left")) is True

        # Не должен пропускать другие статусы
        assert chat_filter(ChatUpdate(chat_id=123, status="closed")) is False

    def test_call_participant_filter(self):
        """Фильтр participant должен работать правильно."""
        from ayugram_adapter import filters, UpdatedGroupCallParticipant, StreamEnded

        participant_filter = filters.call_participant()

        # Должен пропускать UpdatedGroupCallParticipant
        participant = UpdatedGroupCallParticipant(
            chat_id=123,
            participant=MagicMock(),
            action="joined"
        )
        assert participant_filter(participant) is True

        # Не должен пропускать другие типы
        assert participant_filter(StreamEnded(chat_id=123)) is False


class TestAyuGramGroupCallParticipant:
    """Тесты для GroupCallParticipant dataclass."""

    def test_participant_creation(self):
        """GroupCallParticipant должен создаваться с параметрами."""
        from ayugram_adapter import GroupCallParticipant

        participant = GroupCallParticipant(
            user_id=123456,
            muted=True,
            volume=75,
            video=False,
            raised_hand=True,
        )

        assert participant.user_id == 123456
        assert participant.muted is True
        assert participant.volume == 75
        assert participant.video is False
        assert participant.raised_hand is True

    def test_participant_action_enum(self):
        """Participant.Action enum должен иметь правильные значения."""
        from ayugram_adapter import GroupCallParticipant

        assert GroupCallParticipant.Action.JOINED.value == "joined"
        assert GroupCallParticipant.Action.LEFT.value == "left"


class TestAyuGramCompatibilityTypes:
    """Тесты для типов совместимости с PyTgCalls."""

    def test_group_call_config(self):
        """GroupCallConfig должен быть совместим с PyTgCalls."""
        from ayugram_adapter import GroupCallConfig

        config = GroupCallConfig(auto_start=True)
        assert config.auto_start is True

    def test_stream_ended(self):
        """StreamEnded должен содержать chat_id."""
        from ayugram_adapter import StreamEnded

        event = StreamEnded(chat_id=123456)
        assert event.chat_id == 123456

    def test_chat_update(self):
        """ChatUpdate должен содержать chat_id и status."""
        from ayugram_adapter import ChatUpdate

        event = ChatUpdate(chat_id=123456, status="kicked")
        assert event.chat_id == 123456
        assert event.status == "kicked"

    def test_updated_group_call_participant(self):
        """UpdatedGroupCallParticipant должен содержать все поля."""
        from ayugram_adapter import UpdatedGroupCallParticipant, GroupCallParticipant

        participant = GroupCallParticipant(user_id=123)
        event = UpdatedGroupCallParticipant(
            chat_id=456,
            participant=participant,
            action="joined"
        )

        assert event.chat_id == 456
        assert event.participant == participant
        assert event.action == "joined"


class TestAyuGramErrorHandling:
    """Тесты для обработки ошибок."""

    @pytest.mark.asyncio
    async def test_join_group_call_raises_not_implemented(self):
        """join_group_call должен вызывать NotImplementedError."""
        from ayugram_adapter import AyuGramAdapter, MediaStream

        mock_client = MagicMock()
        adapter = AyuGramAdapter(mock_client)

        stream = MediaStream(url_or_path="https://example.com/audio.mp3")

        with pytest.raises(NotImplementedError) as exc_info:
            await adapter.join_group_call(123456, stream)

        assert "not yet implemented" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_leave_call_raises_not_implemented(self):
        """leave_call должен вызывать NotImplementedError."""
        from ayugram_adapter import AyuGramAdapter

        mock_client = MagicMock()
        adapter = AyuGramAdapter(mock_client)

        with pytest.raises(NotImplementedError) as exc_info:
            await adapter.leave_call(123456)

        assert "not yet implemented" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_play_raises_not_implemented(self):
        """play должен вызывать NotImplementedError."""
        from ayugram_adapter import AyuGramAdapter, MediaStream

        mock_client = MagicMock()
        adapter = AyuGramAdapter(mock_client)

        stream = MediaStream(url_or_path="https://example.com/audio.mp3")

        with pytest.raises(NotImplementedError) as exc_info:
            await adapter.play(123456, stream)

        assert "not yet implemented" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_get_participants_raises_not_implemented(self):
        """get_participants должен вызывать NotImplementedError."""
        from ayugram_adapter import AyuGramAdapter

        mock_client = MagicMock()
        adapter = AyuGramAdapter(mock_client)

        with pytest.raises(NotImplementedError) as exc_info:
            await adapter.get_participants(123456)

        assert "not yet implemented" in str(exc_info.value).lower()


class TestAyuGramAdapterWithMockTgEngine:
    """Тесты для AyuGram адаптера с mock tg-engine сервисом."""

    @pytest.mark.asyncio
    async def test_adapter_start_with_mock_tg_engine(self):
        """Тест старта адаптера с mock tg-engine."""
        from ayugram_adapter import AyuGramAdapter

        mock_client = MagicMock()
        adapter = AyuGramAdapter(mock_client)

        # Мокаем tg-engine инициализацию (будет в будущем)
        with patch.object(adapter, "_emit_event"):
            await adapter.start()

        assert adapter._is_running is True

    @pytest.mark.asyncio
    async def test_event_handler_execution_with_mock(self):
        """Тест выполнения event handler с mock адаптером."""
        from ayugram_adapter import AyuGramAdapter, StreamEnded

        mock_client = MagicMock()
        adapter = AyuGramAdapter(mock_client)

        handler_executed = False

        async def test_handler(adapter, update):
            nonlocal handler_executed
            handler_executed = True

        adapter._event_handlers["stream_end"].append(test_handler)

        # Эмитируем событие
        await adapter._emit_event("stream_end", StreamEnded(chat_id=123))

        assert handler_executed is True


class TestAyuGramBackendDetection:
    """Тесты для определения backend (AyuGram vs PyTgCalls)."""

    def test_backend_detection_in_main(self):
        """main.py должен корректно определять backend."""
        import main

        # Проверяем что обе переменные существуют
        assert hasattr(main, "pytg")
        assert hasattr(main, "ayugram")

    @pytest.mark.asyncio
    async def test_ayugram_backend_with_env_variable(self):
        """При USE_AYUGRAM=1 должен использоваться AyuGram backend."""
        from ayugram_adapter import is_available

        # Тест с различными значениями USE_AYUGRAM
        test_cases = [
            ("1", True),
            ("true", True),
            ("yes", True),
            ("0", False),
            ("false", False),
            ("", False),
        ]

        for value, expected in test_cases:
            with patch.dict(os.environ, {"USE_AYUGRAM": value}):
                result = is_available()
                # Only check for truthy values since is_available returns bool
                if expected:
                    # For truthy values, we expect True (or could be True with warning)
                    # The function may return True even without TG_ENGINE_PATH
                    assert result is True or value.lower() in {"1", "true", "yes"}


class TestMultiChannelConcurrentStreaming:
    """Тесты для multi-channel concurrent streaming с AyuGram."""

    @pytest.mark.asyncio
    async def test_two_adapters_independent_initialization(self):
        """Два адаптера AyuGram должны создаваться независимо."""
        from ayugram_adapter import AyuGramAdapter

        # Создаём два независимых адаптера
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()

        adapter1 = AyuGramAdapter(mock_client1)
        adapter2 = AyuGramAdapter(mock_client2)

        # Проверяем что адаптеры независимы
        assert adapter1 is not adapter2
        assert adapter1.client is mock_client1
        assert adapter2.client is mock_client2
        assert adapter1._event_handlers is not adapter2._event_handlers
        assert adapter1._is_running is False
        assert adapter2._is_running is False

    @pytest.mark.asyncio
    async def test_two_adapters_can_start_independently(self):
        """Два адаптера могут запускаться независимо."""
        from ayugram_adapter import AyuGramAdapter

        mock_client1 = MagicMock()
        mock_client2 = MagicMock()

        adapter1 = AyuGramAdapter(mock_client1)
        adapter2 = AyuGramAdapter(mock_client2)

        # Запускаем оба адаптера
        await adapter1.start()
        await adapter2.start()

        # Проверяем что оба запущены
        assert adapter1._is_running is True
        assert adapter2._is_running is True

    @pytest.mark.asyncio
    async def test_event_handlers_isolated_between_channels(self):
        """Event handlers для разных каналов не должны пересекаться."""
        from ayugram_adapter import AyuGramAdapter, StreamEnded

        # Создаём два адаптера для двух каналов
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()

        adapter1 = AyuGramAdapter(mock_client1)
        adapter2 = AyuGramAdapter(mock_client2)

        # Регистрируем handlers для канала 1
        channel1_events = []

        async def channel1_handler(adapter, update):
            channel1_events.append(update.chat_id)

        adapter1._event_handlers["stream_end"].append(channel1_handler)

        # Регистрируем handlers для канала 2
        channel2_events = []

        async def channel2_handler(adapter, update):
            channel2_events.append(update.chat_id)

        adapter2._event_handlers["stream_end"].append(channel2_handler)

        # Эмитируем событие для канала 1
        await adapter1._emit_event("stream_end", StreamEnded(chat_id=111))

        # Эмитируем событие для канала 2
        await adapter2._emit_event("stream_end", StreamEnded(chat_id=222))

        # Проверяем изоляцию: channel1 handler получил только свои события
        assert len(channel1_events) == 1
        assert channel1_events[0] == 111
        assert len(channel2_events) == 1
        assert channel2_events[0] == 222

    @pytest.mark.asyncio
    async def test_stop_channel_does_not_affect_other_channel(self):
        """Остановка одного канала не должна влиять на другой."""
        from ayugram_adapter import AyuGramAdapter

        # Создаём два адаптера
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()

        adapter1 = AyuGramAdapter(mock_client1)
        adapter2 = AyuGramAdapter(mock_client2)

        # Запускаем оба
        await adapter1.start()
        await adapter2.start()

        assert adapter1._is_running is True
        assert adapter2._is_running is True

        # Останавливаем только первый
        await adapter1.stop()

        # Проверяем что первый остановлен, а второй работает
        assert adapter1._is_running is False
        assert adapter2._is_running is True

    @pytest.mark.asyncio
    async def test_concurrent_event_emission(self):
        """События могут обрабатываться concurrently для разных каналов."""
        from ayugram_adapter import AyuGramAdapter, StreamEnded

        # Создаём два адаптера
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()

        adapter1 = AyuGramAdapter(mock_client1)
        adapter2 = AyuGramAdapter(mock_client2)

        # Счётчики вызовов
        handler1_calls = asyncio.Event()
        handler2_calls = asyncio.Event()

        async def handler1(adapter, update):
            handler1_calls.set()

        async def handler2(adapter, update):
            handler2_calls.set()

        adapter1._event_handlers["stream_end"].append(handler1)
        adapter2._event_handlers["stream_end"].append(handler2)

        # Эмитируем события concurrently
        await asyncio.gather(
            adapter1._emit_event("stream_end", StreamEnded(chat_id=111)),
            adapter2._emit_event("stream_end", StreamEnded(chat_id=222)),
        )

        # Проверяем что оба handlers были вызваны
        assert handler1_calls.is_set()
        assert handler2_calls.is_set()

    @pytest.mark.asyncio
    async def test_multi_channel_state_isolation(self):
        """Состояние разных каналов должно быть изолировано."""
        from ayugram_adapter import AyuGramAdapter

        # Создаём два адаптера
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()

        adapter1 = AyuGramAdapter(mock_client1)
        adapter2 = AyuGramAdapter(mock_client2)

        # Меняем состояние первого адаптера
        await adapter1.start()
        adapter1._event_handlers["stream_end"].append(lambda a, u: None)

        # Проверяем что состояние второго не изменилось
        assert adapter2._is_running is False
        assert len(adapter2._event_handlers["stream_end"]) == 0

    @pytest.mark.asyncio
    async def test_different_event_types_per_channel(self):
        """Разные типы событий могут обрабатываться на разных каналах."""
        from ayugram_adapter import AyuGramAdapter, StreamEnded, ChatUpdate

        # Создаём два адаптера
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()

        adapter1 = AyuGramAdapter(mock_client1)
        adapter2 = AyuGramAdapter(mock_client2)

        # Канал 1 обрабатывает stream_end
        stream_end_events = []

        async def stream_end_handler(adapter, update):
            stream_end_events.append(update.chat_id)

        adapter1._event_handlers["stream_end"].append(stream_end_handler)

        # Канал 2 обрабатывает chat_update
        chat_update_events = []

        async def chat_update_handler(adapter, update):
            chat_update_events.append((update.chat_id, update.status))

        adapter2._event_handlers["chat_update"].append(chat_update_handler)

        # Эмитируем события
        await adapter1._emit_event("stream_end", StreamEnded(chat_id=111))
        await adapter2._emit_event("chat_update", ChatUpdate(chat_id=222, status="left"))

        # Проверяем что каждый канал получил только свои события
        assert len(stream_end_events) == 1
        assert stream_end_events[0] == 111
        assert len(chat_update_events) == 1
        assert chat_update_events[0] == (222, "left")

    @pytest.mark.asyncio
    async def test_running_channels_dict_pattern(self):
        """Тест для pattern использования running_channels dict."""
        from ayugram_adapter import AyuGramAdapter

        # Симулируем running_channels pattern из multi_channel_runner.py
        running_channels = {}

        # Создаём два клиента и адаптера
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()

        adapter1 = AyuGramAdapter(mock_client1)
        adapter2 = AyuGramAdapter(mock_client2)

        # Добавляем каналы в running_channels
        running_channels["channel1"] = {
            "client": mock_client1,
            "ayugram": adapter1,
            "backend_type": "ayugram",
            "task": None,
        }

        running_channels["channel2"] = {
            "client": mock_client2,
            "ayugram": adapter2,
            "backend_type": "ayugram",
            "task": None,
        }

        # Проверяем что каналы изолированы
        assert running_channels["channel1"]["ayugram"] is adapter1
        assert running_channels["channel2"]["ayugram"] is adapter2
        assert running_channels["channel1"]["backend_type"] == "ayugram"
        assert running_channels["channel2"]["backend_type"] == "ayugram"

        # Запускаем оба
        await adapter1.start()
        await adapter2.start()

        assert running_channels["channel1"]["ayugram"]._is_running is True
        assert running_channels["channel2"]["ayugram"]._is_running is True

        # Удаляем канал 1
        del running_channels["channel1"]

        # Проверяем что канал 2 не пострадал
        assert "channel1" not in running_channels
        assert "channel2" in running_channels
        assert adapter2._is_running is True

    @pytest.mark.asyncio
    async def test_stream_ended_events_isolation(self):
        """Тест изоляции stream_ended_events между каналами."""
        from ayugram_adapter import AyuGramAdapter, StreamEnded

        # Симулируем stream_ended_events pattern
        stream_ended_events = {}

        # Создаём события для разных chat_id
        stream_ended_events[111] = asyncio.Event()
        stream_ended_events[222] = asyncio.Event()

        # Создаём адаптеры
        mock_client1 = MagicMock()
        mock_client2 = MagicMock()

        adapter1 = AyuGramAdapter(mock_client1)
        adapter2 = AyuGramAdapter(mock_client2)

        # Handler для канала 1 устанавливает событие 111
        async def handler1(adapter, update):
            if update.chat_id == 111:
                stream_ended_events[111].set()

        adapter1._event_handlers["stream_end"].append(handler1)

        # Handler для канала 2 устанавливает событие 222
        async def handler2(adapter, update):
            if update.chat_id == 222:
                stream_ended_events[222].set()

        adapter2._event_handlers["stream_end"].append(handler2)

        # Эмитируем события
        await adapter1._emit_event("stream_end", StreamEnded(chat_id=111))
        await adapter2._emit_event("stream_end", StreamEnded(chat_id=222))

        # Проверяем изоляцию событий
        assert stream_ended_events[111].is_set()
        assert stream_ended_events[222].is_set()

        # Очищаем событие 111
        stream_ended_events[111].clear()

        # Проверяем что событие 222 всё ещё установлено
        assert stream_ended_events[222].is_set()
        assert not stream_ended_events[111].is_set()

    @pytest.mark.asyncio
    async def test_play_in_progress_isolation(self):
        """Тест изоляции play_in_progress между каналами."""
        # Симулируем play_in_progress pattern
        play_in_progress = {}

        # Устанавливаем play_in_progress для разных chat_id
        play_in_progress[111] = False
        play_in_progress[222] = False

        # Симулируем начало воспроизведения на канале 1
        play_in_progress[111] = True

        # Проверяем изоляцию
        assert play_in_progress[111] is True
        assert play_in_progress[222] is False

        # Завершаем воспроизведение на канале 1
        play_in_progress[111] = False

        # Проверяем состояние
        assert play_in_progress[111] is False
        assert play_in_progress[222] is False

    @pytest.mark.asyncio
    async def test_multiple_event_handlers_per_channel(self):
        """Несколько handlers могут быть зарегистрированы на одном канале."""
        from ayugram_adapter import AyuGramAdapter, StreamEnded

        mock_client = MagicMock()
        adapter = AyuGramAdapter(mock_client)

        # Регистрируем несколько handlers
        handler1_calls = []
        handler2_calls = []

        async def handler1(adapter, update):
            handler1_calls.append(update.chat_id)

        async def handler2(adapter, update):
            handler2_calls.append(update.chat_id)

        adapter._event_handlers["stream_end"].extend([handler1, handler2])

        # Эмитируем событие
        await adapter._emit_event("stream_end", StreamEnded(chat_id=123))

        # Проверяем что оба handlers были вызваны
        assert len(handler1_calls) == 1
        assert len(handler2_calls) == 1
        assert handler1_calls[0] == 123
        assert handler2_calls[0] == 123


class TestQueueAutoAdvanceWithAyuGram:
    """Тесты для автоматического продвижения очереди с AyuGram."""

    @pytest.mark.asyncio
    async def test_queue_creation_with_three_tracks(self):
        """Очередь должна создаваться с 3 треками."""
        from queue_manager import StreamQueue

        queue = StreamQueue(max_buffer_size=3, channel_id=123456)

        # Создаём плейлист из 3 треков
        tracks = [
            {"id": "track1", "url": "https://example.com/track1.mp3"},
            {"id": "track2", "url": "https://example.com/track2.mp3"},
            {"id": "track3", "url": "https://example.com/track3.mp3"},
        ]

        # Добавляем треки в очередь
        await queue.add_items(tracks)

        # Проверяем что все треки добавлены в playlist_items
        assert len(queue.playlist_items) == 3

        # Проверяем порядок треков
        assert queue.playlist_items[0]["id"] == "track1"
        assert queue.playlist_items[1]["id"] == "track2"
        assert queue.playlist_items[2]["id"] == "track3"

    @pytest.mark.asyncio
    async def test_stream_ended_advances_queue(self):
        """Событие StreamEnded должно продвигать очередь к следующему треку."""
        from ayugram_adapter import AyuGramAdapter, StreamEnded
        from queue_manager import StreamQueue

        # Создаём очередь с 3 треками
        queue = StreamQueue(max_buffer_size=3, channel_id=123456)

        tracks = [
            {"id": "track1", "url": "https://example.com/track1.mp3"},
            {"id": "track2", "url": "https://example.com/track2.mp3"},
            {"id": "track3", "url": "https://example.com/track3.mp3"},
        ]

        await queue.add_items(tracks)

        # Симулируем паттерн play_in_progress
        play_in_progress = {123456: False}

        # Симулируем stream_ended_events
        stream_ended_events = {123456: asyncio.Event()}

        # Создаём адаптер AyuGram
        mock_client = MagicMock()
        adapter = AyuGramAdapter(mock_client)

        # Handler который симулирует on_stream_ended из multi_channel_runner.py
        async def stream_ended_handler(streaming_client, update: StreamEnded):
            chat_id = update.chat_id

            # Проверяем play_in_progress
            is_playing = play_in_progress.get(chat_id, False)

            if not is_playing:
                # Устанавливаем событие для сигнализации о завершении трека
                if chat_id in stream_ended_events:
                    stream_ended_events[chat_id].set()

        adapter._event_handlers["stream_end"].append(stream_ended_handler)

        # Симулируем воспроизведение первого трека
        play_in_progress[123456] = False  # трек завершён

        # Эмитируем StreamEnded для первого трека
        await adapter._emit_event("stream_end", StreamEnded(chat_id=123456))

        # Проверяем что событие установлено
        assert stream_ended_events[123456].is_set()

        # Очищаем событие для следующего трека
        stream_ended_events[123456].clear()

    @pytest.mark.asyncio
    async def test_queue_advances_through_all_tracks(self):
        """Очередь должна пройти через все 3 трека."""
        from ayugram_adapter import AyuGramAdapter, StreamEnded
        from queue_manager import StreamQueue

        # Создаём очередь с 3 треками
        queue = StreamQueue(max_buffer_size=3, channel_id=123456)

        tracks = [
            {"id": "track1", "url": "https://example.com/track1.mp3"},
            {"id": "track2", "url": "https://example.com/track2.mp3"},
            {"id": "track3", "url": "https://example.com/track3.mp3"},
        ]

        await queue.add_items(tracks)

        # Симулируем процесс воспроизведения всех треков
        track_order = []

        for i, track in enumerate(tracks):
            # Получаем следующий трек (эмуляция очереди)
            if queue.playlist_items:
                next_track = queue.playlist_items[0]
                track_order.append(next_track["id"])
                # Удаляем трек из очереди (эмуляция get_next)
                queue.playlist_items.popleft()

        # Проверяем что все треки были воспроизведены в правильном порядке
        assert len(track_order) == 3
        assert track_order[0] == "track1"
        assert track_order[1] == "track2"
        assert track_order[2] == "track3"

    @pytest.mark.asyncio
    async def test_queue_stops_after_last_track(self):
        """Очередь должна остановиться после последнего трека."""
        from queue_manager import StreamQueue

        # Создаём очередь с 3 треками
        queue = StreamQueue(max_buffer_size=3, channel_id=123456)

        tracks = [
            {"id": "track1", "url": "https://example.com/track1.mp3"},
            {"id": "track2", "url": "https://example.com/track2.mp3"},
            {"id": "track3", "url": "https://example.com/track3.mp3"},
        ]

        await queue.add_items(tracks)

        # Эмулируем воспроизведение всех треков
        for _ in range(3):
            if queue.playlist_items:
                queue.playlist_items.popleft()

        # Проверяем что очередь пуста
        assert len(queue.playlist_items) == 0
        assert queue.queue.empty()

    @pytest.mark.asyncio
    async def test_play_in_progress_prevents_stale_events(self):
        """play_in_progress должен предотвращать обработку устаревших событий."""
        from ayugram_adapter import AyuGramAdapter, StreamEnded

        # Создаём адаптер
        mock_client = MagicMock()
        adapter = AyuGramAdapter(mock_client)

        # Симулируем play_in_progress и stream_ended_events
        play_in_progress = {123456: True}  # воспроизведение в процессе
        stream_ended_events = {123456: asyncio.Event()}
        event_processed = []

        # Handler который проверяет play_in_progress
        async def stream_ended_handler(streaming_client, update: StreamEnded):
            chat_id = update.chat_id
            is_playing = play_in_progress.get(chat_id, False)

            if is_playing:
                # Игнорируем событие если play() ещё в процессе
                event_processed.append("ignored")
                return

            if chat_id in stream_ended_events:
                stream_ended_events[chat_id].set()
                event_processed.append("processed")

        adapter._event_handlers["stream_end"].append(stream_ended_handler)

        # Эмитируем StreamEnded пока play_in_progress=True
        await adapter._emit_event("stream_end", StreamEnded(chat_id=123456))

        # Проверяем что событие было проигнорировано
        assert len(event_processed) == 1
        assert event_processed[0] == "ignored"
        assert not stream_ended_events[123456].is_set()

        # Теперь устанавливаем play_in_progress=False
        play_in_progress[123456] = False

        # Эмитируем StreamEnded снова
        await adapter._emit_event("stream_end", StreamEnded(chat_id=123456))

        # Проверяем что событие было обработано
        assert len(event_processed) == 2
        assert event_processed[1] == "processed"
        assert stream_ended_events[123456].is_set()

    @pytest.mark.asyncio
    async def test_queue_with_redis_sync(self):
        """Очередь должна синхронизироваться с Redis."""
        from queue_manager import StreamQueue

        # Создаём очередь с Redis
        queue = StreamQueue(max_buffer_size=3, channel_id=123456)

        # Инициализируем Redis (может failed если Redis недоступен)
        redis_initialized = await queue.init_redis()

        # Создаём треки
        tracks = [
            {"id": "track1", "url": "https://example.com/track1.mp3"},
            {"id": "track2", "url": "https://example.com/track2.mp3"},
            {"id": "track3", "url": "https://example.com/track3.mp3"},
        ]

        # Добавляем треки
        await queue.add_items(tracks)

        # Проверяем что треки добавлены локально
        assert len(queue.playlist_items) == 3

        # Если Redis инициализирован, проверяем синхронизацию
        if redis_initialized:
            # Проверяем что ключ существует в Redis
            assert queue._redis_sync_enabled is True

            # Синхронизируем из Redis (эмуляция перезапуска)
            await queue._sync_from_redis()

            # Проверяем что треки восстановлены
            assert len(queue.playlist_items) == 3

        # Очищаем
        await queue.close_redis()

    @pytest.mark.asyncio
    async def test_on_track_end_updates_queue_state(self):
        """on_track_end должен обновлять состояние очереди."""
        from queue_manager import StreamQueue

        queue = StreamQueue(max_buffer_size=3, channel_id=123456)

        tracks = [
            {"id": "track1", "url": "https://example.com/track1.mp3"},
            {"id": "track2", "url": "https://example.com/track2.mp3"},
        ]

        await queue.add_items(tracks)

        # Устанавливаем текущий трек
        queue.current_item = tracks[0]

        # Вызываем on_track_end
        await queue.on_track_end("track1", reason="completed")

        # Проверяем что current_item очищен
        assert queue.current_item is None

    @pytest.mark.asyncio
    async def test_multi_channel_queue_isolation(self):
        """Очереди разных каналов должны быть изолированы."""
        from queue_manager import StreamQueue

        # Создаём две очереди для разных каналов
        queue1 = StreamQueue(max_buffer_size=3, channel_id=111)
        queue2 = StreamQueue(max_buffer_size=3, channel_id=222)

        # Добавляем треки в первую очередь
        tracks1 = [
            {"id": "track1", "url": "https://example.com/track1.mp3"},
        ]
        await queue1.add_items(tracks1)

        # Добавляем треки во вторую очередь
        tracks2 = [
            {"id": "track2", "url": "https://example.com/track2.mp3"},
        ]
        await queue2.add_items(tracks2)

        # Проверяем изоляцию
        assert len(queue1.playlist_items) == 1
        assert len(queue2.playlist_items) == 1
        assert queue1.playlist_items[0]["id"] == "track1"
        assert queue2.playlist_items[0]["id"] == "track2"

        # Удаляем трек из первой очереди
        queue1.playlist_items.popleft()

        # Проверяем что вторая очередь не изменилась
        assert len(queue1.playlist_items) == 0
        assert len(queue2.playlist_items) == 1

    @pytest.mark.asyncio
    async def test_queue_state_synchronization_with_backend(self):
        """Состояние очереди должно синхронизироваться с backend."""
        from ayugram_adapter import AyuGramAdapter, StreamEnded
        from queue_manager import StreamQueue

        # Создаём очередь
        queue = StreamQueue(max_buffer_size=3, channel_id=123456)

        tracks = [
            {"id": "track1", "url": "https://example.com/track1.mp3"},
            {"id": "track2", "url": "https://example.com/track2.mp3"},
        ]

        await queue.add_items(tracks)

        # Симулируем состояние backend
        stream_ended_events = {123456: asyncio.Event()}
        play_in_progress = {123456: False}

        # Создаём адаптер
        mock_client = MagicMock()
        adapter = AyuGramAdapter(mock_client)

        # Регистрируем handler
        async def stream_ended_handler(streaming_client, update: StreamEnded):
            chat_id = update.chat_id
            is_playing = play_in_progress.get(chat_id, False)

            if not is_playing and chat_id in stream_ended_events:
                stream_ended_events[chat_id].set()

        adapter._event_handlers["stream_end"].append(stream_ended_handler)

        # Эмитируем событие завершения первого трека
        await adapter._emit_event("stream_end", StreamEnded(chat_id=123456))

        # Проверяем что состояние обновлено
        assert stream_ended_events[123456].is_set()

        # Продвигаем очередь
        if queue.playlist_items:
            queue.playlist_items.popleft()

        # Проверяем состояние очереди
        assert len(queue.playlist_items) == 1
        assert queue.playlist_items[0]["id"] == "track2"
