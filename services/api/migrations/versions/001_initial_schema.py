"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create flashback_scene table
    op.create_table(
        'flashback_scene',
        sa.Column('scene_id', sa.String(255), primary_key=True),
        sa.Column('date', sa.String(10), nullable=False, index=True),
        sa.Column('lang', sa.String(10), nullable=False, server_default='en'),
        sa.Column('event_title', sa.String(500), nullable=False),
        sa.Column('event_year', sa.Integer(), nullable=True),
        sa.Column('event_summary', sa.Text(), nullable=False),
        sa.Column('event_summary_source_text', sa.Text(), nullable=False),
        sa.Column('wikipedia_url', sa.String(1000), nullable=False),
        sa.Column('wikidata_qid', sa.String(20), nullable=True),
        sa.Column('rank_signals', sa.JSON(), nullable=True),
        sa.Column('scene_spec', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )

    # Create flashback_asset table
    op.create_table(
        'flashback_asset',
        sa.Column('asset_id', sa.String(255), primary_key=True),
        sa.Column('scene_id', sa.String(255), sa.ForeignKey('flashback_scene.scene_id'), nullable=False),
        sa.Column('lens_id', sa.Integer(), nullable=False),
        sa.Column('lens_name', sa.String(50), nullable=False),
        sa.Column('image_url', sa.String(1000), nullable=True),
        sa.Column('prompt_used', sa.Text(), nullable=True),
        sa.Column('qc_result', sa.JSON(), nullable=True),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )

    # Create user_usage table
    op.create_table(
        'user_usage',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.String(255), nullable=False, index=True),
        sa.Column('week_start', sa.String(10), nullable=False),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_pro', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
    )

    # Create indexes
    op.create_index('ix_flashback_asset_scene_id', 'flashback_asset', ['scene_id'])
    op.create_index('ix_user_usage_week', 'user_usage', ['user_id', 'week_start'])


def downgrade() -> None:
    op.drop_index('ix_user_usage_week', 'user_usage')
    op.drop_index('ix_flashback_asset_scene_id', 'flashback_asset')
    op.drop_table('user_usage')
    op.drop_table('flashback_asset')
    op.drop_table('flashback_scene')
