"""add_recommendation_tables

Revision ID: o2p3q4r5s6t7
Revises: n1o2p3q4r5s6
Create Date: 2025-01-23 12:00:00.000000

Добавляет таблицы для системы рекомендаций:
- recommendations: AI-генерируемые рекомендации для пользователей
- recommendation_feedback: обратная связь пользователей (лайки/дизлайки)
- user_item_interactions: данные для коллаборативной фильтрации
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'o2p3q4r5s6t7'
down_revision: Union[str, None] = 'n1o2p3q4r5s6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create recommendations table
    op.create_table(
        'recommendations',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('playlist_item_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('algorithm', sa.String(), nullable=False, comment='collaborative_filtering, content_based, hybrid'),
        sa.Column('score', sa.Numeric(5, 4), nullable=False, comment='Уверенность рекомендации от 0 до 1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['playlist_item_id'], ['playlist_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_recommendations_user_id', 'recommendations', ['user_id'])
    op.create_index('idx_recommendations_playlist_item_id', 'recommendations', ['playlist_item_id'])
    op.create_index('idx_recommendations_score', 'recommendations', ['score'])
    op.create_index('idx_recommendations_created_at', 'recommendations', ['created_at'])

    # Create recommendation_feedback table
    op.create_table(
        'recommendation_feedback',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('playlist_item_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('feedback_type', sa.String(10), nullable=False, comment='like или dislike'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['playlist_item_id'], ['playlist_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'playlist_item_id', name='uq_recommendation_feedback_user_item')
    )
    op.create_index('idx_recommendation_feedback_user_id', 'recommendation_feedback', ['user_id'])
    op.create_index('idx_recommendation_feedback_playlist_item_id', 'recommendation_feedback', ['playlist_item_id'])
    op.create_index('idx_recommendation_feedback_feedback_type', 'recommendation_feedback', ['feedback_type'])
    op.create_index('idx_recommendation_feedback_created_at', 'recommendation_feedback', ['created_at'])
    op.create_check_constraint(
        'ck_recommendation_feedback_type',
        'recommendation_feedback',
        "feedback_type IN ('like', 'dislike')"
    )

    # Create user_item_interactions table
    op.create_table(
        'user_item_interactions',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('playlist_item_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('interaction_type', sa.String(20), nullable=False, comment='Тип взаимодействия'),
        sa.Column('duration_seconds', sa.BigInteger(), nullable=True, comment='Длительность просмотра в секундах'),
        sa.Column('completion_rate', sa.Numeric(5, 4), nullable=True, comment='Доля просмотра от 0 до 1'),
        sa.Column('interacted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('metadata', sa.String(), nullable=True, comment='Дополнительные метаданные в формате JSON'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['playlist_item_id'], ['playlist_items.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_user_item_interactions_user_id', 'user_item_interactions', ['user_id'])
    op.create_index('idx_user_item_interactions_playlist_item_id', 'user_item_interactions', ['playlist_item_id'])
    op.create_index('idx_user_item_interactions_interaction_type', 'user_item_interactions', ['interaction_type'])
    op.create_index('idx_user_item_interactions_interacted_at', 'user_item_interactions', ['interacted_at'])
    op.create_index('idx_user_item_interactions_user_item', 'user_item_interactions', ['user_id', 'playlist_item_id'])
    op.create_check_constraint(
        'ck_user_item_interactions_type',
        'user_item_interactions',
        "interaction_type IN ('watch', 'skip', 'like', 'share', 'click')"
    )
    op.create_check_constraint(
        'ck_user_item_interactions_completion_rate',
        'user_item_interactions',
        "completion_rate IS NULL OR (completion_rate >= 0 AND completion_rate <= 1)"
    )


def downgrade() -> None:
    # Drop user_item_interactions
    op.drop_constraint('ck_user_item_interactions_completion_rate', 'user_item_interactions')
    op.drop_constraint('ck_user_item_interactions_type', 'user_item_interactions')
    op.drop_index('idx_user_item_interactions_user_item', table_name='user_item_interactions')
    op.drop_index('idx_user_item_interactions_interacted_at', table_name='user_item_interactions')
    op.drop_index('idx_user_item_interactions_interaction_type', table_name='user_item_interactions')
    op.drop_index('idx_user_item_interactions_playlist_item_id', table_name='user_item_interactions')
    op.drop_index('idx_user_item_interactions_user_id', table_name='user_item_interactions')
    op.drop_table('user_item_interactions')

    # Drop recommendation_feedback
    op.drop_constraint('ck_recommendation_feedback_type', 'recommendation_feedback')
    op.drop_index('idx_recommendation_feedback_created_at', table_name='recommendation_feedback')
    op.drop_index('idx_recommendation_feedback_feedback_type', table_name='recommendation_feedback')
    op.drop_index('idx_recommendation_feedback_playlist_item_id', table_name='recommendation_feedback')
    op.drop_index('idx_recommendation_feedback_user_id', table_name='recommendation_feedback')
    op.drop_table('recommendation_feedback')

    # Drop recommendations
    op.drop_index('idx_recommendations_created_at', table_name='recommendations')
    op.drop_index('idx_recommendations_score', table_name='recommendations')
    op.drop_index('idx_recommendations_playlist_item_id', table_name='recommendations')
    op.drop_index('idx_recommendations_user_id', table_name='recommendations')
    op.drop_table('recommendations')
