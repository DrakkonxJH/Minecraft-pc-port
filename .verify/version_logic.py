"""Port 1:1 da logica corrigida em Tools.java (AUDITORIA 5.2 e 5.3),
comparada com a implementacao antiga, para provar que os crashes e o
downgrade indevido deixam de ocorrer."""


# ---------- implementacao NOVA (espelha o Java) ----------
def version_component(components, index):
    if components is None or index >= len(components):
        return -1
    raw = components[index].strip()
    end = 0
    while end < len(raw) and raw[end].isdigit():
        end += 1
    if end == 0:
        return -1
    return int(raw[:end])


def version_at_least(components, min_major, min_minor):
    major = version_component(components, 0)
    if major < 0:
        return False
    if major != min_major:
        return major > min_major
    minor = version_component(components, 1)
    if minor < 0:
        return False
    return minor >= min_minor


# ---------- implementacao ANTIGA (com bugs) ----------
def old_behaviour(lib_name):
    try:
        version = lib_name.split(":")[2].split(".")
        skip = int(version[0]) >= 5 and int(version[1]) >= 13
        return "mantem" if skip else "troca p/ 5.13.0"
    except IndexError:
        return "CRASH: ArrayIndexOutOfBounds"
    except ValueError:
        return "CRASH: NumberFormatException"


def new_behaviour(lib_name):
    if lib_name is None:
        return "ignorado"
    name_parts = lib_name.split(":")
    if len(name_parts) < 3:
        return "ignorado (coordenada malformada)"
    version = name_parts[2].split(".")
    return "mantem" if version_at_least(version, 5, 13) else "troca p/ 5.13.0"


CASES = [
    ("net.java.dev.jna:jna:5.13.0", "mantem"),
    ("net.java.dev.jna:jna:5.14.0", "mantem"),
    ("net.java.dev.jna:jna:6.2.1", "mantem"),            # 5.3: antigo fazia downgrade
    ("net.java.dev.jna:jna:6.0.0", "mantem"),            # 5.3: idem
    ("net.java.dev.jna:jna:4.5.2", "troca p/ 5.13.0"),
    ("net.java.dev.jna:jna:5.12.9", "troca p/ 5.13.0"),
    ("net.java.dev.jna:jna:5.13.0-SNAPSHOT", "mantem"),  # 5.2
    ("net.java.dev.jna:jna:5", "troca p/ 5.13.0"),       # 5.2
    ("net.java.dev.jna:jna:2.0.0-beta", "troca p/ 5.13.0"),
    ("net.java.dev.jna:jna:1.0.0+build1", "troca p/ 5.13.0"),
    ("grupo:artefato", "ignorado (coordenada malformada)"),
]


def main():
    print(f"{'LIBRARY':<38} | {'ANTIGO':<28} | {'NOVO':<32} | ESPERADO")
    print("-" * 125)
    crashes = downgrades = failures = 0
    for lib, expected in CASES:
        old = old_behaviour(lib)
        new = new_behaviour(lib)
        if old.startswith("CRASH"):
            crashes += 1
        if old == "troca p/ 5.13.0" and new == "mantem":
            downgrades += 1
        ok = new == expected
        if not ok:
            failures += 1
        mark = "" if ok else "   <-- FALHOU"
        print(f"{lib:<38} | {old:<28} | {new:<32} | {expected}{mark}")
    print("-" * 125)
    print(f"Crashes evitados pela correcao 5.2 : {crashes}")
    print(f"Downgrades indevidos evitados (5.3): {downgrades}")
    print(f"Divergencias do esperado           : {failures}")
    assert failures == 0, "A nova implementacao divergiu do comportamento esperado"
    assert crashes > 0 and downgrades > 0, "O teste deveria demonstrar ambos os problemas"
    print("\nOK - todas as assercoes passaram")


if __name__ == "__main__":
    main()
