"""Valida quando o MinecraftDownloader baixa arquivos do jogo.

Bug corrigido: a condicao era `isLocalProfile || !isOnline`, o que impedia
QUALQUER perfil offline de baixar. Ao selecionar Forge/Fabric sem o vanilla
correspondente instalado, o launcher pulava o download e o jogo estourava com

    Can't find the source version for 1.21-forge-51.0.33 (req version=1.21)

Regra correta: baixar depende de haver INTERNET, nao do tipo de conta. Os
arquivos do jogo sao servidos publicamente pela Mojang, sem autenticacao.
"""


def should_download_old(is_local_profile, is_online):
    """Comportamento antigo (com o bug)."""
    return not (is_local_profile or not is_online)


def should_download_new(is_local_profile, is_online):
    """Comportamento novo: so a conexao importa."""
    return is_online


CASES = [
    # (descricao, conta_local, online, deve_baixar)
    ("Conta offline + internet",          True,  True,  True),
    ("Conta offline + sem internet",      True,  False, False),
    ("Conta Microsoft + internet",        False, True,  True),
    ("Conta Microsoft + sem internet",    False, False, False),
]


def main():
    print(f"{'CENARIO':<32} | {'ANTES':<7} | {'AGORA':<7} | ESPERADO")
    print("-" * 70)
    failures = 0
    regressions_fixed = 0
    for desc, local, online, expected in CASES:
        old = should_download_old(local, online)
        new = should_download_new(local, online)
        ok = new == expected
        if not ok:
            failures += 1
        if old != new:
            regressions_fixed += 1
        mark = "" if ok else "   <-- FALHOU"
        print(f"{desc:<32} | {str(old):<7} | {str(new):<7} | {expected}{mark}")

    print("-" * 70)
    print(f"Casos corrigidos pela mudanca: {regressions_fixed}")
    print(f"Divergencias: {failures}")

    # O caso do bug relatado: conta offline com internet DEVE baixar
    assert should_download_new(is_local_profile=True, is_online=True), \
        "perfil offline com internet precisa poder baixar"
    assert not should_download_old(is_local_profile=True, is_online=True), \
        "o teste deveria demonstrar o bug antigo"
    print("Cenario do erro relatado (offline + internet) corrigido: ok")

    # Sem internet segue bloqueado, para ambos os tipos de conta
    assert not should_download_new(True, False)
    assert not should_download_new(False, False)
    print("Sem internet continua bloqueado, como esperado: ok")

    assert failures == 0
    print("\nOK - todas as assercoes passaram")


if __name__ == "__main__":
    main()
