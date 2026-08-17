#!/usr/bin/env python3
"""
Verifica os modos graficos (desempenho/automatico/qualidade) e os presets de
controle.

Dois riscos concretos aqui:

1. Os modos gravam preferencias em lote. Se "desempenho" acabar renderizando
   MAIS pixels que "qualidade" em algum aparelho, ninguem percebe olhando o
   codigo -- os valores saem de uma cadeia de multiplicacoes e arredondamentos.

2. O preset canhoto espelha posicoes reescrevendo expressoes matematicas
   ("${margin} * 2 + ${width}" vira "${screen_width} - ${width} - (...)").
   Um erro ali joga botoes para fora da tela, e o sintoma so aparece dentro do
   jogo, num aparelho com proporcao de tela diferente.
"""
import math
import re
import sys

FAILURES = []

def check(cond, msg):
    if not cond:
        FAILURES.append(msg)

LOW, MEDIUM, HIGH = "LOW", "MEDIUM", "HIGH"
INCREMENT = 5


def detect_tier(ram, cores, is32, gles, sdk):
    if ram < 4096 or cores <= 4 or is32 or gles < 3: return LOW
    if ram >= 8192 and cores >= 8 and sdk >= 30: return HIGH
    return MEDIUM


def automatic_scale(min_side, tier):
    target = {LOW: 540, MEDIUM: 720, HIGH: 1080}[tier]
    if min_side <= target: return 100
    scale = round(100 * target / min_side)
    scale = int(math.ceil(scale / INCREMENT) * INCREMENT)
    floor = 35 if tier == LOW else 50
    return max(floor, min(scale, 100))


def mode_scale(mode, min_side, tier):
    """Espelha GraphicsMode.resolutionScale()."""
    automatic = automatic_scale(min_side, tier)
    if mode == "performance":
        value = int(automatic * 0.70)
        value = int(math.ceil(value / INCREMENT) * INCREMENT)
        return max(35, value)
    if mode == "quality":
        return 100
    return automatic


DEVICES = [
    ("Poco X6 Pro",     11500, 8, False, 3, 34, 1220),
    ("Galaxy S23",       7800, 8, False, 3, 34, 1080),
    ("Moto G32",         3800, 8, False, 3, 31,  720),
    ("Redmi 9A",         1900, 4, False, 3, 29,  720),
    ("Galaxy J5 2016",   1500, 4, True,  2, 23,  720),
    ("16GB tela 1440p", 15500, 8, False, 3, 34, 1440),
]

print(f"{'Aparelho':18s}{'Tier':>8}  desempenho  automatico  qualidade")
print("-" * 62)
for name, ram, cores, is32, gles, sdk, side in DEVICES:
    tier = detect_tier(ram, cores, is32, gles, sdk)
    perf = mode_scale("performance", side, tier)
    auto = mode_scale("automatic", side, tier)
    qual = mode_scale("quality", side, tier)

    # Invariante central: a ordem entre os modos nunca pode se inverter
    check(perf <= auto, f"{name}: desempenho ({perf}%) renderiza mais que automatico ({auto}%)")
    check(auto <= qual, f"{name}: automatico ({auto}%) renderiza mais que qualidade ({qual}%)")

    for mode, value in (("desempenho", perf), ("automatico", auto), ("qualidade", qual)):
        check(35 <= value <= 100, f"{name}/{mode}: escala {value}% fora de 35-100")
        check(value % INCREMENT == 0,
              f"{name}/{mode}: escala {value}% nao e multiplo de {INCREMENT}")

    print(f"{name:18s}{tier:>8}{perf:>11}%{auto:>11}%{qual:>10}%")

# --- Coerencia dos ajustes por modo ------------------------------------------
def mode_settings(mode, tier):
    """Espelha o switch de GraphicsMode.apply()."""
    if mode == "performance":
        return {"force_vsync": False, "sustainedPerformance": False,
                "bigCoreAffinity": True, "checkLibraries": False}
    if mode == "quality":
        return {"force_vsync": True, "sustainedPerformance": True,
                "bigCoreAffinity": False, "checkLibraries": True}
    high = tier == HIGH
    return {"force_vsync": high, "sustainedPerformance": high,
            "bigCoreAffinity": not high, "checkLibraries": tier != LOW}

