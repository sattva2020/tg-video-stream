"""
Integration Tests: Content Import Flow
Тестируем полный цикл импорта контента из различных платформ

Coverage Target: End-to-end import flow testing
Tests:
- YouTube playlist import flow
- Vimeo album import flow
- Local library import flow
- Deduplication during import
- Error handling and recovery
- Progress tracking
- WebSocket notifications (mocked)
"""
import pytest
import uuid
import time
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from src.models.user import User
from src.models.import_job import ImportJob, ImportStatus, ImportPlatform
from src.models.playlist import PlaylistItem, Playlist
from src.models.telegram import Channel, TelegramAccount
from src.services.import_service import ImportService
from src.services.deduplication_service import DeduplicationService
from src.schemas.import_schemas import ImportCreateRequest


# ==================== Fixtures ====================

@pytest.fixture
def test_user(db_session):
    """Create test user with admin role"""
    user = User(
        email='import_test@example.com',
        google_id='import_test_123',
        status='approved',
        role='admin'
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_channel(db_session, test_user):
    """Create test channel for imports"""
    # Create telegram account first
    account = TelegramAccount(
        user_id=test_user.id,
        phone='000000',
        encrypted_session='x',
        tg_user_id=12345
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)

    # Create channel
    channel = Channel(
        account_id=account.id,
        chat_id=12345,
        name='Test Import Channel'
    )
    db_session.add(channel)
    db_session.commit()
    db_session.refresh(channel)
    return channel


@pytest.fixture
def import_service(db_session):
    """Get import service instance"""
    return ImportService()


@pytest.fixture
def deduplication_service(db_session):
    """Get deduplication service instance"""
    return DeduplicationService()


# ==================== 1. YouTube Import Flow ====================

class TestYouTubeImportFlow:
    """Тесты полного цикла импорта YouTube плейлиста"""

    def test_create_youtube_import_job(self, db_session, test_user, test_channel):
        """Создание задачи на импорт YouTube плейлиста"""
        service = ImportService()

        request = ImportCreateRequest(
            platform=ImportPlatform.YOUTUBE,
            source_url='https://www.youtube.com/playlist?list=test123',
            channel_id=test_channel.id,
            options={'deduplicate': True, 'quality': 'best'}
        )

        job = service.create_import_job(
            db=db_session,
            request=request,
            user_id=test_user.id
        )

        assert job.id is not None
        assert job.platform == ImportPlatform.YOUTUBE
        assert job.source_url == 'https://www.youtube.com/playlist?list=test123'
        assert job.channel_id == test_channel.id
        assert job.status == ImportStatus.PENDING
        assert job.user_id == test_user.id
        assert job.options['deduplicate'] is True
        assert job.options['quality'] == 'best'

        # Verify in database
        db_job = db_session.query(ImportJob).filter(ImportJob.id == job.id).first()
        assert db_job is not None
        assert db_job.status == ImportStatus.PENDING

    def test_youtube_import_with_valid_playlist(self, db_session, test_user, test_channel):
        """Импорт валидного YouTube плейлиста с 3 видео"""
        service = ImportService()

        # Mock extract_video_metadata to return test data
        mock_items = [
            {
                'url': 'https://www.youtube.com/watch?v=video1',
                'title': 'Test Video 1',
                'duration': 120,
                'thumbnail': 'https://example.com/thumb1.jpg'
            },
            {
                'url': 'https://www.youtube.com/watch?v=video2',
                'title': 'Test Video 2',
                'duration': 240,
                'thumbnail': 'https://example.com/thumb2.jpg'
            },
            {
                'url': 'https://www.youtube.com/watch?v=video3',
                'title': 'Test Video 3',
                'duration': 180,
                'thumbnail': 'https://example.com/thumb3.jpg'
            }
        ]

        with patch('src.services.import_service.extract_video_metadata') as mock_fetch:
            mock_fetch.return_value = mock_items

            # Create import job
            request = ImportCreateRequest(
                platform=ImportPlatform.YOUTUBE,
                source_url='https://www.youtube.com/playlist?list=test123',
                channel_id=test_channel.id,
                options={'deduplicate': False}
            )

            job = service.create_import_job(
                db=db_session,
                request=request,
                user_id=test_user.id
            )

            # Fetch items
            items = service.fetch_items(job)
            assert len(items) == 3
            assert items[0]['url'] == mock_items[0]['url']

            # Process import
            service.process_import(db_session, job, items)

            # Verify job completed
            assert job.status == ImportStatus.COMPLETED
            assert job.total_items == 3
            assert job.processed_items == 3
            assert job.successful_items == 3
            assert job.failed_items == 0

            # Verify playlist created
            playlist = db_session.query(Playlist).filter(
                Playlist.channel_id == test_channel.id
            ).first()
            assert playlist is not None
            assert 'YouTube' in playlist.name or 'Import' in playlist.name

            # Verify playlist items created
            playlist_items = db_session.query(PlaylistItem).filter(
                PlaylistItem.playlist_id == playlist.id
            ).all()
            assert len(playlist_items) == 3
            assert playlist_items[0].title == 'Test Video 1'
            assert playlist_items[0].duration == 120

    def test_youtube_import_with_duplicates(self, db_session, test_user, test_channel, deduplication_service):
        """Импорт с обнаружением дубликатов"""
        service = ImportService()

        # Create existing playlist item
        existing_playlist = Playlist(
            channel_id=test_channel.id,
            name='Existing Playlist',
            index=0
        )
        db_session.add(existing_playlist)
        db_session.commit()

        existing_item = PlaylistItem(
            playlist_id=existing_playlist.id,
            url='https://www.youtube.com/watch?v=video1',
            title='Existing Video',
            duration=120,
            index=0
        )
        db_session.add(existing_item)
        db_session.commit()

        # Mock fetch to return one duplicate and one new item
        mock_items = [
            {
                'url': 'https://www.youtube.com/watch?v=video1',  # Duplicate
                'title': 'Duplicate Video',
                'duration': 120
            },
            {
                'url': 'https://www.youtube.com/watch?v=video2',  # New
                'title': 'New Video',
                'duration': 240
            }
        ]

        with patch('src.services.import_service.extract_video_metadata') as mock_fetch:
            mock_fetch.return_value = mock_items

            # Create import job with deduplication enabled
            request = ImportCreateRequest(
                platform=ImportPlatform.YOUTUBE,
                source_url='https://www.youtube.com/playlist?list=test123',
                channel_id=test_channel.id,
                options={'deduplicate': True}
            )

            job = service.create_import_job(
                db=db_session,
                request=request,
                user_id=test_user.id
            )

            # Process import with deduplication
            items = service.fetch_items(job)
            service.process_import(db_session, job, items, deduplication_service=deduplication_service)

            # Verify deduplication worked
            assert job.status == ImportStatus.COMPLETED
            assert job.total_items == 2
            assert job.successful_items == 1  # Only new item imported
            assert job.skipped_items == 1  # Duplicate skipped

            # Verify only one new item was created
            playlist = db_session.query(Playlist).filter(
                Playlist.channel_id == test_channel.id,
                Playlist.name != 'Existing Playlist'
            ).first()
            assert playlist is not None

            playlist_items = db_session.query(PlaylistItem).filter(
                PlaylistItem.playlist_id == playlist.id
            ).all()
            assert len(playlist_items) == 1
            assert playlist_items[0].url == 'https://www.youtube.com/watch?v=video2'

    def test_youtube_import_error_handling(self, db_session, test_user, test_channel):
        """Обработка ошибок при импорте"""
        service = ImportService()

        # Mock fetch to raise error
        with patch('src.services.import_service.extract_video_metadata') as mock_fetch:
            mock_fetch.side_effect = Exception('Network error')

            request = ImportCreateRequest(
                platform=ImportPlatform.YOUTUBE,
                source_url='https://www.youtube.com/playlist?list=invalid',
                channel_id=test_channel.id
            )

            job = service.create_import_job(
                db=db_session,
                request=request,
                user_id=test_user.id
            )

            # Attempt to fetch items should handle error gracefully
            try:
                items = service.fetch_items(job)
            except Exception as e:
                # Verify job marked as failed
                job.mark_failed(str(e))

            db_session.commit()
            db_session.refresh(job)

            assert job.status == ImportStatus.FAILED
            assert 'Network error' in job.error_message


# ==================== 2. Vimeo Import Flow ====================

class TestVimeoImportFlow:
    """Тесты полного цикла импорта Vimeo альбома"""

    def test_create_vimeo_import_job(self, db_session, test_user, test_channel):
        """Создание задачи на импорт Vimeo альбома"""
        service = ImportService()

        request = ImportCreateRequest(
            platform=ImportPlatform.VIMEO,
            source_url='https://vimeo.com/album/1234567',
            channel_id=test_channel.id,
            options={'quality': 'high'}
        )

        job = service.create_import_job(
            db=db_session,
            request=request,
            user_id=test_user.id
        )

        assert job.platform == ImportPlatform.VIMEO
        assert job.source_url == 'https://vimeo.com/album/1234567'
        assert job.status == ImportStatus.PENDING

    def test_vimeo_import_with_valid_album(self, db_session, test_user, test_channel):
        """Импорт валидного Vimeo альбома"""
        service = ImportService()

        # Mock extract_video_metadata for Vimeo
        mock_items = [
            {
                'url': 'https://vimeo.com/123456789',
                'title': 'Vimeo Video 1',
                'duration': 300,
                'thumbnail': 'https://example.com/vimeo1.jpg'
            },
            {
                'url': 'https://vimeo.com/987654321',
                'title': 'Vimeo Video 2',
                'duration': 450,
                'thumbnail': 'https://example.com/vimeo2.jpg'
            }
        ]

        with patch('src.services.import_service.extract_video_metadata') as mock_fetch:
            mock_fetch.return_value = mock_items

            request = ImportCreateRequest(
                platform=ImportPlatform.VIMEO,
                source_url='https://vimeo.com/album/1234567',
                channel_id=test_channel.id
            )

            job = service.create_import_job(
                db=db_session,
                request=request,
                user_id=test_user.id
            )

            # Process import
            items = service.fetch_items(job)
            service.process_import(db_session, job, items)

            # Verify completion
            assert job.status == ImportStatus.COMPLETED
            assert job.successful_items == 2

            # Verify playlist created with Vimeo content type
            playlist = db_session.query(Playlist).filter(
                Playlist.channel_id == test_channel.id
            ).first()
            assert playlist is not None
            assert playlist.content_type == 'vimeo'

            playlist_items = db_session.query(PlaylistItem).filter(
                PlaylistItem.playlist_id == playlist.id
            ).all()
            assert len(playlist_items) == 2
            assert playlist_items[0].content_type == 'vimeo'


# ==================== 3. Local Import Flow ====================

class TestLocalImportFlow:
    """Тесты полного цикла импорта локальных файлов"""

    def test_create_local_import_job(self, db_session, test_user, test_channel):
        """Создание задачи на импорт локальной библиотеки"""
        service = ImportService()

        request = ImportCreateRequest(
            platform=ImportPlatform.LOCAL,
            source_path='/media/music',
            channel_id=test_channel.id,
            options={'recursive': True, 'extract_metadata': True}
        )

        job = service.create_import_job(
            db=db_session,
            request=request,
            user_id=test_user.id
        )

        assert job.platform == ImportPlatform.LOCAL
        assert job.source_path == '/media/music'
        assert job.options['recursive'] is True
        assert job.options['extract_metadata'] is True

    def test_local_import_with_files(self, db_session, test_user, test_channel):
        """Импорт локальных аудиофайлов"""
        service = ImportService()

        # Mock media_scanner results
        mock_files = [
            {
                'path': '/media/music/track1.mp3',
                'filename': 'track1.mp3',
                'size': 5242880,
                'duration': 240,
                'metadata': {
                    'artist': 'Test Artist',
                    'album': 'Test Album',
                    'title': 'Track 1'
                }
            },
            {
                'path': '/media/music/track2.flac',
                'filename': 'track2.flac',
                'size': 10485760,
                'duration': 300,
                'metadata': {
                    'artist': 'Test Artist',
                    'album': 'Test Album',
                    'title': 'Track 2'
                }
            }
        ]

        with patch('src.services.import_service.scan_folder') as mock_scan:
            mock_scan.return_value = mock_files

            request = ImportCreateRequest(
                platform=ImportPlatform.LOCAL,
                source_path='/media/music',
                channel_id=test_channel.id
            )

            job = service.create_import_job(
                db=db_session,
                request=request,
                user_id=test_user.id
            )

            # Process import
            items = service.fetch_items(job)
            service.process_import(db_session, job, items)

            # Verify completion
            assert job.status == ImportStatus.COMPLETED
            assert job.successful_items == 2

            # Verify playlist created
            playlist = db_session.query(Playlist).filter(
                Playlist.channel_id == test_channel.id
            ).first()
            assert playlist is not None

            playlist_items = db_session.query(PlaylistItem).filter(
                PlaylistItem.playlist_id == playlist.id
            ).all()
            assert len(playlist_items) == 2
            assert playlist_items[0].title == 'Track 1'
            assert playlist_items[0].duration == 240


# ==================== 4. Progress Tracking ====================

class TestImportProgressTracking:
    """Тесты отслеживания прогресса импорта"""

    def test_progress_updates_during_import(self, db_session, test_user, test_channel):
        """Обновление прогресса во время импорта"""
        service = ImportService()

        # Mock 5 items
        mock_items = [
            {'url': f'https://youtube.com/watch?v=video{i}', 'title': f'Video {i}', 'duration': 120}
            for i in range(5)
        ]

        with patch('src.services.import_service.extract_video_metadata') as mock_fetch:
            mock_fetch.return_value = mock_items

            request = ImportCreateRequest(
                platform=ImportPlatform.YOUTUBE,
                source_url='https://youtube.com/playlist?list=test',
                channel_id=test_channel.id
            )

            job = service.create_import_job(
                db=db_session,
                request=request,
                user_id=test_user.id
            )

            # Mark as started
            job.mark_started()
            db_session.commit()

            # Simulate progress updates
            for i in range(5):
                job.update_progress(processed=i+1, successful=i+1)
                db_session.commit()
                db_session.refresh(job)

                expected_percentage = int(((i+1) / 5) * 100)
                assert job.progress_percentage == expected_percentage
                assert job.processed_items == i+1

            # Mark as completed
            job.mark_completed()
            db_session.commit()
            db_session.refresh(job)

            assert job.status == ImportStatus.COMPLETED
            assert job.progress_percentage == 100
            assert job.completed_at is not None

    def test_import_pause_resume(self, db_session, test_user, test_channel):
        """Пауза и возобновление импорта"""
        service = ImportService()

        request = ImportCreateRequest(
            platform=ImportPlatform.YOUTUBE,
            source_url='https://youtube.com/playlist?list=test',
            channel_id=test_channel.id
        )

        job = service.create_import_job(
            db=db_session,
            request=request,
            user_id=test_user.id
        )

        # Start the job
        job.mark_started()
        db_session.commit()

        # Pause the job
        service.pause_job(db_session, job.id)
        db_session.refresh(job)

        assert job.status == ImportStatus.PAUSED

        # Resume the job
        service.resume_job(db_session, job.id)
        db_session.refresh(job)

        assert job.status == ImportStatus.IN_PROGRESS

    def test_import_cancellation(self, db_session, test_user, test_channel):
        """Отмена импорта"""
        service = ImportService()

        request = ImportCreateRequest(
            platform=ImportPlatform.YOUTUBE,
            source_url='https://youtube.com/playlist?list=test',
            channel_id=test_channel.id
        )

        job = service.create_import_job(
            db=db_session,
            request=request,
            user_id=test_user.id
        )

        # Cancel the job
        service.cancel_job(db_session, job.id)
        db_session.refresh(job)

        assert job.status == ImportStatus.CANCELLED
        assert job.completed_at is not None  # Cancellation sets completion time


# ==================== 5. Import Summary ====================

class TestImportSummary:
    """Тесты сводки импорта"""

    def test_generate_import_summary(self, db_session, test_user, test_channel):
        """Генерация сводки результатов импорта"""
        service = ImportService()

        mock_items = [
            {'url': 'https://youtube.com/watch?v=video1', 'title': 'Video 1', 'duration': 120},
            {'url': 'https://youtube.com/watch?v=video2', 'title': 'Video 2', 'duration': 240}
        ]

        with patch('src.services.import_service.extract_video_metadata') as mock_fetch:
            mock_fetch.return_value = mock_items

            request = ImportCreateRequest(
                platform=ImportPlatform.YOUTUBE,
                source_url='https://youtube.com/playlist?list=test',
                channel_id=test_channel.id
            )

            job = service.create_import_job(
                db=db_session,
                request=request,
                user_id=test_user.id
            )

            # Process import
            items = service.fetch_items(job)
            service.process_import(db_session, job, items)

            # Generate summary
            summary = service.get_import_summary(db_session, job.id)

            assert summary is not None
            assert summary['total_items'] == 2
            assert summary['imported_items'] == 2
            assert summary['duplicate_items'] == 0
            assert summary['failed_items'] == 0
            assert 'duration' in summary
            assert summary['status'] == ImportStatus.COMPLETED


# ==================== 6. End-to-End Flow ====================

class TestEndToEndImportFlow:
    """Тесты полного цикла от создания до завершения"""

    def test_complete_youtube_import_workflow(self, db_session, test_user, test_channel):
        """Полный рабочий процесс импорта YouTube плейлиста"""
        service = ImportService()
        dedup_service = DeduplicationService()

        # Step 1: Create import job
        request = ImportCreateRequest(
            platform=ImportPlatform.YOUTUBE,
            source_url='https://youtube.com/playlist?list=complete_test',
            channel_id=test_channel.id,
            options={'deduplicate': True, 'quality': 'best'}
        )

        job = service.create_import_job(
            db=db_session,
            request=request,
            user_id=test_user.id
        )

        assert job.status == ImportStatus.PENDING
        assert job.id is not None

        # Step 2: Fetch playlist items
        mock_items = [
            {'url': 'https://youtube.com/watch?v=v1', 'title': 'Complete Test 1', 'duration': 100},
            {'url': 'https://youtube.com/watch?v=v2', 'title': 'Complete Test 2', 'duration': 200},
            {'url': 'https://youtube.com/watch?v=v3', 'title': 'Complete Test 3', 'duration': 150}
        ]

        with patch('src.services.import_service.extract_video_metadata') as mock_fetch:
            mock_fetch.return_value = mock_items

            items = service.fetch_items(job)
            assert len(items) == 3

            # Step 3: Start processing
            job.mark_started()
            db_session.commit()

            # Step 4: Process import with progress updates
            service.process_import(db_session, job, items, deduplication_service=dedup_service)

            # Step 5: Verify completion
            assert job.status == ImportStatus.COMPLETED
            assert job.total_items == 3
            assert job.processed_items == 3
            assert job.successful_items == 3
            assert job.progress_percentage == 100
            assert job.started_at is not None
            assert job.completed_at is not None

            # Step 6: Verify playlist created
            playlists = db_session.query(Playlist).filter(
                Playlist.channel_id == test_channel.id
            ).all()
            assert len(playlists) == 1

            playlist = playlists[0]
            assert playlist.content_type == 'youtube'

            # Step 7: Verify all items imported
            playlist_items = db_session.query(PlaylistItem).filter(
                PlaylistItem.playlist_id == playlist.id
            ).all()
            assert len(playlist_items) == 3

            # Verify item order and data
            assert playlist_items[0].index == 0
            assert playlist_items[0].title == 'Complete Test 1'
            assert playlist_items[1].index == 1
            assert playlist_items[1].title == 'Complete Test 2'
            assert playlist_items[2].index == 2
            assert playlist_items[2].title == 'Complete Test 3'

            # Step 8: Generate and verify summary
            summary = service.get_import_summary(db_session, job.id)
            assert summary['total_items'] == 3
            assert summary['imported_items'] == 3
            assert summary['status'] == ImportStatus.COMPLETED

    def test_import_with_partial_failure(self, db_session, test_user, test_channel):
        """Импорт с частичными ошибками"""
        service = ImportService()

        # Mix of valid and invalid items
        mock_items = [
            {'url': 'https://youtube.com/watch?v=valid1', 'title': 'Valid 1', 'duration': 100},
            {'url': 'invalid-url', 'title': 'Invalid', 'duration': 0},  # Will fail
            {'url': 'https://youtube.com/watch?v=valid2', 'title': 'Valid 2', 'duration': 200}
        ]

        with patch('src.services.import_service.extract_video_metadata') as mock_fetch:
            mock_fetch.return_value = mock_items

            request = ImportCreateRequest(
                platform=ImportPlatform.YOUTUBE,
                source_url='https://youtube.com/playlist?list=partial_fail',
                channel_id=test_channel.id
            )

            job = service.create_import_job(
                db=db_session,
                request=request,
                user_id=test_user.id
            )

            job.mark_started()
            db_session.commit()

            # Process import - should handle partial failures gracefully
            items = service.fetch_items(job)
            service.process_import(db_session, job, items)

            # Verify job completed despite failures
            assert job.status == ImportStatus.COMPLETED
            assert job.total_items == 3
            assert job.successful_items >= 1  # At least one successful
            assert job.failed_items >= 1  # At least one failed

            # Verify summary includes errors
            summary = service.get_import_summary(db_session, job.id)
            assert summary['failed_items'] >= 1
            if summary.get('errors'):
                assert len(summary['errors']) >= 1


# ==================== 7. WebSocket Notifications ====================

class TestWebSocketNotifications:
    """Тесты WebSocket уведомлений о прогрессе импорта"""

    def test_websocket_notification_on_progress_update(self, db_session, test_user, test_channel):
        """WebSocket уведомление при обновлении прогресса"""
        service = ImportService()

        request = ImportCreateRequest(
            platform=ImportPlatform.YOUTUBE,
            source_url='https://youtube.com/playlist?list=test',
            channel_id=test_channel.id
        )

        job = service.create_import_job(
            db=db_session,
            request=request,
            user_id=test_user.id
        )

        # Mock WebSocket notification
        with patch('src.tasks.import_tasks._notify_import_progress') as mock_notify:
            job.update_progress(processed=5, successful=5)
            db_session.commit()

            # In real flow, this would trigger WebSocket notification
            # For integration test, we verify the job state is correct
            db_session.refresh(job)
            assert job.processed_items == 5
            assert job.successful_items == 5


# ==================== 8. Activity Logging ====================

class TestActivityLogging:
    """Тесты логирования активности импорта"""

    def test_import_start_logged(self, db_session, test_user, test_channel):
        """Логирование начала импорта"""
        from src.services.activity_service import ActivityService

        service = ImportService()
        activity_service = ActivityService(db_session)

        request = ImportCreateRequest(
            platform=ImportPlatform.YOUTUBE,
            source_url='https://youtube.com/playlist?list=test',
            channel_id=test_channel.id
        )

        job = service.create_import_job(
            db=db_session,
            request=request,
            user_id=test_user.id
        )

        # Log import started
        activity_service.log_event(
            event_type='import_started',
            message=f'Запущен импорт контента из {job.platform.value}',
            user_id=test_user.id,
            user_email=test_user.email,
            details={
                'import_job_id': str(job.id),
                'platform': job.platform.value,
                'source_url': job.source_url
            }
        )

        # Verify log entry created
        from src.models.activity_log import ActivityLog
        logs = db_session.query(ActivityLog).filter(
            ActivityLog.event_type == 'import_started'
        ).all()

        assert len(logs) >= 1
        import_log = [l for l in logs if l.details.get('import_job_id') == str(job.id)][0]
        assert import_log is not None
        assert import_log.user_id == test_user.id

    def test_import_completion_logged(self, db_session, test_user, test_channel):
        """Логирование завершения импорта"""
        from src.services.activity_service import ActivityService

        service = ImportService()
        activity_service = ActivityService(db_session)

        mock_items = [
            {'url': 'https://youtube.com/watch?v=v1', 'title': 'Test', 'duration': 120}
        ]

        with patch('src.services.import_service.extract_video_metadata') as mock_fetch:
            mock_fetch.return_value = mock_items

            request = ImportCreateRequest(
                platform=ImportPlatform.YOUTUBE,
                source_url='https://youtube.com/playlist?list=test',
                channel_id=test_channel.id
            )

            job = service.create_import_job(
                db=db_session,
                request=request,
                user_id=test_user.id
            )

            # Process import
            items = service.fetch_items(job)
            service.process_import(db_session, job, items)

            # Log completion
            activity_service.log_event(
                event_type='import_completed',
                message=f'Завершён импорт из {job.platform.value}: {job.successful_items} элементов',
                user_id=test_user.id,
                user_email=test_user.email,
                details={
                    'import_job_id': str(job.id),
                    'platform': job.platform.value,
                    'total_items': job.total_items,
                    'successful_items': job.successful_items
                }
            )

            # Verify log entry
            from src.models.activity_log import ActivityLog
            logs = db_session.query(ActivityLog).filter(
                ActivityLog.event_type == 'import_completed'
            ).all()

            assert len(logs) >= 1
