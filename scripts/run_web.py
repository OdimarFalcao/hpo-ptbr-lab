from __future__ import annotations

import argparse
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def port_available(port: int) -> bool:
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Inicia a bancada local; Ctrl+C encerra apenas os processos desta execução.")
    parser.add_argument("--without-research", action="store_true", help="Não iniciar Streamlit; a área de pesquisa deve ser iniciada separadamente.")
    args = parser.parse_args()
    if not (ROOT / "web/dist/index.html").is_file():
        print("Frontend ausente. Execute npm ci e npm run build dentro de web/.")
        return 1
    ports = [8000] if args.without_research else [8000, 8504]
    if any(not port_available(port) for port in ports):
        print(f"Uma das portas {ports} está ocupada. Não encerrei processos existentes. Pare a execução anterior ou use --without-research se apenas 8504 estiver ocupada.")
        return 1
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    processes = []
    try:
        processes.append(subprocess.Popen([sys.executable, "-m", "uvicorn", "hpo_ptbr.web_api:app", "--host", "127.0.0.1", "--port", "8000", "--no-access-log"], cwd=ROOT, env=environment))
        if not args.without_research:
            processes.append(subprocess.Popen([sys.executable, "-m", "streamlit", "run", "streamlit_app.py", "--server.address", "127.0.0.1", "--server.port", "8504", "--browser.gatherUsageStats", "false"], cwd=ROOT, env=environment))
        print("Bancada: http://127.0.0.1:8000 · Pesquisa: http://127.0.0.1:8504", flush=True)
        print("Mantenha este terminal aberto. Ctrl+C encerra os servidores iniciados aqui.", flush=True)
        while all(process.poll() is None for process in processes):
            time.sleep(0.5)
        return 1
    except KeyboardInterrupt:
        return 0
    finally:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        for process in processes:
            if process.poll() is None:
                process.terminate()
        for process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


if __name__ == "__main__":
    raise SystemExit(main())
