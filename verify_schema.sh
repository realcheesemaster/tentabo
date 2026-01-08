#!/bin/bash
# Quick schema verification script

echo "=========================================="
echo "TENTABO PRM - Schema Verification"
echo "=========================================="
echo ""

echo "1. Testing database connection..."
python3 -c "from app.database import engine; from sqlalchemy import text; conn = engine.connect(); result = conn.execute(text('SELECT version()')); print('   ✓ Connected:', result.fetchone()[0][:60]); conn.close()" 2>/dev/null && echo "   ✓ Connection successful" || echo "   ✗ Connection failed"

echo ""
echo "2. Checking tables..."
python3 -c "from sqlalchemy import inspect; from app.database import engine; tables = inspect(engine).get_table_names(); print(f'   ✓ {len(tables)} tables found')"

echo ""
echo "3. Checking migration status..."
python3 -m alembic current 2>/dev/null | grep -q "a8e2b505fe67" && echo "   ✓ Migration applied: a8e2b505fe67" || echo "   ! Migration check failed"

echo ""
echo "4. Sample data check..."
python3 -c "
from app.database import SessionLocal
from app.models import AdminUser, Product, Partner, Distributor
db = SessionLocal()
counts = {
    'Admin Users': db.query(AdminUser).count(),
    'Products': db.query(Product).count(),
    'Partners': db.query(Partner).count(),
    'Distributors': db.query(Distributor).count(),
}
for name, count in counts.items():
    print(f'   {name}: {count} records')
db.close()
"

echo ""
echo "=========================================="
echo "Schema verification complete!"
echo "Run 'python3 test_schema.py' for full tests"
echo "=========================================="
