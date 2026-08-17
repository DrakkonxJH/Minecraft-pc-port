#!/usr/bin/env python3
"""
Reimplementa getCompatibleRenderers() e a autosselecao de renderizador do
MainActivity, e roda os dois contra um catalogo de aparelhos reais variados.

Motivacao: todas as decisoes de renderizador foram calibradas num unico
aparelho (Adreno/Mali topo de linha, GLES 3.2, Vulkan). As regressoes que
importam acontecem justamente nos aparelhos que nao temos -- GLES 2, sem
Vulkan, GPU nao identificada -- e o sintoma tipico e tela preta, nao excecao,
o que torna a falha silenciosa.
"""
import sys

FAILURES = []

def check(cond, msg):
    if not cond:
        FAILURES.append(msg)

ALL_RENDERERS = [
    "opengles2",
    "opengles3_desktopgl_zink_kopper",
    "vulkan_zink",
    "opengles_mobileglues",
    "opengles3_ltw",
]

# Bibliotecas presentes neste APK (confirmado em jniLibs/ e nos AARs)
LIBS_PRESENT = {
    "opengles2": True,                        # libng_gl4es.so
    "opengles3_desktopgl_zink_kopper": True,  # libglxshim.so
    "opengles_mobileglues": True,             # libmobileglues.so
    "vulkan_zink": False,                     # libOSMesa.so ausente
    "opengles3_ltw": False,                   # libltw.so proprietaria, ausente
}


def requires_gles3(rid):
    return "mobileglues" in rid or "zink" in rid or "ltw" in rid


def compatible_renderers(has_vulkan, gles_major, libs=None):
    """Espelha Tools.getCompatibleRenderers()."""
    libs = LIBS_PRESENT if libs is None else libs
    has_gles3 = gles_major >= 3
    out = []
    for rid in ALL_RENDERERS:
        if "vulkan" in rid and not has_vulkan: continue
        if "vulkan_zink" in rid and not libs.get("vulkan_zink"): continue
        if "ltw" in rid and (not has_gles3 or not libs.get("opengles3_ltw")): continue
        if requires_gles3(rid) and not has_gles3: continue
        if not libs.get(rid, True): continue
        out.append(rid)
    if not out:
        out.append("opengles2")   # fallback garantido
    return out


def autoselect(modern_version, gles_major, has_vulkan):
    """Espelha a autosselecao do MainActivity + o ajuste de compatibilidade."""
    renderer = "opengles2"
    if modern_version and gles_major >= 3:
        renderer = "opengles_mobileglues"
    available = compatible_renderers(has_vulkan, gles_major)
    if renderer not in available:
        renderer = available[0]
    return renderer


# Catalogo de aparelhos reais, cobrindo a faixa que o app aceita (minSdk 21)
DEVICES = [
    # (nome, GLES, Vulkan, RAM MB, 64 bits)
    ("Poco X6 Pro (Mali-G615, Android 14)",        3, True,  11500, True),
    ("Xiaomi 2311DRK48G (Mali-G615)",              3, True,  11323, True),
    ("Galaxy S23 (Adreno 740, OneUI)",             3, True,   7800, True),
    ("Galaxy S21 (Xclipse/Mali)",                  3, True,   7500, True),
    ("Pixel 8 (Mali-G715, 16 KB pages)",           3, True,  11800, True),
    ("Moto G32 (Adreno 610)",                      3, True,   3800, True),
    ("Redmi 9A (PowerVR GE8320, Android 10)",      3, False,  1900, True),
    ("Galaxy J5 2016 (Adreno 306, Android 6)",     2, False,  1500, False),
    ("tablet generico GLES2 sem Vulkan",           2, False,  2000, True),
    ("aparelho com GPU nao identificada",          2, False,  3000, True),
    ("emulador x86_64 (SwiftShader)",              3, False,  4000, True),
]

print("Aparelho                                    GLES  Vulkan  ->  renderer escolhido")
print("-" * 92)
for name, gles, vulkan, ram, is64 in DEVICES:
    available = compatible_renderers(vulkan, gles)

    # Nunca pode ficar vazio: quem chama faz .get(0) direto
    check(len(available) > 0, f"{name}: lista de renderizadores vazia")

    # Nenhum renderizador que exige GLES 3 pode sobrar num aparelho GLES 2
    if gles < 3:
        for rid in available:
            check(not requires_gles3(rid),
                  f"{name}: {rid} exige GLES 3 mas o aparelho so tem GLES {gles}")

    # Nenhum renderizador sem biblioteca empacotada pode ser oferecido
    for rid in available:
        check(LIBS_PRESENT.get(rid, True) or rid == "opengles2",
              f"{name}: {rid} nao tem biblioteca nativa no APK")

    # A escolha automatica precisa estar entre as disponiveis
    for modern in (False, True):
        chosen = autoselect(modern, gles, vulkan)
        check(chosen in available,
              f"{name}: autosselecao escolheu {chosen}, fora da lista disponivel")
        # MobileGlues jamais em GLES 2 -- este era o bug: bastava a versao ser
        # 1.17+ para escolher MobileGlues em qualquer hardware
        if gles < 3:
            check(chosen != "opengles_mobileglues",
                  f"{name}: MobileGlues escolhido num aparelho GLES 2 (tela preta)")

    chosen_modern = autoselect(True, gles, vulkan)
    print(f"{name:44s}{gles:^6}{str(vulkan):^8}  ->  {chosen_modern}")

# --- Caso extremo: nenhuma biblioteca presente -------------------------------
empty = compatible_renderers(True, 3, libs={k: False for k in LIBS_PRESENT})
check(empty == ["opengles2"],
      f"sem nenhuma biblioteca o fallback deveria ser opengles2, veio {empty}")

if FAILURES:
    print("\nFALHAS:")
    for f in FAILURES:
        print("  -", f)
    sys.exit(1)
print("\nCompatibilidade de renderizadores: todas as verificacoes passaram")
