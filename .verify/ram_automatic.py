"""Valida o modo automatico de alocacao de RAM.

Problema observado: um Xiaomi com 11.323 MB recebeu 10.296 MB (91% da RAM
total), sobrando ~1 GB para o Android inteiro. Nessa faixa o sistema mata o
processo do jogo quando outro app pede memoria, e as pausas de GC crescem
porque o heap fica muito maior que o working set real do Minecraft.

Regras implementadas em LauncherPreferences:
  * baseline por hardware (findBestRAMAllocation)
  * bonus por quantidade de mods
  * teto rigido de 55% da RAM total
  * respeito a memoria livre no momento, reservando 1,5 GB ao sistema
  * piso de 512 MB
"""


def find_best_ram(device_ram, is_32bit=False):
    """Espelha LauncherPreferences.findBestRAMAllocation()."""
    if device_ram < 1024: return 296
    if device_ram < 1536: return 448
    if device_ram < 2048: return 656
    if is_32bit: return 696
    if device_ram < 3064: return 936
    if device_ram < 4096: return 1144
    if device_ram < 6144: return 1536
    if device_ram < 8192: return 2048
    if device_ram < 12288: return 3072
    return 4096


def compute_automatic_ram(device_ram, mod_count=0, available=0, is_32bit=False):
    """Espelha LauncherPreferences.computeAutomaticRAM()."""
    baseline = find_best_ram(device_ram, is_32bit)

    if mod_count >= 150:  bonus = 2048
    elif mod_count >= 75: bonus = 1536
    elif mod_count >= 30: bonus = 1024
    elif mod_count >= 10: bonus = 512
    else:                 bonus = 0

    target = baseline + bonus
    target = min(target, int(device_ram * 0.55))

    if available > 0:
        target = min(target, available - 1536)

    return max(target, 512)


def main():
    print("=== Aparelhos comuns, vanilla ===")
    print(f"{'RAM TOTAL':<12} | {'ALOCADO':<9} | {'% DA RAM':<9} | SOBRA P/ SISTEMA")
    print("-" * 62)
    failures = 0
    for ram in (2048, 4096, 6144, 8192, 11323, 16384):
        alloc = compute_automatic_ram(ram)
        pct = alloc / ram * 100
        left = ram - alloc
        # Invariantes: nunca passar de 55%, sempre deixar >= 2 GB livres em
        # aparelhos de 6 GB ou mais.
        ok = pct <= 55.1 and (ram < 6144 or left >= 2048)
        failures += 0 if ok else 1
        mark = "" if ok else "   <-- FALHOU"
        print(f"{ram:>6} MB    | {alloc:>5} MB  | {pct:>6.1f}%   | {left:>6} MB{mark}")

    print("\n=== Seu aparelho (11.323 MB) por quantidade de mods ===")
    print(f"{'MODS':<8} | {'ALOCADO':<9} | {'% DA RAM':<9} | OBSERVACAO")
    print("-" * 62)
    for mods, desc in ((0, "vanilla"), (15, "poucos mods"), (45, "modpack medio"),
                       (90, "modpack grande"), (200, "modpack pesado")):
        alloc = compute_automatic_ram(11323, mods)
        pct = alloc / 11323 * 100
        ok = pct <= 55.1
        failures += 0 if ok else 1
        print(f"{mods:>4}     | {alloc:>5} MB  | {pct:>6.1f}%   | {desc}")

    print("\n=== Memoria livre limita a alocacao ===")
    print(f"{'LIVRE':<10} | {'ALOCADO':<9} | RESERVA P/ SISTEMA")
    print("-" * 50)
    for avail in (8000, 4000, 2500, 1800):
        alloc = compute_automatic_ram(11323, 0, available=avail)
        reserve = avail - alloc
        ok = reserve >= 1536 or alloc == 512
        failures += 0 if ok else 1
        mark = "" if ok else "   <-- FALHOU"
        print(f"{avail:>5} MB   | {alloc:>5} MB  | {reserve:>6} MB{mark}")

    print("\n=== Comparacao com o comportamento anterior ===")
    old = 10296   # valor observado no log do usuario
    new = compute_automatic_ram(11323)
    print(f"  antes: {old} MB ({old/11323*100:.0f}% da RAM) -> sobra {11323-old} MB")
    print(f"  agora: {new} MB ({new/11323*100:.0f}% da RAM) -> sobra {11323-new} MB")
    assert new < old, "a nova alocacao deveria ser menor"
    assert 11323 - new >= 2048, "precisa sobrar pelo menos 2 GB para o sistema"

    # Aparelho fraco continua funcional
    assert compute_automatic_ram(1024) >= 512
    assert compute_automatic_ram(512) == 512
    print("\nAparelhos fracos mantem o piso de 512 MB: ok")

    # -Xms deve ser metade do -Xmx, no minimo 512
    for alloc in (512, 2048, 4096):
        xms = max(512, alloc // 2)
        assert xms <= alloc, "-Xms nao pode exceder -Xmx"
    print("-Xms sempre menor ou igual a -Xmx: ok")

    print(f"\nDivergencias: {failures}")
    assert failures == 0
    print("OK - todas as assercoes passaram")


if __name__ == "__main__":
    main()
