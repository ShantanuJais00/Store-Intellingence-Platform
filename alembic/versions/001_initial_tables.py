"""initial_tables

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
    op.create_table('stores',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('store_id', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('zones', sa.JSON(), nullable=True),
        sa.Column('cameras', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('store_id')
    )
    op.create_table('events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('event_id', sa.String(length=36), nullable=False),
        sa.Column('store_id', sa.String(length=20), nullable=False),
        sa.Column('camera_id', sa.String(length=20), nullable=True),
        sa.Column('visitor_id', sa.String(length=50), nullable=True),
        sa.Column('event_type', sa.String(length=30), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('zone_id', sa.String(length=50), nullable=True),
        sa.Column('dwell_ms', sa.Integer(), nullable=True),
        sa.Column('is_staff', sa.Boolean(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_events_event_id'), 'events', ['event_id'], unique=True)
    op.create_index(op.f('ix_events_event_type'), 'events', ['event_type'], unique=False)
    op.create_index(op.f('ix_events_store_id'), 'events', ['store_id'], unique=False)
    op.create_index(op.f('ix_events_timestamp'), 'events', ['timestamp'], unique=False)
    op.create_index(op.f('ix_events_visitor_id'), 'events', ['visitor_id'], unique=False)
    
    op.create_table('sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('store_id', sa.String(length=20), nullable=False),
        sa.Column('visitor_id', sa.String(length=50), nullable=False),
        sa.Column('entry_time', sa.DateTime(), nullable=False),
        sa.Column('exit_time', sa.DateTime(), nullable=True),
        sa.Column('is_reentry', sa.Boolean(), nullable=True),
        sa.Column('is_staff', sa.Boolean(), nullable=True),
        sa.Column('converted', sa.Boolean(), nullable=True),
        sa.Column('total_dwell_ms', sa.Integer(), nullable=True),
        sa.Column('zones_visited', sa.JSON(), nullable=True),
        sa.Column('transaction_id', sa.String(length=36), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id')
    )
    op.create_index(op.f('ix_sessions_store_id'), 'sessions', ['store_id'], unique=False)
    
    op.create_table('transactions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('transaction_id', sa.String(length=36), nullable=False),
        sa.Column('store_id', sa.String(length=20), nullable=False),
        sa.Column('order_id', sa.String(length=20), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('product_id', sa.String(length=20), nullable=True),
        sa.Column('brand_name', sa.String(length=100), nullable=True),
        sa.Column('total_amount', sa.Float(), nullable=True),
        sa.Column('matched_visitor_id', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('transaction_id')
    )
    op.create_index(op.f('ix_transactions_store_id'), 'transactions', ['store_id'], unique=False)
    
    op.create_table('anomalies',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('anomaly_id', sa.String(length=36), nullable=False),
        sa.Column('store_id', sa.String(length=20), nullable=False),
        sa.Column('anomaly_type', sa.String(length=30), nullable=False),
        sa.Column('severity', sa.String(length=10), nullable=False),
        sa.Column('message', sa.String(length=500), nullable=True),
        sa.Column('suggested_action', sa.String(length=500), nullable=True),
        sa.Column('detected_at', sa.DateTime(), nullable=False),
        sa.Column('resolved', sa.Boolean(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('anomaly_id')
    )
    op.create_index(op.f('ix_anomalies_store_id'), 'anomalies', ['store_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_anomalies_store_id'), table_name='anomalies')
    op.drop_table('anomalies')
    op.drop_index(op.f('ix_transactions_store_id'), table_name='transactions')
    op.drop_table('transactions')
    op.drop_index(op.f('ix_sessions_store_id'), table_name='sessions')
    op.drop_table('sessions')
    op.drop_index(op.f('ix_events_visitor_id'), table_name='events')
    op.drop_index(op.f('ix_events_timestamp'), table_name='events')
    op.drop_index(op.f('ix_events_store_id'), table_name='events')
    op.drop_index(op.f('ix_events_event_type'), table_name='events')
    op.drop_index(op.f('ix_events_event_id'), table_name='events')
    op.drop_table('events')
    op.drop_table('stores')
