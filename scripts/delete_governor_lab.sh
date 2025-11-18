#!/data/data/com.termux/files/usr/bin/bash
set -e

TARGET="$HOME/governor_xrpl_quantum_lab"

if [ -d "$TARGET" ]; then
    rm -rf "$TARGET"
    echo "[*] Project deleted."
else
    echo "[!] Nothing to delete."
fi
