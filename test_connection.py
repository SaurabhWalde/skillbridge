"""
Quick test — does your DATABASE_URL actually work?
Run: python test_connection.py
"""

import os
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("DATABASE_URL")
print(f"📋 DATABASE_URL = {url[:50]}...") if url and len(url) > 50 else print(f"📋 DATABASE_URL = {url}")

if not url:
    print("❌ DATABASE_URL is not set in .env file!")
    print("   Create a .env file with: DATABASE_URL=postgresql://...")
    exit(1)

# Test 1: Can we resolve the hostname?
print("\n🔍 Test 1: DNS resolution...")
try:
    from urllib.parse import urlparse
    import socket
    parsed = urlparse(url)
    hostname = parsed.hostname
    print(f"   Hostname: {hostname}")
    ip = socket.gethostbyname(hostname)
    print(f"   ✅ Resolved to: {ip}")
except Exception as e:
    print(f"   ❌ DNS failed: {e}")
    print("\n   FIX: Check your internet connection or DNS settings")
    print("   TRY: Use mobile hotspot, or change DNS to 8.8.8.8")
    exit(1)

# Test 2: Can we connect to the database?
print("\n🔍 Test 2: Database connection...")
try:
    from sqlalchemy import create_engine, text
    engine = create_engine(url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        print(f"   ✅ Database connected! SELECT 1 = {result.scalar()}")
except Exception as e:
    print(f"   ❌ Connection failed: {e}")
    print("\n   FIX: Check your DATABASE_URL credentials")
    print("   TRY: Go to neon.tech → Connection Details → copy the pooled URL")
    exit(1)

print("\n🎉 Everything works! You can now run: python run.py")