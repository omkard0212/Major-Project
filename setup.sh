#!/bin/bash
echo "============================================"
echo "  ArthSathi - First Time Setup"
echo "============================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found. Install it first:"
    echo "  Ubuntu/Debian: sudo apt install python3 python3-pip"
    echo "  Mac: brew install python3"
    exit 1
fi
echo "[OK] Python3 found."

# Install packages
echo ""
echo "Installing Python packages..."
pip3 install -r requirements.txt --quiet
echo "[OK] Packages installed."

# Create .env if not exists
if [ ! -f "backend/config/.env" ]; then
    cp backend/config/.env.example backend/config/.env
    sed -i 's/your_postgres_password_here/postgres/' backend/config/.env
    sed -i 's/your_secret_key_here/arthsathi_secret_key_2026/' backend/config/.env
    echo "[OK] .env file created."
else
    echo "[OK] .env already exists."
fi

# Create database
echo ""
echo "Setting up database..."
PGPASSWORD=postgres psql -U postgres -c "CREATE DATABASE arthsathi;" 2>/dev/null
PGPASSWORD=postgres psql -U postgres -d arthsathi -f database/schema.sql 2>/dev/null
echo "[OK] Database ready."

# Process dataset
if [ ! -f "ml-model/schemes_processed.csv" ]; then
    echo ""
    echo "Processing schemes dataset..."
    cd ml-model && python3 parse_schemes.py && cd ..
    echo "[OK] Dataset processed."
fi

echo ""
echo "============================================"
echo "  Setup Complete! Run ./start.sh to launch."
echo "============================================"
