"""auth refresh tokens, tool policies, and pgvector retrieval

Revision ID: 0002_auth_pgvector_runtime
Revises: 0001_initial
Create Date: 2026-05-05
"""

from alembic import op

revision = "0002_auth_pgvector_runtime"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS email VARCHAR(255)")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash TEXT")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP")

    op.execute("""
        CREATE TABLE IF NOT EXISTS refresh_tokens (
          id VARCHAR(32) PRIMARY KEY,
          tenant_id VARCHAR(32) NOT NULL,
          user_id VARCHAR(32) NOT NULL REFERENCES users(id),
          token_hash VARCHAR(128) NOT NULL UNIQUE,
          jwt_id VARCHAR(64) NOT NULL UNIQUE,
          expires_at TIMESTAMP NOT NULL,
          revoked_at TIMESTAMP NULL,
          replaced_by_token_id VARCHAR(32) NULL,
          created_at TIMESTAMP,
          updated_at TIMESTAMP
        )
        """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_id ON refresh_tokens(user_id)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_refresh_tokens_tenant_id ON refresh_tokens(tenant_id)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_refresh_tokens_jwt_id ON refresh_tokens(jwt_id)")

    op.execute("ALTER TABLE paper_chunks ADD COLUMN IF NOT EXISTS embedding TEXT")
    op.execute("ALTER TABLE paper_chunks ADD COLUMN IF NOT EXISTS embedding_model VARCHAR(120)")
    if dialect == "postgresql":
        op.execute("""
            ALTER TABLE paper_chunks
            ALTER COLUMN embedding TYPE vector(384)
            USING CASE WHEN embedding IS NULL THEN NULL ELSE embedding::vector END
            """)
        op.execute("""
            ALTER TABLE paper_chunks
            ADD COLUMN IF NOT EXISTS content_tsv tsvector
            GENERATED ALWAYS AS (to_tsvector('english', coalesce(content, ''))) STORED
            """)
        op.execute("""
            CREATE INDEX IF NOT EXISTS ix_paper_chunks_embedding_hnsw
            ON paper_chunks USING hnsw (embedding vector_cosine_ops)
            """)
        op.execute("""
            CREATE INDEX IF NOT EXISTS ix_paper_chunks_content_tsv
            ON paper_chunks USING gin (content_tsv)
            """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS tools (
          id VARCHAR(32) PRIMARY KEY,
          name VARCHAR(120) NOT NULL UNIQUE,
          description TEXT,
          permission_key VARCHAR(120) NOT NULL,
          timeout_seconds INTEGER NOT NULL DEFAULT 15,
          requires_approval BOOLEAN NOT NULL DEFAULT false,
          is_side_effect BOOLEAN NOT NULL DEFAULT false,
          is_active BOOLEAN NOT NULL DEFAULT true,
          created_at TIMESTAMP,
          updated_at TIMESTAMP
        )
        """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS agent_tools (
          id VARCHAR(32) PRIMARY KEY,
          tenant_id VARCHAR(32) NOT NULL,
          agent_id VARCHAR(64) NOT NULL,
          tool_name VARCHAR(120) NOT NULL,
          enabled BOOLEAN NOT NULL DEFAULT true,
          created_at TIMESTAMP,
          updated_at TIMESTAMP
        )
        """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS tool_permissions (
          id VARCHAR(32) PRIMARY KEY,
          role_id VARCHAR(32) NOT NULL REFERENCES roles(id),
          tool_name VARCHAR(120) NOT NULL,
          can_execute BOOLEAN NOT NULL DEFAULT true,
          requires_approval BOOLEAN NOT NULL DEFAULT false,
          created_at TIMESTAMP,
          updated_at TIMESTAMP
        )
        """)

    for table in ("agent_runs", "agent_steps", "tool_invocations"):
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS started_at TIMESTAMP")
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS finished_at TIMESTAMP")
        op.execute(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS latency_ms INTEGER")
    op.execute("ALTER TABLE agent_steps ADD COLUMN IF NOT EXISTS error_message TEXT")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS tool_permissions")
    op.execute("DROP TABLE IF EXISTS agent_tools")
    op.execute("DROP TABLE IF EXISTS tools")
    op.execute("DROP TABLE IF EXISTS refresh_tokens")
