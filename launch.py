#!/usr/bin/env python3
"""
MONK-OS Launcher — lance l'app de façon déterministe.

Corrige les problèmes de démarrage :
- tue toute ancienne instance qui bloque le port,
- port FIXE (8505) — l'URL est donc toujours la même,
- utilise le même interpréteur Python (sys.executable -m streamlit), donc pas
  de dépendance à un `streamlit` présent ou non dans le PATH,
- n'ouvre le navigateur qu'une fois le serveur réellement prêt.
"""

import os
import sys
import time
import socket
import subprocess
import webbrowser
from urllib.request import urlopen

PORT = 8505
URL = f"http://localhost:{PORT}"


def port_is_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex(("127.0.0.1", port)) == 0


def kill_stale_instances(port: int):
    """Tue tout process qui écoute déjà sur le port (ancienne instance MONK-OS)."""
    try:
        pids = subprocess.check_output(
            ["lsof", "-ti", f"tcp:{port}", "-sTCP:LISTEN"],
            text=True,
        ).split()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pids = []
    for pid in pids:
        try:
            subprocess.run(["kill", pid], check=False)
            print(f"   ↳ ancienne instance arrêtée (PID {pid})")
        except Exception:
            pass
    if pids:
        time.sleep(1.5)  # laisse le port se libérer


def wait_until_ready(url: str, timeout: float = 25.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def launch_app():
    app_dir = os.path.dirname(os.path.abspath(__file__))
    app_file = os.path.join(app_dir, "app.py")

    print("🚀 Lancement de MONK-OS...")

    # 1. Nettoie toute instance déjà en cours sur le port.
    if port_is_open(PORT):
        print(f"   Port {PORT} occupé — nettoyage de l'ancienne instance...")
        kill_stale_instances(PORT)

    # 2. Démarre Streamlit avec le Python courant (indépendant du PATH).
    try:
        process = subprocess.Popen(
            [
                sys.executable, "-m", "streamlit", "run", app_file,
                "--server.port", str(PORT),
                "--server.headless", "true",
                "--logger.level=error",
            ],
            cwd=app_dir,
        )
    except FileNotFoundError:
        print("❌ Streamlit introuvable. Installe-le avec :")
        print(f"   {sys.executable} -m pip install -r requirements.txt")
        sys.exit(1)

    # 3. Attend que le serveur réponde avant d'ouvrir le navigateur.
    print(f"   En attente du serveur sur {URL} ...")
    if wait_until_ready(URL):
        print(f"   ✓ Prêt — ouverture de {URL}\n")
        webbrowser.open(URL)
    else:
        print("   ⚠ Le serveur met du temps à démarrer. Ouvre manuellement :")
        print(f"   {URL}\n")

    try:
        process.wait()
    except KeyboardInterrupt:
        process.terminate()
        print("\n✓ MONK-OS fermée")
        sys.exit(0)


if __name__ == "__main__":
    launch_app()
