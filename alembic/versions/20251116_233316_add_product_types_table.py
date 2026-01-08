"""add product_types table and update products

Revision ID: 20251116233316
Revises: 2919e6e03409
Create Date: 2025-11-16 23:33:16

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251116233316'
down_revision = '2919e6e03409'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create product_types table
    op.create_table(
        'product_types',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index(op.f('ix_product_types_name'), 'product_types', ['name'], unique=False)
    op.create_index(op.f('ix_product_types_is_active'), 'product_types', ['is_active'], unique=False)

    # Insert default product types based on existing product types in the database
    # First, get unique types from products table and create product_types for them
    op.execute("""
        INSERT INTO product_types (name, description, is_active, created_at, updated_at)
        SELECT DISTINCT
            type as name,
            'Migrated from existing products' as description,
            true as is_active,
            now() as created_at,
            now() as updated_at
        FROM products
        WHERE type IS NOT NULL AND type != ''
        ON CONFLICT (name) DO NOTHING;
    """)

    # Add type_id column to products table (nullable initially)
    op.add_column('products', sa.Column('type_id', postgresql.UUID(as_uuid=True), nullable=True))

    # Update products to reference product_types
    op.execute("""
        UPDATE products p
        SET type_id = pt.id
        FROM product_types pt
        WHERE p.type = pt.name;
    """)

    # Now make type_id NOT NULL and add foreign key constraint
    op.alter_column('products', 'type_id', nullable=False)
    op.create_foreign_key('fk_products_type_id', 'products', 'product_types', ['type_id'], ['id'])
    op.create_index(op.f('ix_products_type_id'), 'products', ['type_id'], unique=False)

    # Drop old type column (string)
    op.drop_index('ix_products_type', table_name='products')
    op.drop_column('products', 'type')


def downgrade() -> None:
    # Add back the old type column
    op.add_column('products', sa.Column('type', sa.String(length=100), nullable=True))

    # Populate it from product_types
    op.execute("""
        UPDATE products p
        SET type = pt.name
        FROM product_types pt
        WHERE p.type_id = pt.id;
    """)

    # Make it NOT NULL
    op.alter_column('products', 'type', nullable=False)
    op.create_index('ix_products_type', 'products', ['type'], unique=False)

    # Drop type_id column and constraints
    op.drop_index(op.f('ix_products_type_id'), table_name='products')
    op.drop_constraint('fk_products_type_id', 'products', type_='foreignkey')
    op.drop_column('products', 'type_id')

    # Drop product_types table
    op.drop_index(op.f('ix_product_types_is_active'), table_name='product_types')
    op.drop_index(op.f('ix_product_types_name'), table_name='product_types')
    op.drop_table('product_types')
