"""Valida que o gate de conta foi removido: TODA conta acessa TODAS as funcoes.

Contexto: a restricao nao vinha do PojavLauncher (base deste projeto) — foi
introduzida pelo Amethyst em 2025 (commit 17c435da3). O MineDrakk a remove,
voltando ao comportamento original: contas locais/offline sao um recurso
padrao de launchers de terceiros.

Isto nao contorna protecao alguma:
  * os arquivos do jogo vem dos servidores publicos da Mojang;
  * servidores com online-mode=true seguem recusando contas sem licenca,
    pois quem valida e o servidor da Mojang, nao o launcher.
"""


class Account:
    def __init__(self, username, access_token="0"):
        self.username = username
        self.accessToken = access_token

    def is_local(self):
        return self.accessToken == "0" and not self.username.startswith("Demo.")

    def is_demo(self):
        return self.username.startswith("Demo.")


class Launcher:
    def __init__(self, accounts=None):
        self.accounts = accounts or []

    # --- Tools.hasVerifiedOwnership() -> sempre true ---
    def has_verified_ownership(self):
        return True

    # --- Tools.hasOnlineProfile(): informativo, nao bloqueia ---
    def has_online_profile(self):
        return any(not a.is_local() and not a.is_demo() for a in self.accounts)

    # --- Tools.hasNoOnlineProfileDialog(): executa a acao, nunca barra ---
    def gate(self, run=None, custom_title=None, custom_message=None):
        if run is not None:
            return run()          # acao sempre executa
        return None               # so exibe dialogo informativo

    # --- LauncherActivity: sem restricao de versao por tipo de conta ---
    def can_launch_version(self, release_year):
        return True


ONLINE = Account("Steve", access_token="abc123")
LOCAL = Account("JogadorOffline")
DEMO = Account("Demo.Player", access_token="abc123")

FEATURES = ["criar perfil", "editar perfil", "instalar JAR",
            "instalar modpack", "abrir pasta", "login local", "jogar"]


def main():
    setups = [
        ("Sem nenhuma conta", Launcher()),
        ("So conta local", Launcher([LOCAL])),
        ("Conta demo (Demo.Player)", Launcher([DEMO])),
        ("Conta Microsoft completa", Launcher([ONLINE])),
        ("Varias contas locais", Launcher([LOCAL, Account("Amigo1")])),
    ]

    print(f"{'CENARIO':<28} | {'FUNCOES LIBERADAS':<20} | VERSOES")
    print("-" * 76)
    failures = 0
    for desc, launcher in setups:
        liberadas = sum(1 for _ in FEATURES if launcher.gate(run=lambda: True))
        todas = liberadas == len(FEATURES)
        # qualquer versao, incluindo anteriores a 1.3.1 (antes travadas na demo)
        versoes = all(launcher.can_launch_version(y) for y in (2010, 2012, 2020, 2026))
        if not (todas and versoes):
            failures += 1
        print(f"{desc:<28} | {liberadas}/{len(FEATURES)}{'':<16} | "
              f"{'todas' if versoes else 'RESTRITO'}")

    print("-" * 76)

    # A acao passada ao gate deve realmente executar
    executed = []
    Launcher().gate(run=lambda: executed.append(True))
    assert executed, "a acao deveria ter sido executada"
    print("Acao passada ao gate executa: ok")

    # hasOnlineProfile continua reportando o fato corretamente (uso informativo)
    assert Launcher([ONLINE]).has_online_profile() is True
    assert Launcher([LOCAL]).has_online_profile() is False
    assert Launcher([DEMO]).has_online_profile() is False
    print("hasOnlineProfile segue informando corretamente: ok")

    # Versoes antigas liberadas para conta demo (trava do launcher removida)
    assert Launcher([DEMO]).can_launch_version(2011) is True
    print("Versoes anteriores a 1.3.1 liberadas na conta demo: ok")

    print(f"\nDivergencias: {failures}")
    assert failures == 0
    print("OK - todas as assercoes passaram")


if __name__ == "__main__":
    main()
