"""Add Gate and Stay models for distributed architecture

- Add Gate model (data plane registration & heartbeat tracking)
- Add Stay model (period of being inside, multiple sessions per stay)
- Add Session.stay_id FK (link session to parent stay)
- Add Session.gate_id FK (track which gate handled session)
- Add SessionRecording.gate_id FK
- Backward compatible: stay_id and gate_id nullable

Revision ID: c50921c6cc09
Revises: 9a1b2c3d4e5f
Create Date: 2026-01-07 10:00:53.761998

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c50921c6cc09'
down_revision: Union[str, Sequence[str], None] = '9a1b2c3d4e5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add Gate and Stay models."""
    # Create gates table
    op.create_table('gates',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('hostname', sa.String(length=255), nullable=False),
    sa.Column('api_token', sa.String(length=255), nullable=False),
    sa.Column('location', sa.String(length=255), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('last_heartbeat', sa.DateTime(), nullable=True),
    sa.Column('version', sa.String(length=50), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('api_token')
    )
    op.create_index(op.f('ix_gates_id'), 'gates', ['id'], unique=False)
    op.create_index(op.f('ix_gates_name'), 'gates', ['name'], unique=True)
    
    # Create stays table
    op.create_table('stays',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('policy_id', sa.Integer(), nullable=False),
    sa.Column('gate_id', sa.Integer(), nullable=True),
    sa.Column('server_id', sa.Integer(), nullable=False),
    sa.Column('started_at', sa.DateTime(), nullable=False),
    sa.Column('ended_at', sa.DateTime(), nullable=True),
    sa.Column('duration_seconds', sa.Integer(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('termination_reason', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['gate_id'], ['gates.id'], ),
    sa.ForeignKeyConstraint(['policy_id'], ['access_policies.id'], ),
    sa.ForeignKeyConstraint(['server_id'], ['servers.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stays_ended_at'), 'stays', ['ended_at'], unique=False)
    op.create_index(op.f('ix_stays_gate_id'), 'stays', ['gate_id'], unique=False)
    op.create_index(op.f('ix_stays_id'), 'stays', ['id'], unique=False)
    op.create_index(op.f('ix_stays_is_active'), 'stays', ['is_active'], unique=False)
    op.create_index(op.f('ix_stays_policy_id'), 'stays', ['policy_id'], unique=False)
    op.create_index(op.f('ix_stays_server_id'), 'stays', ['server_id'], unique=False)
    op.create_index(op.f('ix_stays_started_at'), 'stays', ['started_at'], unique=False)
    op.create_index(op.f('ix_stays_user_id'), 'stays', ['user_id'], unique=False)
    
    # Add gate_id to session_recordings
    op.add_column('session_recordings', sa.Column('gate_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'session_recordings', 'gates', ['gate_id'], ['id'])
    
    # Add stay_id and gate_id to sessions
    op.add_column('sessions', sa.Column('stay_id', sa.Integer(), nullable=True))
    op.add_column('sessions', sa.Column('gate_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_sessions_gate_id'), 'sessions', ['gate_id'], unique=False)
    op.create_index(op.f('ix_sessions_stay_id'), 'sessions', ['stay_id'], unique=False)
    op.create_foreign_key(None, 'sessions', 'gates', ['gate_id'], ['id'])
    op.create_foreign_key(None, 'sessions', 'stays', ['stay_id'], ['id'])
    
    # Insert default gate (localhost)
    op.execute("""
        INSERT INTO gates (name, hostname, api_token, status, is_active, created_at, updated_at)
        VALUES ('gate-localhost', 'localhost', 'localhost-default-token-changeme', 'online', true, NOW(), NOW())
    """)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema - remove Gate and Stay models."""
    # Drop foreign keys and columns from sessions
    op.drop_constraint(None, 'sessions', type_='foreignkey')
    op.drop_constraint(None, 'sessions', type_='foreignkey')
    op.drop_index(op.f('ix_sessions_stay_id'), table_name='sessions')
    op.drop_index(op.f('ix_sessions_gate_id'), table_name='sessions')
    op.drop_column('sessions', 'gate_id')
    op.drop_column('sessions', 'stay_id')
    
    # Drop gate_id from session_recordings
    op.drop_constraint(None, 'session_recordings', type_='foreignkey')
    op.drop_column('session_recordings', 'gate_id')
    
    # Drop stays table
    op.drop_index(op.f('ix_stays_user_id'), table_name='stays')
    op.drop_index(op.f('ix_stays_started_at'), table_name='stays')
    op.drop_index(op.f('ix_stays_server_id'), table_name='stays')
    op.drop_index(op.f('ix_stays_policy_id'), table_name='stays')
    op.drop_index(op.f('ix_stays_is_active'), table_name='stays')
    op.drop_index(op.f('ix_stays_id'), table_name='stays')
    op.drop_index(op.f('ix_stays_gate_id'), table_name='stays')
    op.drop_index(op.f('ix_stays_ended_at'), table_name='stays')
    op.drop_table('stays')
    
    # Drop gates table
    op.drop_index(op.f('ix_gates_name'), table_name='gates')
    op.drop_index(op.f('ix_gates_id'), table_name='gates')
    op.drop_table('gates')
