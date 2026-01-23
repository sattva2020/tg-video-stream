"""add_live_streaming_tables

Revision ID: o2p3q4r5s6t7
Revises: n1o2p3q4r5s6
Create Date: 2026-01-23 18:00:00.000000

Добавляет таблицы для Feature 019 (Real-Time Live Streaming Capabilities):
- live_streams: live streaming broadcasts с RTMP/SRT/WebRTC ingestion
- guest_sessions: guest co-hosting sessions для live streams
- recordings: метаданные записей live streams для последующего воспроизведения

Schema Reference: specs/019-real-time-live-streaming-capabilities/spec.md
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Import GUID type from database module
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from src.database import GUID


# revision identifiers, used by Alembic.
revision: str = 'o2p3q4r5s6t7'
down_revision: Union[str, None] = 'n1o2p3q4r5s6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ENUM types
    # IngestionType enum
    ingestion_type_enum = postgresql.ENUM(
        'rtmp', 'srt', 'webrtc_camera', 'webrtc_screen',
        name='ingestion_type',
        create_type=True
    )
    ingestion_type_enum.create(op.get_bind(), checkfirst=True)

    # LiveStreamStatus enum
    live_stream_status_enum = postgresql.ENUM(
        'idle', 'active', 'paused', 'stopped', 'error',
        name='live_stream_status',
        create_type=True
    )
    live_stream_status_enum.create(op.get_bind(), checkfirst=True)

    # GuestSessionStatus enum
    guest_session_status_enum = postgresql.ENUM(
        'pending', 'accepted', 'active', 'rejected', 'left', 'kicked',
        name='guest_session_status',
        create_type=True
    )
    guest_session_status_enum.create(op.get_bind(), checkfirst=True)

    # RecordingStatus enum
    recording_status_enum = postgresql.ENUM(
        'recording', 'processing', 'ready', 'error', 'deleted',
        name='recording_status',
        create_type=True
    )
    recording_status_enum.create(op.get_bind(), checkfirst=True)

    # RecordingFormat enum
    recording_format_enum = postgresql.ENUM(
        'mp4', 'webm', 'mkv', 'hls',
        name='recording_format',
        create_type=True
    )
    recording_format_enum.create(op.get_bind(), checkfirst=True)

    # Create live_streams table
    op.create_table(
        'live_streams',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('owner_id', GUID(), nullable=False, comment='Telegram user ID владельца stream'),
        sa.Column('chat_id', sa.BigInteger(), nullable=False, comment='Telegram chat ID для трансляции'),
        sa.Column('title', sa.String(255), nullable=False, comment='Название live stream'),
        sa.Column(
            'status',
            live_stream_status_enum,
            nullable=False,
            server_default='idle',
            comment='Текущий статус live stream'
        ),
        sa.Column(
            'ingestion_type',
            ingestion_type_enum,
            nullable=False,
            comment='Тип входящего потока (RTMP, SRT, WEBRTC_CAMERA, WEBRTC_SCREEN)'
        ),
        sa.Column('ingestion_url', sa.String(512), nullable=True, comment='URL для RTMP/SRT ingestion'),
        sa.Column('stream_key', sa.String(255), nullable=True, unique=True, comment='Уникальный ключ для RTMP ingestion'),
        sa.Column('viewer_count', sa.Integer(), nullable=False, server_default='0', comment='Текущее количество зрителей'),
        sa.Column('latency_ms', sa.Integer(), nullable=True, comment='Текущая задержка в миллисекундах'),
        sa.Column('preview_url', sa.String(512), nullable=True, comment='URL для превью потока (HLS/DASH)'),
        sa.Column('recording_enabled', sa.Boolean(), nullable=False, server_default='true', comment='Автоматическая запись потока'),
        sa.Column('active_recording_id', GUID(), nullable=True, comment='ID активной записи (NULL если запись не идет)'),
        sa.Column('max_guests', sa.Integer(), nullable=False, server_default='5', comment='Максимальное количество со-ведущих'),
        sa.Column('current_guest_count', sa.Integer(), nullable=False, server_default='0', comment='Текущее количество активных гостей'),
        sa.Column('quality_preset', sa.String(50), nullable=True, comment='Пресет качества (low, medium, high, ultra)'),
        sa.Column('is_chat_enabled', sa.Boolean(), nullable=False, server_default='true', comment='Включен ли чат во время трансляции'),
        sa.Column('last_error', sa.Text(), nullable=True, comment='Последняя ошибка если status=ERROR'),
        sa.Column('error_count', sa.Integer(), nullable=False, server_default='0', comment='Количество ошибок с момента последнего запуска'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()'), comment='Время создания live stream'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True, comment='Время последнего запуска live stream (NULL если никогда не запускался)'),
        sa.Column('stopped_at', sa.DateTime(timezone=True), nullable=True, comment='Время последней остановки live stream (NULL если не останавливался)'),
        sa.Column('went_live_at', sa.DateTime(timezone=True), nullable=True, comment='Время когда stream стал LIVE (NULL если создан как live)'),
        sa.Column('last_viewer_update', sa.DateTime(timezone=True), nullable=True, comment='Время последнего обновления счетчика зрителей'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_live_streams_owner_id', 'live_streams', ['owner_id'])
    op.create_index('ix_live_streams_chat_id', 'live_streams', ['chat_id'])

    # Create guest_sessions table
    op.create_table(
        'guest_sessions',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('live_stream_id', GUID(), nullable=False),
        sa.Column('user_id', GUID(), nullable=False),
        sa.Column(
            'status',
            guest_session_status_enum,
            nullable=False,
            server_default='pending',
            comment='Текущий статус guest session'
        ),
        sa.Column('can_speak', sa.Boolean(), nullable=False, server_default='true', comment='Разрешение на использование микрофона'),
        sa.Column('can_share_video', sa.Boolean(), nullable=False, server_default='true', comment='Разрешение на включение камеры'),
        sa.Column('can_share_screen', sa.Boolean(), nullable=False, server_default='false', comment='Разрешение на демонстрацию экрана'),
        sa.Column('can_control_stream', sa.Boolean(), nullable=False, server_default='false', comment='Разрешение на управление потоком'),
        sa.Column('can_invite_others', sa.Boolean(), nullable=False, server_default='false', comment='Разрешение на приглашение других гостей'),
        sa.Column('webrtc_connection_id', sa.String(255), nullable=True, unique=True, comment='Уникальный ID WebRTC соединения'),
        sa.Column('connection_quality', sa.String(50), nullable=True, comment='Качество соединения (poor, fair, good, excellent)'),
        sa.Column('invite_token', sa.String(255), nullable=True, unique=True, comment='Уникальный токен для приглашения'),
        sa.Column('invite_message', sa.Text(), nullable=True, comment='Персональное сообщение в приглашении'),
        sa.Column('rejection_reason', sa.Text(), nullable=True, comment='Причина отказа (если rejected)'),
        sa.Column('leave_reason', sa.Text(), nullable=True, comment='Причина выхода (если left)'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()'), comment='Время создания приглашения'),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=True, comment='Время когда guest присоединился к сессии'),
        sa.Column('left_at', sa.DateTime(timezone=True), nullable=True, comment='Время когда guest покинул сессию'),
        sa.Column('last_active_at', sa.DateTime(timezone=True), nullable=True, comment='Время последней активности'),
        sa.ForeignKeyConstraint(['live_stream_id'], ['live_streams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_guest_sessions_live_stream_id', 'guest_sessions', ['live_stream_id'])
    op.create_index('ix_guest_sessions_user_id', 'guest_sessions', ['user_id'])
    op.create_index('ix_guest_sessions_invite_token', 'guest_sessions', ['invite_token'])

    # Create recordings table
    op.create_table(
        'recordings',
        sa.Column('id', GUID(), nullable=False),
        sa.Column('live_stream_id', GUID(), nullable=False, comment='FK to live_streams table'),
        sa.Column('file_path', sa.String(1024), nullable=False, comment='Путь к файлу записи в файловой системе'),
        sa.Column('file_url', sa.String(1024), nullable=True, comment='URL для доступа к записи через API'),
        sa.Column('duration', sa.BigInteger(), nullable=True, comment='Длительность записи в секундах (NULL если запись в процессе)'),
        sa.Column('file_size', sa.BigInteger(), nullable=True, comment='Размер файла в байтах (NULL если запись в процессе)'),
        sa.Column(
            'status',
            recording_status_enum,
            nullable=False,
            server_default='recording',
            comment='Текущий статус записи'
        ),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()'), comment='Время начала записи'),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True, comment='Время окончания записи (NULL если запись активна)'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()'), comment='Время создания записи в БД'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()'), comment='Время последнего обновления записи'),
        sa.Column('format', recording_format_enum, nullable=True, comment='Формат записи (MP4, WEBM, MKV, HLS)'),
        sa.Column('bitrate', sa.Integer(), nullable=True, comment='Средний битрейт в kbps'),
        sa.Column('resolution', sa.String(20), nullable=True, comment='Разрешение видео (напр. "1920x1080", NULL если только аудио)'),
        sa.Column('video_codec', sa.String(50), nullable=True, comment='Видеокодек (напр. "h264", "vp9", NULL если только аудио)'),
        sa.Column('audio_codec', sa.String(50), nullable=True, comment='Аудиокодек (напр. "aac", "opus")'),
        sa.Column('thumbnail_url', sa.String(1024), nullable=True, comment='URL для превью изображения (первый кадр)'),
        sa.Column('preview_url', sa.String(1024), nullable=True, comment='URL для превью видео (короткий фрагмент)'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='Сообщение об ошибке если status=ERROR'),
        sa.ForeignKeyConstraint(['live_stream_id'], ['live_streams.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_recordings_live_stream_id', 'recordings', ['live_stream_id'])


def downgrade() -> None:
    # Drop tables in reverse order due to foreign key constraints
    op.drop_index('ix_recordings_live_stream_id', table_name='recordings')
    op.drop_table('recordings')

    op.drop_index('ix_guest_sessions_invite_token', table_name='guest_sessions')
    op.drop_index('ix_guest_sessions_user_id', table_name='guest_sessions')
    op.drop_index('ix_guest_sessions_live_stream_id', table_name='guest_sessions')
    op.drop_table('guest_sessions')

    op.drop_index('ix_live_streams_chat_id', table_name='live_streams')
    op.drop_index('ix_live_streams_owner_id', table_name='live_streams')
    op.drop_table('live_streams')

    # Drop ENUM types
    postgresql.ENUM(name='recording_format').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='recording_status').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='guest_session_status').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='live_stream_status').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='ingestion_type').drop(op.get_bind(), checkfirst=True)
