"""Valida a arvore de decisao de Tools.setFullscreen()/applyContentInsets()
apos a migracao para edge-to-edge (AUDITORIA B2).

Regras que precisam valer na API 35+, onde setDecorFitsSystemWindows(true)
deixa de ter efeito e o edge-to-edge e imposto pela plataforma:

  1. Tela do jogo (fullscreen)  -> barras escondidas, padding ZERO
  2. Launcher (nao-fullscreen)  -> barras visiveis, padding = insets
  3. Multi-janela               -> nunca fullscreen, sempre padding
"""

# Insets simulados de um aparelho com notch, em landscape.
BARS = {"left": 0, "top": 66, "right": 0, "bottom": 48}
CUTOUT = {"left": 88, "top": 0, "right": 0, "bottom": 0}


def union(a, b):
    return {k: max(a[k], b[k]) for k in a}


def set_fullscreen(fullscreen, sdk_int, in_multi_window):
    """Espelha Tools.setFullscreen()."""
    multi_window_mode = sdk_int >= 24 and in_multi_window
    want_fullscreen = fullscreen and not multi_window_mode

    state = {
        "decorFitsSystemWindows": False,   # sempre False agora
        "systemBarsHidden": want_fullscreen,
        "transientBySwipe": want_fullscreen,
    }
    state["padding"] = apply_content_insets(want_fullscreen)
    return state


def apply_content_insets(fullscreen):
    """Espelha Tools.applyContentInsets()."""
    if fullscreen:
        return {"left": 0, "top": 0, "right": 0, "bottom": 0}
    return union(BARS, CUTOUT)


CASES = [
    # (descricao, fullscreen, sdk, multiwindow, espera_barras_ocultas, espera_padding)
    ("Jogo (MainActivity), API 36",          True,  36, False, True,  False),
    ("Jogo, API 30",                          True,  30, False, True,  False),
    ("Jogo, API 21",                          True,  21, False, True,  False),
    ("Launcher (LauncherActivity), API 36",  False, 36, False, False, True),
    ("Launcher, API 21",                     False, 21, False, False, True),
    ("Jogo em multi-janela, API 36",         True,  36, True,  False, True),
    ("Launcher em multi-janela, API 36",     False, 36, True,  False, True),
]


def main():
    hdr = f"{'CENARIO':<38} | {'BARRAS':<9} | {'PADDING':<26} | OK"
    print(hdr)
    print("-" * len(hdr))

    failures = 0
    for desc, fs, sdk, mw, exp_hidden, exp_padded in CASES:
        st = set_fullscreen(fs, sdk, mw)
        padded = any(v > 0 for v in st["padding"].values())

        ok = st["systemBarsHidden"] == exp_hidden and padded == exp_padded
        # Invariante critica: nunca esconder as barras E aplicar padding ao mesmo
        # tempo (desperdicaria area util), nem mostrar barras sem padding
        # (conteudo ficaria por baixo delas na API 35+).
        if st["systemBarsHidden"] == padded:
            ok = False
        if not ok:
            failures += 1

        bars = "ocultas" if st["systemBarsHidden"] else "visiveis"
        pad = str(tuple(st["padding"].values())) if padded else "zero"
        print(f"{desc:<38} | {bars:<9} | {pad:<26} | {'ok' if ok else 'FALHOU'}")

    print("-" * len(hdr))
    print(f"Divergencias: {failures}")
    assert failures == 0, "A arvore de decisao divergiu do esperado"
    print("\nOK - todas as assercoes passaram")


if __name__ == "__main__":
    main()
