#!/bin/bash

# Test PostgreSQL connection for Tentabo PRM
echo "🔍 Testing PostgreSQL connection to marshmallow02.oxileo.net..."
echo "=================================================="

# Database credentials
export PGHOST="marshmallow02.oxileo.net"
export PGPORT="5432"
export PGDATABASE="tentabo_oxibox"
export PGUSER="tentabo_oxibox"
export PGPASSWORD='CN1IdxkA^waY9tVdEivk%2Q&fpQWA4y!'

# Test with psql (if installed)
if command -v psql &> /dev/null; then
    echo "📊 Using psql to test connection..."
    psql -c "SELECT version();" -c "SELECT current_database();" -c "SELECT current_user;"

    if [ $? -eq 0 ]; then
        echo "✅ psql connection successful!"
    else
        echo "❌ psql connection failed!"
    fi
else
    echo "⚠️  psql not found, using Python script instead..."
fi

# Test with Python script
if command -v python3 &> /dev/null; then
    echo ""
    echo "🐍 Testing with Python psycopg2..."
    echo "=================================================="

    # Install psycopg2 if needed
    pip3 install psycopg2-binary --quiet 2>/dev/null || pip install psycopg2-binary --quiet 2>/dev/null

    python3 test_db_connection.py

    if [ $? -eq 0 ]; then
        echo "✅ Python connection test successful!"
    else
        echo "❌ Python connection test failed!"
    fi
else
    echo "❌ Python not found. Please install Python 3 to run the test script."
fi