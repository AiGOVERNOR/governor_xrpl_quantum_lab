#!/data/data/com.termux/files/usr/bin/bash
set -e

cd "$HOME/governor_xrpl_quantum_lab"

pkg update -y && pkg upgrade -y
pkg install -y python git clang make

python -m venv .venv
. .venv/bin/activate

pip install --upgrade pip

echo "[*] Environment ready!"
echo "Run:"
echo "  . .venv/bin/activate"
echo "  python governor_ai.py --mode plan"
