"""Add recursive user groups and extend server groups

Revision ID: 16fef1ee2380
Revises: 8419b886bc6d
Create Date: 2026-01-05 10:42:11.172694

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '16fef1ee2380'
down_revision: Union[str, Sequence[str], None] = '8419b886bc6d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create user_groups table
    op.create_table('user_groups',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('parent_group_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['parent_group_id'], ['user_groups.id'], ondelete='SET NULL'),
        sa.CheckConstraint('id != parent_group_id', name='user_groups_no_self_reference')
    )
    
    # Create user_group_members table
    op.create_table('user_group_members',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_group_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('added_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['user_group_id'], ['user_groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_group_id', 'user_id', name='user_group_members_unique')
    )
    
    # Extend server_groups with parent_group_id for recursion
    op.add_column('server_groups', sa.Column('parent_group_id', sa.Integer(), nullable=True))
    op.create_foreign_key('server_groups_parent_fk', 'server_groups', 'server_groups', 
                         ['parent_group_id'], ['id'], ondelete='SET NULL')
    op.create_check_constraint('server_groups_no_self_reference', 'server_groups', 
                              'id != parent_group_id')
    
    # Extend access_policies with user_group_id
    op.add_column('access_policies', sa.Column('user_group_id', sa.Integer(), nullable=True))
    op.create_foreign_key('access_policies_user_group_fk', 'access_policies', 'user_groups',
                         ['user_group_id'], ['id'], ondelete='CASCADE')
    
    # Add port_forwarding_allowed to users
    op.add_column('users', sa.Column('port_forwarding_allowed', sa.Boolean(), 
                                     server_default=sa.false(), nullable=False))
    
    # Add port_forwarding_allowed to user_groups
    op.add_column('user_groups', sa.Column('port_forwarding_allowed', sa.Boolean(),
                                           server_default=sa.false(), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove port_forwarding_allowed from user_groups
    op.drop_column('user_groups', 'port_forwarding_allowed')
    
    # Remove port_forwarding_allowed from users
    op.drop_column('users', 'port_forwarding_allowed')
    
    # Remove user_group_id from access_policies
    op.drop_constraint('access_policies_user_group_fk', 'access_policies', type_='foreignkey')
    op.drop_column('access_policies', 'user_group_id')
    
    # Remove parent_group_id from server_groups
    op.drop_constraint('server_groups_no_self_reference', 'server_groups', type_='check')
    op.drop_constraint('server_groups_parent_fk', 'server_groups', type_='foreignkey')
    op.drop_column('server_groups', 'parent_group_id')
    
    # Drop user_group_members table
    op.drop_table('user_group_members')
    
    # Drop user_groups table
    op.drop_table('user_groups')
