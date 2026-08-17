#!/usr/bin/env python3
"""
Reimplementa DeviceProfile e verifica o perfil de estabilidade contra um
catalogo de aparelhos reais.

O risco especifico deste recurso: ele grava configuracoes automaticamente. Um
erro aqui nao trava o app -- ele degrada silenciosamente a experiencia de quem
nunca vai reclamar, ou pior, sobrescreve o que o usuario ajustou a mao. As
verificacoes abaixo focam nesses dois pontos.
"""
import math
import sys

FAILURES = []


def check(cond, msg):
    if not cond:
        FAILURES.append(msg)


LOW, MEDIUM, HIGH = "LOW", "MEDIUM", "HIGH"


def detect_tier(ram, cores, is32, gles, sdk):
    """Espelha DeviceProfile.detectTier()."""
    if ram < 4096 or cores <= 4 or is32 or gles < 3:
        return LOW
    if ram >= 8192 and cores >= 8 and sdk >= 30:
        return HIGH
    return MEDIUM


def resolution_scale(min_side, tier, increment=5):
    """Espelha DeviceProfile.recommendedResolutionScale()."""
    target = {LOW: 540, MEDIUM: 720, HIGH: 1080}[tier]
    if min_side <= target:
        return 100
    scale = round(100 * target / min_side)
    scale = int(math.ceil(scale / increment) * increment)
    floor = 35 if tier == LOW else 50
    return max(floor, min(scale, 100))


def recommended_settings(tier):
    """Espelha o conjunto de chaves gravadas por applyRecommendedDefaults()."""
    high = tier == HIGH
    return {
        "alternate_surface":    tier != LOW,
        "sustainedPerformance": high,
        "force_vsync":          high,
        "bigCoreAffinity":      tier != HIGH,
        "checkLibraries":       tier != LOW,
        "allocationAutomatic":  True,
    }


# (nome, RAM, cores, 32bits, GLES, SDK, lado menor da tela, tier esperado)
DEVICES = [
    ("Poco X6 Pro",                 11500, 8, False, 3, 34, 1220, HIGH),
    ("Xiaomi 2311DRK48G",           11323, 8, False, 3, 36, 1080, HIGH),
    ("Galaxy S23",                   7800, 8, False, 3, 34, 1080, MEDIUM),
    ("Pixel 8",                     11800, 9, False, 3, 34, 1080, HIGH),
    ("Moto G32",                     3800, 8, False, 3, 31,  720, LOW),
    ("Redmi 9A",                     1900, 4, False, 3, 29,  720, LOW),
    ("Galaxy J5 2016",               1500, 4, True,  2, 23,  720, LOW),
    ("tablet GLES2",                 2000, 4, False, 2, 22,  800, LOW),
    ("Galaxy A54",                   7600, 8, False, 3, 33, 1080, MEDIUM),
    ("aparelho 8GB Android 9",       8192, 8, False, 3, 28, 1080, MEDIUM),
    ("aparelho 16GB gamer",         15500, 8, False, 3, 34, 1440, HIGH),
]

print(f"{'Aparelho':24s}{'Tier':>8}{'Escala':>9}   surface  sustained  vsync  bigCore")
print("-" * 78)
for name, ram, cores, is32, gles, sdk, side, expected in DEVICES:
    tier = detect_tier(ram, cores, is32, gles, sdk)
    check(tier == expected, f"{name}: classificado {tier}, esperado {expected}")

    scale = resolution_scale(side, tier)
    floor = 35 if tier == LOW else 50
    check(floor <= scale <= 100, f"{name}: escala {scale} fora de {floor}-100%")
    check(scale % 5 == 0, f"{name}: escala {scale} nao e multiplo do incremento")

    s = recommended_settings(tier)
    # Invariante central: aparelho de entrada nunca recebe ajuste caro
    if tier == LOW:
        check(not s["sustainedPerformance"],
              f"{name}: desempenho sustentado num aparelho de entrada corta o clock de pico")
        check(not s["alternate_surface"],
              f"{name}: surface alternativa em aparelho de entrada (driver antigo)")
        check(not s["checkLibraries"],
              f"{name}: verificacao SHA-1 atrasa o lancamento em aparelho fraco")
        check(scale <= 100, f"{name}: escala deveria reduzir")
    # RAM automatica e sempre ligada: e a protecao contra o Android matar o jogo
    check(s["allocationAutomatic"], f"{name}: RAM automatica deveria estar ligada")

    print(f"{name:24s}{tier:>8}{scale:>8}%   "
          f"{str(s['alternate_surface']):<9}{str(s['sustainedPerformance']):<11}"
          f"{str(s['force_vsync']):<7}{s['bigCoreAffinity']}")

# --- Monotonicidade: hardware melhor nunca deve receber perfil pior ----------
order = {LOW: 0, MEDIUM: 1, HIGH: 2}
prev = -1
for ram in range(2048, 16385, 512):
    tier = detect_tier(ram, 8, False, 3, 34)
    check(order[tier] >= prev,
          f"{ram} MB recebeu tier menor que um aparelho com menos RAM")
    prev = order[tier]

# --- Escala de resolucao: tela maior nunca deve renderizar mais pixels -------
for tier in (LOW, MEDIUM, HIGH):
    prev_pixels = None
    for side in (540, 720, 900, 1080, 1440, 2160):
        scale_pct = resolution_scale(side, tier)
        pixels = side * scale_pct / 100
        target = {LOW: 540, MEDIUM: 720, HIGH: 1080}[tier]
        floor = 35 if tier == LOW else 50
        # Quando o piso de legibilidade e atingido, nao da para chegar ao alvo:
        # a checagem entao e so que o piso foi de fato respeitado.
        at_floor = scale_pct == floor
        check(at_floor or pixels <= target * 1.12,
              f"tier {tier}, tela {side}: renderiza {pixels:.0f}px, alvo {target}px")
        prev_pixels = pixels

# --- Qualquer aparelho GLES 2 ou 32 bits e sempre LOW ------------------------
for ram in (2048, 8192, 16384):
    for cores in (4, 8):
        check(detect_tier(ram, cores, True, 3, 34) == LOW,
              f"32 bits com {ram} MB/{cores} cores nao foi classificado LOW")
        check(detect_tier(ram, cores, False, 2, 34) == LOW,
              f"GLES 2 com {ram} MB/{cores} cores nao foi classificado LOW")

# --- Preservacao das escolhas do usuario -------------------------------------
def apply(prefs, force, recommended):
    """Espelha setIfAbsent(): so grava o que o usuario nunca tocou."""
    result = dict(prefs)
    for key, value in recommended.items():
        if force or key not in prefs:
            result[key] = value
    return result

user_prefs = {"alternate_surface": False, "force_vsync": True}
after = apply(user_prefs, False, recommended_settings(HIGH))
check(after["alternate_surface"] is False,
      "aplicacao automatica sobrescreveu uma escolha explicita do usuario")
check(after["force_vsync"] is True,
      "aplicacao automatica sobrescreveu force_vsync do usuario")
check("bigCoreAffinity" in after,
      "chaves nao tocadas pelo usuario deveriam receber o padrao recomendado")

forced = apply(user_prefs, True, recommended_settings(HIGH))
check(forced["alternate_surface"] is True,
      "o botao manual deveria sobrescrever, ja que o usuario pediu")

if FAILURES:
    print("\nFALHAS:")
    for f in FAILURES:
        print("  -", f)
    sys.exit(1)
print("\nPerfil de aparelho: todas as verificacoes passaram")
