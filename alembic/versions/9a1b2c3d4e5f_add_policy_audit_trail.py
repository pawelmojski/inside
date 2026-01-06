"""Add policy audit trail

Revision ID: 9a1b2c3d4e5f
Revises: 8f3c9a2e1d5b
Create Date: 2026-01-06 18:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '9a1b2c3d4e5f'
down_revision = '8f3c9a2e1d5b'
branch_labels = None
depends_on = None


def upgrade():
    # Add created_by_user_id to access_policies
    op.add_column('access_policies', 
                  sa.Column('created_by_user_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_access_policies_created_by',
                         'access_policies', 'users',
                         ['created_by_user_id'], ['id'])
    
    # Set existing policies to admin (user_id=1)
    op.execute("UPDATE access_policies SET created_by_user_id = 1 WHERE created_by_user_id IS NULL")
    
    # Create policy_audit_log table for full change tracking
    op.create_table('policy_audit_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('policy_id', sa.Integer(), nullable=False),
        sa.Column('changed_by_user_id', sa.Integer(), nullable=True),
        sa.Column('change_type', sa.String(length=50), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=True),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('full_old_state', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('full_new_state', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['policy_id'], ['access_policies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changed_by_user_id'], ['users.id'], )
    )
    op.create_index('idx_policy_audit_log_policy_id', 'policy_audit_log', ['policy_id'])
    op.create_index('idx_policy_audit_log_changed_at', 'policy_audit_log', ['changed_at'])
    op.create_index('idx_policy_audit_log_change_type', 'policy_audit_log', ['change_type'])


def downgrade():
    op.drop_index('idx_policy_audit_log_change_type', table_name='policy_audit_log')
    op.drop_index('idx_policy_audit_log_changed_at', table_name='policy_audit_log')
    op.drop_index('idx_policy_audit_log_policy_id', table_name='policy_audit_log')
    op.drop_table('policy_audit_log')
    op.drop_constraint('fk_access_policies_created_by', 'access_policies', type_='foreignkey')
    op.drop_column('access_policies', 'created_by_user_id')