for tier in (LOW, MEDIUM, HIGH):
    perf = mode_settings("performance", tier)
    qual = mode_settings("quality", tier)
    # VSync limita quadros: nunca deve estar ligado no modo desempenho
    check(not perf["force_vsync"], f"{tier}: VSync ligado no modo desempenho limita os quadros")
    # Desempenho sustentado corta o clock de pico
    check(not perf["sustainedPerformance"],
          f"{tier}: desempenho sustentado ligado no modo desempenho corta o clock")
    check(qual["force_vsync"], f"{tier}: modo qualidade deveria ligar o VSync")

# --- Espelhamento do preset canhoto ------------------------------------------
def mirror_x(expr):
    """Espelha ControlPresets.mirrorX()."""
    if not expr: return expr
    return "${screen_width} - ${width} - (" + expr + ")"

def evaluate(expr, screen_width=2340, screen_height=1080, width=100, height=100,
             margin=10):
    """Avalia a expressao como o exp4j faria, para conferir os limites."""
    env = {
        "${screen_width}": str(screen_width), "${screen_height}": str(screen_height),
        "${width}": str(width), "${height}": str(height),
        "${margin}": str(margin),
        "${right}": str(screen_width - width),
        "${bottom}": str(screen_height - height),
        "${top}": "0", "${left}": "0",
        "${preferred_scale}": "100",
    }
    out = expr
    for key, value in env.items():
        out = out.replace(key, value)
    if re.search(r'[a-zA-Z_$]', out):
        return None  # contem funcao (px(), abs()...) que nao simulamos
    return eval(out)  # noqa: S307 - expressao controlada, so numeros e operadores

# Posicoes usadas pelo layout classico, que o preset canhoto espelha
CLASSIC_X = [
    "${margin}",
    "${margin} * 2 + ${width}",
    "${margin} * 3 + ${width} * 2",
    "${margin} * 4 + ${width} * 3",
    "${right} - ${margin} * 2 - ${width}",
]

for screen_w, screen_h in ((2340, 1080), (1920, 1080), (2400, 1080), (1280, 720)):
    for expr in CLASSIC_X:
        original = evaluate(expr, screen_width=screen_w, screen_height=screen_h)
        mirrored = evaluate(mirror_x(expr), screen_width=screen_w, screen_height=screen_h)
        if original is None or mirrored is None:
            continue
        # O botao espelhado precisa caber inteiro na tela
        check(mirrored >= 0,
              f"tela {screen_w}: espelhar '{expr}' deu x={mirrored}, fora da tela a esquerda")
        check(mirrored + 100 <= screen_w,
              f"tela {screen_w}: espelhar '{expr}' deu x={mirrored}, fora da tela a direita")
        # Espelhar duas vezes deve voltar a posicao original
        twice = evaluate(mirror_x(mirror_x(expr)), screen_width=screen_w,
                         screen_height=screen_h)
        check(twice is not None and abs(twice - original) < 0.01,
              f"tela {screen_w}: espelhar duas vezes '{expr}' nao voltou ao original "
              f"({original} -> {twice})")

# --- Presets declarados batem com os arrays de recursos ----------------------
with open('app_pojavlauncher/src/main/res/values/headings_array.xml', encoding='utf-8') as fh:
    arrays = fh.read()

for name, expected in (("control_preset_values", ["classic", "gamepad", "compact", "lefty"]),
                       ("graphics_mode_values", ["performance", "automatic", "quality"])):
    block = re.search(rf'<string-array name="{name}".*?</string-array>', arrays, re.S)
    check(block is not None, f"array {name} nao encontrado")
    if block:
        items = re.findall(r'<item>([^<]+)</item>', block.group(0))
        check(items == expected,
              f"array {name}: {items}, esperado {expected}")

# Os nomes exibidos devem ter a mesma quantidade dos valores
for names, values in (("control_preset_names", "control_preset_values"),
                      ("graphics_mode_names", "graphics_mode_values")):
    nb = re.search(rf'<string-array name="{names}".*?</string-array>', arrays, re.S)
    vb = re.search(rf'<string-array name="{values}".*?</string-array>', arrays, re.S)
    if nb and vb:
        n = len(re.findall(r'<item>', nb.group(0)))
        v = len(re.findall(r'<item>', vb.group(0)))
        check(n == v, f"{names} tem {n} itens mas {values} tem {v}: a lista ficaria dessincronizada")

if FAILURES:
    print("\nFALHAS:")
    for f in FAILURES:
        print("  -", f)
    sys.exit(1)
print("\nModos graficos e presets: todas as verificacoes passaram")
