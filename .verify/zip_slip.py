"""Valida a guarda de Zip Slip adicionada em ZipUtils.zipExtract (AUDITORIA 4.3).
Espelha a logica Java: canonicalDestination = destino canonico + separador,
e cada entrada precisa comecar por esse prefixo."""

import os
import tempfile

def resolve(destination, entry_name, dir_name=""):
    """Equivalente a new File(destination, entryName.substring(dirNameLen))."""
    return os.path.join(destination, entry_name[len(dir_name):])

def is_inside_directory(target, canonical_dir_with_sep):
    """Equivalente a ZipUtils.isInsideDirectory()."""
    return os.path.realpath(target).startswith(canonical_dir_with_sep)

def extract_allowed(destination, entry_name, dir_name=""):
    canonical_destination = os.path.realpath(destination) + os.sep
    target = resolve(destination, entry_name, dir_name)
    return is_inside_directory(target, canonical_destination)

CASES = [
    # (entrada no zip, deve ser permitida?)
    ("mods/sodium.jar",                                   True),
    ("config/nested/deep/settings.toml",                  True),
    ("assets/minecraft/textures/block/stone.png",         True),
    ("normal.txt",                                        True),
    ("./relative/but/fine.txt",                           True),
    ("mods/../mods/ok.jar",                               True),   # normaliza p/ dentro
    ("../../../../data/data/com.drakkonx.minedrakk/files/x", False),
    ("../evil.sh",                                        False),
    ("mods/../../../../../etc/passwd",                    False),
    ("../../sibling/escape.txt",                          False),
]

def main():
    with tempfile.TemporaryDirectory() as tmp:
        destination = os.path.join(tmp, "modpack_install")
        os.makedirs(destination, exist_ok=True)

        print(f"{'ENTRADA DO ZIP':<56} | {'RESULTADO':<9} | ESPERADO")
        print("-" * 92)
        failures = 0
        blocked = 0
        for entry, should_allow in CASES:
            allowed = extract_allowed(destination, entry)
            if not allowed:
                blocked += 1
            ok = allowed == should_allow
            if not ok:
                failures += 1
            result = "permitido" if allowed else "BLOQUEADO"
            expected = "permitido" if should_allow else "BLOQUEADO"
            mark = "" if ok else "   <-- FALHOU"
            print(f"{entry:<56} | {result:<9} | {expected}{mark}")

        print("-" * 92)
        print(f"Entradas maliciosas bloqueadas: {blocked}")
        print(f"Divergencias: {failures}")
        assert failures == 0, "A guarda divergiu do comportamento esperado"
        assert blocked == 4, f"Esperava bloquear 4 entradas, bloqueou {blocked}"
        print("\nOK - todas as assercoes passaram")

if __name__ == "__main__":
    main()
