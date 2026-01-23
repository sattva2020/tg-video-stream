"""add_interaction_models

Revision ID: o2p3q4r5s6t7
Revises: n1o2p3q4r5s6
Create Date: 2026-01-23 17:00:00.000000

Adds database tables for viewer interaction and engagement features (Feature 020):
- Polls: polls, poll_options, poll_votes (with poll_type and poll_status enums)
- Q&A: questions, question_upvotes (with question_status enum)
- Interactions: emoji_reactions, chat_messages (with reaction_display_status and chat_message_status enums)
- Engagement: shoutouts, ctas (with shoutout_type, shoutout_status, cta_action_type, cta_status enums)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import src.database


# revision identifiers, used by Alembic.
revision: str = 'o2p3q4r5s6t7'
down_revision: Union[str, None] = 'n1o2p3q4r5s6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ENUM types
    # Poll enums
    poll_type_enum = sa.Enum('single_choice', 'multiple_choice', name='poll_type')
    poll_type_enum.create(op.get_bind(), checkfirst=True)
    poll_status_enum = sa.Enum('draft', 'active', 'paused', 'closed', name='poll_status')
    poll_status_enum.create(op.get_bind(), checkfirst=True)

    # Question status enum
    question_status_enum = sa.Enum('pending', 'answered', 'rejected', 'pinned', name='question_status')
    question_status_enum.create(op.get_bind(), checkfirst=True)

    # Reaction display status enum
    reaction_display_status_enum = sa.Enum('pending', 'visible', 'expired', 'hidden', name='reaction_display_status')
    reaction_display_status_enum.create(op.get_bind(), checkfirst=True)

    # Chat message status enum
    chat_message_status_enum = sa.Enum('pending', 'visible', 'hidden', 'flagged', name='chat_message_status')
    chat_message_status_enum.create(op.get_bind(), checkfirst=True)

    # Shoutout enums
    shoutout_type_enum = sa.Enum('new_follower', 'new_subscriber', 'donor', 'top_viewer', 'custom', name='shoutout_type')
    shoutout_type_enum.create(op.get_bind(), checkfirst=True)
    shoutout_status_enum = sa.Enum('pending', 'displayed', 'skipped', 'cancelled', name='shoutout_status')
    shoutout_status_enum.create(op.get_bind(), checkfirst=True)

    # CTA enums
    cta_action_type_enum = sa.Enum('subscribe', 'visit_link', 'donate', 'follow_social', 'join_group', 'custom', name='cta_action_type')
    cta_action_type_enum.create(op.get_bind(), checkfirst=True)
    cta_status_enum = sa.Enum('draft', 'scheduled', 'active', 'paused', 'completed', 'expired', name='cta_status')
    cta_status_enum.create(op.get_bind(), checkfirst=True)

    # Create polls table
    op.create_table(
        'polls',
        sa.Column('id', src.database.GUID(), nullable=False),
        sa.Column('owner_id', src.database.GUID(), nullable=False),
        sa.Column('question', sa.String(500), nullable=False, comment='Вопрос опроса'),
        sa.Column('description', sa.String(2000), nullable=True, comment='Описание опроса (опционально)'),
        sa.Column('poll_type', sa.Enum('single_choice', 'multiple_choice', name='poll_type', create_type=False), nullable=False, comment='Тип опроса (single/multiple choice)'),
        sa.Column('status', sa.Enum('draft', 'active', 'paused', 'closed', name='poll_status', create_type=False), nullable=False, comment='Текущий статус опроса'),
        sa.Column('allow_multiple_votes', sa.Boolean(), nullable=False, comment='Разрешить пользователю голосовать несколько раз'),
        sa.Column('is_anonymous', sa.Boolean(), nullable=False, comment='Анонимное голосование (не записывать user_id)'),
        sa.Column('max_votes_per_user', sa.Integer(), nullable=True, comment='Максимальное количество голосов одного пользователя (NULL = без ограничений)'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment='Время создания опроса'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True, comment='Время запуска опроса (NULL если не запускался)'),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True, comment='Запланированное время окончания (NULL если бессрочный)'),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True, comment='Фактическое время закрытия (NULL если открыт)'),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_polls_owner_id', 'polls', ['owner_id'])

    # Create poll_options table
    op.create_table(
        'poll_options',
        sa.Column('id', src.database.GUID(), nullable=False),
        sa.Column('poll_id', src.database.GUID(), nullable=False),
        sa.Column('text', sa.String(500), nullable=False, comment='Текст варианта ответа'),
        sa.Column('order', sa.Integer(), nullable=False, comment='Порядок отображения варианта'),
        sa.Column('vote_count', sa.Integer(), nullable=False, comment='Кэшированное количество голосов'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment='Время создания варианта'),
        sa.ForeignKeyConstraint(['poll_id'], ['polls.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_poll_options_poll_id', 'poll_options', ['poll_id'])
    op.create_index('ix_poll_options_poll_order', 'poll_options', ['poll_id', 'order'])

    # Create poll_votes table
    op.create_table(
        'poll_votes',
        sa.Column('id', src.database.GUID(), nullable=False),
        sa.Column('poll_id', src.database.GUID(), nullable=False),
        sa.Column('option_id', src.database.GUID(), nullable=False),
        sa.Column('user_id', src.database.GUID(), nullable=True),
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=True, comment='Telegram ID для анонимных пользователей'),
        sa.Column('voted_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment='Время голосования'),
        sa.ForeignKeyConstraint(['poll_id'], ['polls.id'], ),
        sa.ForeignKeyConstraint(['option_id'], ['poll_options.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_poll_votes_poll_id', 'poll_votes', ['poll_id'])
    op.create_index('ix_poll_votes_option_id', 'poll_votes', ['option_id'])
    op.create_index('ix_poll_votes_user_id', 'poll_votes', ['user_id'])
    op.create_index('ix_poll_votes_telegram_user_id', 'poll_votes', ['telegram_user_id'])
    op.create_index('ix_poll_votes_poll_user', 'poll_votes', ['poll_id', 'user_id'])
    op.create_index('ix_poll_votes_poll_telegram', 'poll_votes', ['poll_id', 'telegram_user_id'])

    # Create questions table
    op.create_table(
        'questions',
        sa.Column('id', src.database.GUID(), nullable=False),
        sa.Column('stream_id', src.database.GUID(), nullable=False),
        sa.Column('author_id', src.database.GUID(), nullable=True),
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=True, comment='Telegram ID для анонимных пользователей'),
        sa.Column('author_name', sa.String(255), nullable=True, comment='Имя автора (для анонимных вопросов или отображения)'),
        sa.Column('content', sa.Text(), nullable=False, comment='Текст вопроса'),
        sa.Column('status', sa.Enum('pending', 'answered', 'rejected', 'pinned', name='question_status', create_type=False), nullable=False, comment='Текущий статус вопроса'),
        sa.Column('is_pinned', sa.Boolean(), nullable=False, comment='Вопрос закреплен (важный)'),
        sa.Column('upvote_count', sa.Integer(), nullable=False, comment='Кэшированное количество upvotes'),
        sa.Column('answer', sa.Text(), nullable=True, comment='Ответ на вопрос (NULL если не отвечен)'),
        sa.Column('answered_at', sa.DateTime(timezone=True), nullable=True, comment='Время ответа на вопрос (NULL если не отвечен)'),
        sa.Column('is_filtered', sa.Boolean(), nullable=False, comment='Вопрос отфильтрован модерацией'),
        sa.Column('filter_reason', sa.String(500), nullable=True, comment='Причина фильтрации (например, неуместный контент)'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment='Время создания вопроса'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment='Время последнего обновления'),
        sa.ForeignKeyConstraint(['stream_id'], ['streams.id'], ),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_questions_stream_id', 'questions', ['stream_id'])
    op.create_index('ix_questions_author_id', 'questions', ['author_id'])
    op.create_index('ix_questions_telegram_user_id', 'questions', ['telegram_user_id'])
    op.create_index('ix_questions_stream_status', 'questions', ['stream_id', 'status'])
    op.create_index('ix_questions_stream_upvotes', 'questions', ['stream_id', 'upvote_count'])
    op.create_index('ix_questions_created_at', 'questions', ['created_at'])

    # Create question_upvotes table
    op.create_table(
        'question_upvotes',
        sa.Column('id', src.database.GUID(), nullable=False),
        sa.Column('question_id', src.database.GUID(), nullable=False),
        sa.Column('user_id', src.database.GUID(), nullable=True),
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=True, comment='Telegram ID для анонимных пользователей'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment='Время upvote'),
        sa.ForeignKeyConstraint(['question_id'], ['questions.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_question_upvotes_question_id', 'question_upvotes', ['question_id'])
    op.create_index('ix_question_upvotes_user_id', 'question_upvotes', ['user_id'])
    op.create_index('ix_question_upvotes_telegram_user_id', 'question_upvotes', ['telegram_user_id'])
    op.create_index('ix_question_upvotes_question_user', 'question_upvotes', ['question_id', 'user_id'])
    op.create_index('ix_question_upvotes_question_telegram', 'question_upvotes', ['question_id', 'telegram_user_id'])
    op.create_index('ix_question_upvotes_created_at', 'question_upvotes', ['created_at'])

    # Create emoji_reactions table
    op.create_table(
        'emoji_reactions',
        sa.Column('id', src.database.GUID(), nullable=False),
        sa.Column('stream_id', src.database.GUID(), nullable=False),
        sa.Column('user_id', src.database.GUID(), nullable=True),
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=True, comment='Telegram ID для анонимных пользователей'),
        sa.Column('emoji', sa.String(100), nullable=False, comment='Эмодзи (Unicode or shortname)'),
        sa.Column('display_status', sa.Enum('pending', 'visible', 'expired', 'hidden', name='reaction_display_status', create_type=False), nullable=False, comment='Статус отображения реакции'),
        sa.Column('position_x', sa.Integer(), nullable=False, comment='Позиция X на overlay (0-100%)'),
        sa.Column('position_y', sa.Integer(), nullable=False, comment='Позиция Y на overlay (0-100%)'),
        sa.Column('scale', sa.Integer(), nullable=False, comment='Размер эмодзи в процентах'),
        sa.Column('animation_type', sa.String(50), nullable=True, comment='Тип анимации (fade, pop, bounce, etc.)'),
        sa.Column('is_filtered', sa.Boolean(), nullable=False, comment='Реакция отфильтрована модерацией'),
        sa.Column('filter_reason', sa.String(500), nullable=True, comment='Причина фильтрации'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment='Время создания реакции'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True, comment='Время окончания отображения (NULL = бессрочно)'),
        sa.ForeignKeyConstraint(['stream_id'], ['streams.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_emoji_reactions_stream_id', 'emoji_reactions', ['stream_id'])
    op.create_index('ix_emoji_reactions_user_id', 'emoji_reactions', ['user_id'])
    op.create_index('ix_emoji_reactions_telegram_user_id', 'emoji_reactions', ['telegram_user_id'])
    op.create_index('ix_emoji_reactions_stream_status', 'emoji_reactions', ['stream_id', 'display_status'])
    op.create_index('ix_emoji_reactions_stream_created', 'emoji_reactions', ['stream_id', 'created_at'])
    op.create_index('ix_emoji_reactions_expires_at', 'emoji_reactions', ['expires_at'])

    # Create chat_messages table
    op.create_table(
        'chat_messages',
        sa.Column('id', src.database.GUID(), nullable=False),
        sa.Column('stream_id', src.database.GUID(), nullable=False),
        sa.Column('author_id', src.database.GUID(), nullable=True),
        sa.Column('telegram_user_id', sa.BigInteger(), nullable=True, comment='Telegram ID для анонимных пользователей'),
        sa.Column('author_name', sa.String(255), nullable=False, comment='Имя автора для отображения'),
        sa.Column('author_avatar_url', sa.String(500), nullable=True, comment='URL аватара автора (опционально)'),
        sa.Column('content', sa.Text(), nullable=False, comment='Текст сообщения'),
        sa.Column('message_status', sa.Enum('pending', 'visible', 'hidden', 'flagged', name='chat_message_status', create_type=False), nullable=False, comment='Статус отображения сообщения'),
        sa.Column('telegram_message_id', sa.BigInteger(), nullable=True, comment='Оригинальный ID сообщения из Telegram'),
        sa.Column('original_timestamp', sa.DateTime(timezone=True), nullable=True, comment='Оригинальное время отправки в Telegram'),
        sa.Column('is_filtered', sa.Boolean(), nullable=False, comment='Сообщение отфильтровано модерацией'),
        sa.Column('filter_reason', sa.String(500), nullable=True, comment='Причина фильтрации'),
        sa.Column('is_flagged', sa.Boolean(), nullable=False, comment='Сообщение помечено для проверки'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment='Время получения сообщения'),
        sa.ForeignKeyConstraint(['stream_id'], ['streams.id'], ),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_chat_messages_stream_id', 'chat_messages', ['stream_id'])
    op.create_index('ix_chat_messages_author_id', 'chat_messages', ['author_id'])
    op.create_index('ix_chat_messages_telegram_user_id', 'chat_messages', ['telegram_user_id'])
    op.create_index('ix_chat_messages_stream_status', 'chat_messages', ['stream_id', 'message_status'])
    op.create_index('ix_chat_messages_stream_created', 'chat_messages', ['stream_id', 'created_at'])
    op.create_index('ix_chat_messages_telegram_message_id', 'chat_messages', ['telegram_message_id'])

    # Create shoutouts table
    op.create_table(
        'shoutouts',
        sa.Column('id', src.database.GUID(), nullable=False),
        sa.Column('stream_id', src.database.GUID(), nullable=False),
        sa.Column('triggered_by_id', src.database.GUID(), nullable=True),
        sa.Column('shoutout_type', sa.Enum('new_follower', 'new_subscriber', 'donor', 'top_viewer', 'custom', name='shoutout_type', create_type=False), nullable=False, comment='Тип shoutout'),
        sa.Column('status', sa.Enum('pending', 'displayed', 'skipped', 'cancelled', name='shoutout_status', create_type=False), nullable=False, comment='Текущий статус shoutout'),
        sa.Column('recipient_name', sa.String(255), nullable=False, comment='Имя получателя shoutout'),
        sa.Column('recipient_handle', sa.String(255), nullable=True, comment='Username/handle получателя (опционально)'),
        sa.Column('recipient_avatar_url', sa.String(500), nullable=True, comment='URL аватара получателя (опционально)'),
        sa.Column('title', sa.String(255), nullable=True, comment='Заголовок shoutout (опционально)'),
        sa.Column('message', sa.Text(), nullable=True, comment='Сообщение shoutout (опционально)'),
        sa.Column('display_duration', sa.Integer(), nullable=False, comment='Длительность отображения в секундах'),
        sa.Column('priority', sa.Integer(), nullable=False, comment='Приоритет отображения (higher = раньше)'),
        sa.Column('is_pinned', sa.Boolean(), nullable=False, comment='Закреплен для отображения'),
        sa.Column('trigger_type', sa.String(50), nullable=False, comment='Тип триггера (manual, auto_follower, auto_subscriber, etc.)'),
        sa.Column('trigger_metadata', sa.Text(), nullable=True, comment='JSON метаданные триггера (опционально)'),
        sa.Column('is_filtered', sa.Boolean(), nullable=False, comment='Shoutout отфильтрован модерацией'),
        sa.Column('filter_reason', sa.String(500), nullable=True, comment='Причина фильтрации'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment='Время создания shoutout'),
        sa.Column('displayed_at', sa.DateTime(timezone=True), nullable=True, comment='Время отображения (NULL если не отображался)'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True, comment='Время окончания отображения (NULL = бессрочно)'),
        sa.ForeignKeyConstraint(['stream_id'], ['streams.id'], ),
        sa.ForeignKeyConstraint(['triggered_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_shoutouts_stream_id', 'shoutouts', ['stream_id'])
    op.create_index('ix_shoutouts_triggered_by_id', 'shoutouts', ['triggered_by_id'])
    op.create_index('ix_shoutouts_stream_status', 'shoutouts', ['stream_id', 'status'])
    op.create_index('ix_shoutouts_stream_priority', 'shoutouts', ['stream_id', 'priority'])
    op.create_index('ix_shoutouts_created_at', 'shoutouts', ['created_at'])

    # Create ctas table
    op.create_table(
        'ctas',
        sa.Column('id', src.database.GUID(), nullable=False),
        sa.Column('stream_id', src.database.GUID(), nullable=False),
        sa.Column('created_by_id', src.database.GUID(), nullable=False),
        sa.Column('action_type', sa.Enum('subscribe', 'visit_link', 'donate', 'follow_social', 'join_group', 'custom', name='cta_action_type', create_type=False), nullable=False, comment='Тип действия CTA'),
        sa.Column('status', sa.Enum('draft', 'scheduled', 'active', 'paused', 'completed', 'expired', name='cta_status', create_type=False), nullable=False, comment='Текущий статус CTA'),
        sa.Column('title', sa.String(255), nullable=False, comment='Заголовок CTA'),
        sa.Column('message', sa.Text(), nullable=True, comment='Сообщение CTA (опционально)'),
        sa.Column('action_url', sa.String(1000), nullable=True, comment='URL для действия (для visit_link, donate, etc.)'),
        sa.Column('button_text', sa.String(100), nullable=False, comment='Текст на кнопке действия'),
        sa.Column('button_color', sa.String(20), nullable=True, comment='Цвет кнопки (hex код, опционально)'),
        sa.Column('is_dismissable', sa.Boolean(), nullable=False, comment='Можно ли закрыть CTA'),
        sa.Column('display_duration', sa.Integer(), nullable=True, comment='Длительность отображения в секундах (NULL = пока не закроют)'),
        sa.Column('position', sa.String(50), nullable=False, comment='Позиция на overlay (top-left, top-right, bottom-left, bottom-right, center)'),
        sa.Column('priority', sa.Integer(), nullable=False, comment='Приоритет отображения (higher = раньше)'),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True, comment='Запланированное время отображения (NULL = немедленно)'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True, comment='Время окончания действия (NULL = бессрочно)'),
        sa.Column('display_count', sa.Integer(), nullable=False, comment='Сколько раз отображался'),
        sa.Column('dismiss_count', sa.Integer(), nullable=False, comment='Сколько раз закрыли'),
        sa.Column('click_count', sa.Integer(), nullable=False, comment='Сколько раз кликнули'),
        sa.Column('conversion_rate', sa.Integer(), nullable=True, comment='Коэффициент конверсии в % (clicks / displays * 100)'),
        sa.Column('is_filtered', sa.Boolean(), nullable=False, comment='CTA отфильтрован модерацией'),
        sa.Column('filter_reason', sa.String(500), nullable=True, comment='Причина фильтрации'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment='Время создания CTA'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment='Время последнего обновления'),
        sa.ForeignKeyConstraint(['stream_id'], ['streams.id'], ),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ctas_stream_id', 'ctas', ['stream_id'])
    op.create_index('ix_ctas_created_by_id', 'ctas', ['created_by_id'])
    op.create_index('ix_ctas_stream_status', 'ctas', ['stream_id', 'status'])
    op.create_index('ix_ctas_scheduled_at', 'ctas', ['scheduled_at'])
    op.create_index('ix_ctas_expires_at', 'ctas', ['expires_at'])


def downgrade() -> None:
    # Drop tables in reverse order due to foreign key constraints
    op.drop_index('ix_ctas_expires_at', table_name='ctas')
    op.drop_index('ix_ctas_scheduled_at', table_name='ctas')
    op.drop_index('ix_ctas_stream_status', table_name='ctas')
    op.drop_index('ix_ctas_created_by_id', table_name='ctas')
    op.drop_index('ix_ctas_stream_id', table_name='ctas')
    op.drop_table('ctas')

    op.drop_index('ix_shoutouts_created_at', table_name='shoutouts')
    op.drop_index('ix_shoutouts_stream_priority', table_name='shoutouts')
    op.drop_index('ix_shoutouts_stream_status', table_name='shoutouts')
    op.drop_index('ix_shoutouts_triggered_by_id', table_name='shoutouts')
    op.drop_index('ix_shoutouts_stream_id', table_name='shoutouts')
    op.drop_table('shoutouts')

    op.drop_index('ix_chat_messages_telegram_message_id', table_name='chat_messages')
    op.drop_index('ix_chat_messages_stream_created', table_name='chat_messages')
    op.drop_index('ix_chat_messages_stream_status', table_name='chat_messages')
    op.drop_index('ix_chat_messages_telegram_user_id', table_name='chat_messages')
    op.drop_index('ix_chat_messages_author_id', table_name='chat_messages')
    op.drop_index('ix_chat_messages_stream_id', table_name='chat_messages')
    op.drop_table('chat_messages')

    op.drop_index('ix_emoji_reactions_expires_at', table_name='emoji_reactions')
    op.drop_index('ix_emoji_reactions_stream_created', table_name='emoji_reactions')
    op.drop_index('ix_emoji_reactions_stream_status', table_name='emoji_reactions')
    op.drop_index('ix_emoji_reactions_telegram_user_id', table_name='emoji_reactions')
    op.drop_index('ix_emoji_reactions_user_id', table_name='emoji_reactions')
    op.drop_index('ix_emoji_reactions_stream_id', table_name='emoji_reactions')
    op.drop_table('emoji_reactions')

    op.drop_index('ix_question_upvotes_created_at', table_name='question_upvotes')
    op.drop_index('ix_question_upvotes_question_telegram', table_name='question_upvotes')
    op.drop_index('ix_question_upvotes_question_user', table_name='question_upvotes')
    op.drop_index('ix_question_upvotes_telegram_user_id', table_name='question_upvotes')
    op.drop_index('ix_question_upvotes_user_id', table_name='question_upvotes')
    op.drop_index('ix_question_upvotes_question_id', table_name='question_upvotes')
    op.drop_table('question_upvotes')

    op.drop_index('ix_questions_created_at', table_name='questions')
    op.drop_index('ix_questions_stream_upvotes', table_name='questions')
    op.drop_index('ix_questions_stream_status', table_name='questions')
    op.drop_index('ix_questions_telegram_user_id', table_name='questions')
    op.drop_index('ix_questions_author_id', table_name='questions')
    op.drop_index('ix_questions_stream_id', table_name='questions')
    op.drop_table('questions')

    op.drop_index('ix_poll_votes_poll_telegram', table_name='poll_votes')
    op.drop_index('ix_poll_votes_poll_user', table_name='poll_votes')
    op.drop_index('ix_poll_votes_telegram_user_id', table_name='poll_votes')
    op.drop_index('ix_poll_votes_user_id', table_name='poll_votes')
    op.drop_index('ix_poll_votes_option_id', table_name='poll_votes')
    op.drop_index('ix_poll_votes_poll_id', table_name='poll_votes')
    op.drop_table('poll_votes')

    op.drop_index('ix_poll_options_poll_order', table_name='poll_options')
    op.drop_index('ix_poll_options_poll_id', table_name='poll_options')
    op.drop_table('poll_options')

    op.drop_index('ix_polls_owner_id', table_name='polls')
    op.drop_table('polls')

    # Drop ENUM types
    sa.Enum(name='cta_status').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='cta_action_type').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='shoutout_status').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='shoutout_type').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='chat_message_status').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='reaction_display_status').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='question_status').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='poll_status').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='poll_type').drop(op.get_bind(), checkfirst=True)
