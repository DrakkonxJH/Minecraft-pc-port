#!/usr/bin/env python3
"""
Reimplementa TimeRemaining.format() e verifica que a estimativa de tempo do
download nunca produz um texto absurdo.

O risco real aqui e dividir por uma velocidade proxima de zero e anunciar
"faltam 900 horas" quando a conexao apenas engasgou por um instante -- ou pior,
mostrar um numero que oscila violentamente a cada atualizacao de 33 ms.
"""
import math
import sys

FAILURES = []

MIN_SPEED = 1024          # 1 KB/s
MAX_SECONDS = 24 * 60 * 60
MB = 1024 * 1024


def fmt(remaining_bytes, bytes_per_second):
    """Espelha TimeRemaining.format(); None = nao mostrar estimativa."""
    if remaining_bytes <= 0: return None
    if bytes_per_second < MIN_SPEED: return None
    seconds = math.ceil(remaining_bytes / bytes_per_second)
    if seconds <= 0 or seconds > MAX_SECONDS: return None
    if seconds < 60:
        return f"faltam {seconds} s"
    if seconds < 3600:
        return f"faltam {(seconds + 59) // 60} min"
    return f"faltam {seconds // 3600}h {(seconds % 3600) // 60}min"


def check(cond, msg):
    if not cond:
        FAILURES.append(msg)


# --- Casos degenerados nao devem mostrar nada --------------------------------
check(fmt(0, 5 * MB) is None, "download terminado nao deveria mostrar ETA")
check(fmt(-100, 5 * MB) is None, "restante negativo nao deveria mostrar ETA")
check(fmt(100 * MB, 0) is None, "velocidade zero nao deveria mostrar ETA")
check(fmt(100 * MB, 10) is None, "10 B/s nao deveria mostrar ETA")
check(fmt(500 * MB, 1025) is None,
      "estimativa acima de 24 h nao deveria ser mostrada")

# --- Nunca lanca excecao em nenhuma combinacao plausivel ---------------------
for remaining in (0, 1, 1024, MB, 100 * MB, 2000 * MB):
    for speed in (0, 1, 1024, 100 * 1024, MB, 50 * MB):
        try:
            fmt(remaining, speed)
        except Exception as e:  # noqa: BLE001
            FAILURES.append(f"excecao com restante={remaining} speed={speed}: {e}")

# --- Monotonicidade: mais bytes restantes nunca deve dar menos tempo ---------
def seconds_of(remaining, speed):
    if remaining <= 0 or speed < MIN_SPEED: return 0
    return math.ceil(remaining / speed)

prev = 0
for mb in range(1, 500, 7):
    cur = seconds_of(mb * MB, 5 * MB)
    check(cur >= prev, f"{mb} MB restantes deu menos tempo que o anterior")
    prev = cur

# --- Mais velocidade nunca deve dar mais tempo -------------------------------
prev = float('inf')
for speed_mb in (0.5, 1, 2, 5, 10, 25, 50):
    cur = seconds_of(300 * MB, speed_mb * MB)
    check(cur <= prev, f"{speed_mb} MB/s deu mais tempo que uma velocidade menor")
    prev = cur

# --- Arredondamento para cima (nunca prometer menos do que vai levar) --------
check(fmt(int(1.5 * 60 * MB), MB) == "faltam 2 min",
      "90 s deveria virar '2 min', nao '1 min'")

# --- Casos concretos ---------------------------------------------------------
CASES = [
    ("Minecraft novo, 4G rapido",   350 * MB, 8 * MB,   "faltam 44 s"),
    ("Minecraft novo, wifi lento",  350 * MB, 1 * MB,   "faltam 6 min"),
    ("modpack grande, 3G",         1200 * MB, 300*1024, "faltam 1h 8min"),
    ("quase terminando",              2 * MB, 5 * MB,   "faltam 1 s"),
]
for name, remaining, speed, expected in CASES:
    got = fmt(remaining, speed)
    check(got == expected, f"{name}: esperado '{expected}', obtido '{got}'")
    print(f"  {name:28s} -> {got}")

if FAILURES:
    print("\nFALHAS:")
    for f in FAILURES:
        print("  -", f)
    sys.exit(1)
print("\nTempo restante: todas as verificacoes passaram")
