#!/bin/bash
# Remote script to create test database on VPS

DB_NAME="sattva_test_db"
DB_USER="sattva_test"
DB_PASSWORD="TestPassword2024Secure"

echo "Creating test database..."

# Create user
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>&1 | head -1

# Create database  
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>&1 | head -1

# Grant privileges
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
sudo -u postgres psql -d $DB_NAME -c "GRANT ALL ON SCHEMA public TO $DB_USER;"

echo "Test DB ready: postgresql://$DB_USER:$DB_PASSWORD@10.99.99.6:5432/$DB_NAME"
