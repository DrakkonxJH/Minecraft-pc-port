#!/usr/bin/env python3
"""
Reimplementa a logica de RAM automatica de LauncherPreferences em Python e
verifica que ela se comporta bem em toda a faixa de aparelhos -- de 1 GB ate
24 GB -- e nao so no aparelho do desenvolvedor.

Nao substitui uma compilacao: apenas garante que as regras nao produzam
valores absurdos (heap maior que a memoria livre, piso negativo, aparelho de
16 GB recebendo menos que um de 12 GB, etc).
"""
import sys

FAILURES = []


def check(condition, message):
    if not condition:
        FAILURES.append(message)


def find_best(device_ram, is32=False):
    """Espelha findBestRAMAllocation()."""
    if device_ram < 1024: return 296
    if device_ram < 1536: return 448
    if device_ram < 2048: return 656
    if is32: return 696
    if device_ram < 3064: return 936
    if device_ram < 4096: return 1144
    scaled = round(device_ram * 0.30 / 256) * 256
    return max(1280, min(scaled, 6144))


def compute_automatic(device_ram, free_ram, mods, is32=False):
    """Espelha computeAutomaticRAM()."""
    baseline = find_best(device_ram, is32)
    if mods >= 150:  bonus = 2048
    elif mods >= 75: bonus = 1536
    elif mods >= 30: bonus = 1024
    elif mods >= 10: bonus = 512
    else:            bonus = 0
    target = baseline + bonus
    target = min(target, int(device_ram * 0.55))
    if is32:
        target = min(target, 1024)
    if free_ram > 0:
        target = min(target, free_ram - 1536)
    return max(target, 512)


# --- Propriedades gerais, em toda a faixa de aparelhos -----------------------
for ram in range(512, 24577, 128):
    free = int(ram * 0.85)  # aparelho recem-ligado
    value = compute_automatic(ram, free, 0)
    check(value >= 512, f"{ram} MB: alocacao {value} abaixo do piso")
    check(value <= max(512, int(ram * 0.55)),
          f"{ram} MB: alocacao {value} passou de 55% da RAM total")
    check(value <= 6144 or ram < 0, f"{ram} MB: alocacao {value} passou do teto absoluto")

# --- Monotonicidade: mais RAM nunca deve dar menos heap ----------------------
prev = 0
for ram in range(4096, 24577, 256):
    value = compute_automatic(ram, int(ram * 0.85), 0)
    check(value >= prev,
          f"nao monotonico: {ram} MB deu {value}, menor que o aparelho anterior ({prev})")
    prev = value

# --- Mais mods nunca deve dar menos heap -------------------------------------
for ram in (4096, 8192, 12288, 16384, 24576):
    prev = 0
    for mods in (0, 10, 30, 75, 150, 400):
        value = compute_automatic(ram, int(ram * 0.85), mods)
        check(value >= prev, f"{ram} MB com {mods} mods deu {value} < {prev}")
        prev = value

# --- 32 bits nunca deve exceder o espaco enderecavel -------------------------
for ram in (2048, 4096, 8192):
    value = compute_automatic(ram, int(ram * 0.85), 200, is32=True)
    check(value <= 1024, f"32 bits com {ram} MB pediu {value} MB de heap")

# --- Memoria livre e respeitada ----------------------------------------------
check(compute_automatic(12288, 2000, 0) == 512,
      "com apenas 2 GB livres o piso de 512 MB deveria prevalecer")
check(compute_automatic(12288, 4096, 0) <= 4096 - 1536,
      "com 4 GB livres o heap deveria deixar 1,5 GB para o sistema")

# --- Casos concretos citados pelo usuario ------------------------------------
CASES = [
    # (nome, RAM total, RAM livre, mods, faixa esperada)
    ("Xiaomi 2311DRK48G (12 GB)",       11323, 9000, 0,   (3000, 3600)),
    ("Poco X6 Pro (12 GB reais)",       11500, 9000, 0,   (3000, 3600)),
    ("Poco X6 Pro com modpack grande",  11500, 9000, 120, (4500, 5200)),
    ("aparelho de 6 GB",                 5800, 4500, 0,   (1500, 2000)),
    ("aparelho de 16 GB",               15500, 12000, 0,  (4400, 5000)),
    ("aparelho de 24 GB",               23000, 18000, 0,  (6000, 6200)),
    ("aparelho de 3 GB",                 2900, 2200, 0,   (512, 1000)),
]
for name, ram, free, mods, (lo, hi) in CASES:
    value = compute_automatic(ram, free, mods)
    check(lo <= value <= hi,
          f"{name}: alocou {value} MB, esperado entre {lo} e {hi}")
    print(f"  {name:34s} -> {value:5d} MB")

if FAILURES:
    print("\nFALHAS:")
    for f in FAILURES:
        print("  -", f)
    sys.exit(1)
print("\nRAM automatica: todas as verificacoes passaram")
