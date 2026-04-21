"""
Convenience runner:
    python run.py           → Start server
    python run.py seed      → Seed database
    python run.py test      → Run tests
"""

import sys
import subprocess
import uvicorn


def run_server():
    print("🚀 Starting SkillBridge API...")
    print("📄 Docs: http://localhost:8000/docs")
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)


def run_seed():
    print("🌱 Seeding database...")
    subprocess.run([sys.executable, "-m", "src.seed"], check=True)


def run_tests():
    print("🧪 Running tests...")
    subprocess.run([sys.executable, "-m", "pytest", "tests/test_api.py", "-v", "-s"], check=True)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "server"
    actions = {"server": run_server, "seed": run_seed, "test": run_tests}

    if cmd in actions:
        actions[cmd]()
    else:
        print(f"Unknown command: {cmd}. Use: server | seed | test")