#!/bin/bash
# Check database connectivity

echo "=========================================="
echo "Database Connectivity Check"
echo "=========================================="
echo ""

# 1. Check if PostgreSQL container is running
echo "1. Checking PostgreSQL container:"
docker compose ps postgres
echo ""

# 2. Check PostgreSQL logs
echo "2. Recent PostgreSQL logs:"
docker compose logs postgres --tail 10
echo ""

# 3. Test connection from dashboard container
echo "3. Testing connection from dashboard container:"
docker compose exec dashboard python3 -c "
import psycopg2
import os
try:
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'postgres'),
        port=int(os.getenv('POSTGRES_PORT', 5432)),
        database=os.getenv('POSTGRES_DB', 'arbitrage_bot'),
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD', '')
    )
    print('✓ Database connection successful!')
    conn.close()
except Exception as e:
    print(f'✗ Database connection failed: {e}')
"
echo ""

# 4. Check environment variables
echo "4. Checking environment variables:"
docker compose exec dashboard env | grep POSTGRES
echo ""

# 5. Check if database is ready
echo "5. Checking if PostgreSQL is ready:"
docker compose exec postgres pg_isready -U postgres
echo ""

echo "=========================================="
echo "If database is not connecting:"
echo "1. Check .env file has correct POSTGRES_* variables"
echo "2. Restart PostgreSQL: docker compose restart postgres"
echo "3. Wait 30 seconds for PostgreSQL to initialize"
echo "4. Restart dashboard: docker compose restart dashboard"
echo "=========================================="

