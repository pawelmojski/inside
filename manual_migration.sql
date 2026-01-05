-- Manual migration: recursive groups
BEGIN;

-- Create user_groups table
CREATE TABLE IF NOT EXISTS user_groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    parent_group_id INTEGER REFERENCES user_groups(id) ON DELETE SET NULL,
    port_forwarding_allowed BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT user_groups_no_self_reference CHECK (id != parent_group_id)
);

CREATE INDEX IF NOT EXISTS ix_user_groups_parent_group_id ON user_groups(parent_group_id);

-- Create user_group_members table
CREATE TABLE IF NOT EXISTS user_group_members (
    id SERIAL PRIMARY KEY,
    user_group_id INTEGER NOT NULL REFERENCES user_groups(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    added_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT user_group_members_unique UNIQUE (user_group_id, user_id)
);

CREATE INDEX IF NOT EXISTS ix_user_group_members_user_id ON user_group_members(user_id);
CREATE INDEX IF NOT EXISTS ix_user_group_members_group_id ON user_group_members(user_group_id);

-- Extend server_groups with parent_group_id
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='server_groups' AND column_name='parent_group_id') THEN
        ALTER TABLE server_groups ADD COLUMN parent_group_id INTEGER REFERENCES server_groups(id) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints WHERE constraint_name='server_groups_no_self_reference') THEN
        ALTER TABLE server_groups ADD CONSTRAINT server_groups_no_self_reference CHECK (id != parent_group_id);
    END IF;
END $$;
CREATE INDEX IF NOT EXISTS ix_server_groups_parent_group_id ON server_groups(parent_group_id);

-- Extend access_policies with user_group_id
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='access_policies' AND column_name='user_group_id') THEN
        ALTER TABLE access_policies ADD COLUMN user_group_id INTEGER REFERENCES user_groups(id) ON DELETE CASCADE;
    END IF;
END $$;
CREATE INDEX IF NOT EXISTS ix_access_policies_user_group_id ON access_policies(user_group_id);

-- Add port_forwarding_allowed to users
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='users' AND column_name='port_forwarding_allowed') THEN
        ALTER TABLE users ADD COLUMN port_forwarding_allowed BOOLEAN NOT NULL DEFAULT false;
    END IF;
END $$;

-- Update alembic version
UPDATE alembic_version SET version_num = '16fef1ee2380' WHERE version_num = '8419b886bc6d';

COMMIT;
