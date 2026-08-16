"""Valida a maquina de estados do gate de conta apos o MODO OFFLINE.

Espelha Tools.hasOnlineProfile(), Tools.hasVerifiedOwnership() e
Tools.hasNoOnlineProfileDialog().

Regra central: a posse do jogo e verificada UMA VEZ (o launcher baixa os
arquivos da Mojang, entao exigir a posse e obrigatorio); depois disso o
usuario joga offline sem depender da API da Microsoft.
"""


class Account:
    def __init__(self, username, access_token="0", is_microsoft=False):
        self.username = username
        self.accessToken = access_token
        self.isMicrosoft = is_microsoft

    def is_local(self):
        return self.accessToken == "0" and not self.username.startswith("Demo.")

    def is_demo(self):
        return self.username.startswith("Demo.")


class Launcher:
    def __init__(self, accounts=None, ownership_verified=False):
        self.accounts = accounts or []
        self.prefs = {"ownership_verified": ownership_verified}

    # --- Tools.hasOnlineProfile() ---
    def has_online_profile(self):
        return any(not a.is_local() and not a.is_demo() for a in self.accounts)

    # --- Tools.markOwnershipVerified() ---
    def mark_ownership_verified(self):
        self.prefs["ownership_verified"] = True

    # --- Tools.hasVerifiedOwnership() ---
    def has_verified_ownership(self):
        if self.has_online_profile():
            self.mark_ownership_verified()
            return True
        return self.prefs.get("ownership_verified", False)

    # --- Tools.hasNoOnlineProfileDialog() ---
    def gate(self, current_is_demo=False, custom_message=None):
        entitled = self.has_verified_ownership()
        demo_blocked = current_is_demo and custom_message is not None
        return entitled and not demo_blocked   # True = acao liberada


ONLINE = Account("Steve", access_token="abc123", is_microsoft=True)
LOCAL = Account("JogadorOffline")
DEMO = Account("Demo.Player", access_token="abc123")


def main():
    cases = [
        # (descricao, launcher, libera?, comentario)
        ("Instalacao nova, sem contas",
         Launcher(), False, "precisa validar a posse uma vez"),

        ("Conta Microsoft com o jogo",
         Launcher([ONLINE]), True, "caminho normal"),

        ("So conta local, posse NUNCA validada",
         Launcher([LOCAL]), False, "corretamente bloqueado"),

        ("So conta local, posse JA validada antes",
         Launcher([LOCAL], ownership_verified=True), True,
         "<< o ganho: joga offline"),

        ("Sem contas, mas posse ja validada",
         Launcher([], ownership_verified=True), True,
         "conta MS removida do aparelho"),

        ("Varios perfis locais, posse validada",
         Launcher([LOCAL, Account("OutroNick")], ownership_verified=True), True,
         "multiplos perfis offline"),

        ("Conta demo, posse nunca validada",
         Launcher([DEMO]), False, "demo nao comprova posse"),

        ("Conta demo + posse ja validada",
         Launcher([DEMO], ownership_verified=True), True, "liberado"),
    ]

    print(f"{'CENARIO':<42} | {'LIBERA':<7} | OBSERVACAO")
    print("-" * 100)
    failures = 0
    for desc, launcher, expected, note in cases:
        got = launcher.gate()
        ok = got == expected
        if not ok:
            failures += 1
        mark = "" if ok else "  <-- FALHOU"
        print(f"{desc:<42} | {str(got):<7} | {note}{mark}")

    print("-" * 100)

    # Efeito colateral: uma conta online valida grava a flag para uso offline
    l = Launcher([ONLINE])
    assert not l.prefs["ownership_verified"]
    l.has_verified_ownership()
    assert l.prefs["ownership_verified"], "login online deve gravar a flag"
    print("Login online grava a flag de posse para uso offline: ok")

    # A flag sobrevive a remocao da conta
    l.accounts = []
    assert l.has_verified_ownership(), "posse deve sobreviver a remocao da conta"
    print("Posse sobrevive a remocao da conta Microsoft: ok")

    # Bloqueio de demo continua valendo quando o chamador passa mensagem propria
    l2 = Launcher([DEMO], ownership_verified=True)
    assert l2.gate(current_is_demo=True, custom_message="demo") is False
    print("Bloqueio especifico de perfil demo preservado: ok")

    print(f"\nDivergencias: {failures}")
    assert failures == 0
    print("OK - todas as assercoes passaram")


if __name__ == "__main__":
    main()
