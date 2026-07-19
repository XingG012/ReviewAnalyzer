"""add GIN index on tagged_reviews.tags

Revision ID: 48995661cf26
Revises: 265ebd4aa3a1
Create Date: 2026-07-19 09:19:20.338140

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "48995661cf26"
down_revision: str | Sequence[str] | None = "265ebd4aa3a1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建 GIN 索引，加速 JSONB tags 字段查询"""
    op.create_index(
        "idx_tagged_tags",
        "tagged_reviews",
        ["tags"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    """删除 GIN 索引"""
    op.drop_index("idx_tagged_tags", table_name="tagged_reviews")
