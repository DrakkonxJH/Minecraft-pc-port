#!/usr/bin/env python3
"""
Verifica a logica do gerenciador de mods.

O risco aqui e diferente do resto do projeto: este codigo RENOMEIA e APAGA
arquivos do usuario. Um erro de parsing de nome nao trava o app -- ele
desativa o mod errado, ou apaga o arquivo errado, e o usuario so descobre
quando o jogo abre sem o mod que ele queria.

Verificamos:
  1. O par ativar/desativar e reversivel e nunca perde o nome original.
  2. A extracao de nome e versao nao quebra com os padroes reais de nomes de
     mod (que variam muito entre autores).
  3. A extracao da versao do Minecraft do id do perfil ignora a versao do
     loader -- confundir as duas mandaria o usuario para o catalogo filtrado
     pela versao errada.
"""
import re
import sys

FAILURES = []


def check(cond, msg):
    if not cond:
        FAILURES.append(msg)


DISABLED = '.disabled'


def file_name(name):
    """Espelha ModEntry.getFileName()."""
    if name.lower().endswith(DISABLED):
        return name[:-len(DISABLED)]
    return name


def is_enabled(name):
    return name.lower().endswith('.jar')


def toggle(name, enabled):
    """Espelha ModEntry.setEnabled()."""
    if enabled == is_enabled(name):
        return name
    return file_name(name) if enabled else file_name(name) + DISABLED


def display_name(name):
    """Espelha ModEntry.getDisplayName()."""
    n = file_name(name)
    if n.lower().endswith('.jar'):
        n = n[:-4]
    cut = -1
    for i in range(1, len(n) - 1):
        if n[i] in '-_+' and n[i + 1].isdigit():
            cut = i
            break
    if cut > 0:
        n = n[:cut]
    return n.replace('_', ' ').strip()


def version_hint(name):
    """Espelha ModEntry.getVersionHint()."""
    n = file_name(name)
    if n.lower().endswith('.jar'):
        n = n[:-4]
    for i in range(1, len(n) - 1):
        if n[i] in '-_+' and n[i + 1].isdigit():
            return n[i + 1:]
    return ''


def _is_game_version(part):
    return bool(re.fullmatch(r'\d+\.\d+(\.\d+)?', part)) and not part.startswith('0.')


def extract_mc_version(version_id):
    """Espelha ModManagerFragment.extractMinecraftVersion()."""
    if not version_id:
        return ''
    parts = re.split(r'[-_]', version_id)
    loaders = ('forge', 'neoforge', 'fabric', 'quilt', 'optifine', 'lwjgl3ify')
    loader_index = -1
    for i, p in enumerate(parts):
        if p.lower() in loaders:
            loader_index = i
            break
    if loader_index > 0:
        for i in range(loader_index - 1, -1, -1):
            if _is_game_version(parts[i]):
                return parts[i]
    best = ''
    for p in parts:
        if _is_game_version(p):
            best = p
    return best


# --- 1. Ativar/desativar e reversivel ---------------------------------------
NAMES = [
    'sodium-fabric-0.5.8+mc1.20.1.jar',
    'lithium-fabric-mc1.21.11-0.21.4.jar',
    'Mod Menu 17.0.0.jar',
    'no-telemetry-1.10.0.jar',
    'fabric-api-0.141.3+1.21.11.jar',
    'JEI_1.20.1-15.2.0.27.jar',
    'mod.with.dots-1.0.jar',
]
for original in NAMES:
    off = toggle(original, False)
    check(off.endswith(DISABLED), f"{original}: desativar nao acrescentou {DISABLED}")
    check(not is_enabled(off), f"{original}: continua ativo apos desativar")
    back = toggle(off, True)
    check(back == original,
          f"{original}: ativar de novo deu '{back}', deveria voltar ao original")
    # Desativar duas vezes nao pode acumular sufixo
    twice = toggle(off, False)
    check(twice == off, f"{original}: desativar duas vezes acumulou sufixo -> {twice}")
    # Ativar um mod ja ativo nao muda nada
    check(toggle(original, True) == original,
          f"{original}: ativar um mod ja ativo alterou o nome")

# --- 2. Nome e versao para exibicao -----------------------------------------
CASES = [
    ('sodium-fabric-0.5.8+mc1.20.1.jar', 'sodium-fabric', '0.5.8+mc1.20.1'),
    ('lithium-fabric-mc1.21.11-0.21.4.jar', 'lithium-fabric-mc1.21.11', '0.21.4'),
    ('no-telemetry-1.10.0.jar', 'no-telemetry', '1.10.0'),
    ('fabric-api-0.141.3+1.21.11.jar', 'fabric-api', '0.141.3+1.21.11'),
]
for filename, expect_name, expect_version in CASES:
    got_name = display_name(filename)
    got_version = version_hint(filename)
    check(got_name == expect_name,
          f"{filename}: nome '{got_name}', esperado '{expect_name}'")
    check(got_version == expect_version,
          f"{filename}: versao '{got_version}', esperado '{expect_version}'")

# Nunca pode devolver string vazia: a lista ficaria com uma linha em branco
for filename in NAMES + [f + DISABLED for f in NAMES]:
    check(display_name(filename).strip() != '',
          f"{filename}: nome de exibicao vazio")

# Nome sem versao nenhuma continua legivel
check(display_name('OptiFine.jar') == 'OptiFine', 'nome sem versao foi alterado')
check(version_hint('OptiFine.jar') == '', 'versao inventada para nome sem versao')

# --- 3. Versao do Minecraft a partir do id do perfil ------------------------
PROFILES = [
    # (id do perfil, versao do jogo esperada)
    ('fabric-loader-0.18.6-1.21.11', '1.21.11'),
    ('fabric-loader-0.16.5-1.20.1', '1.20.1'),
    ('1.21-forge-51.0.33', '1.21'),
    ('1.20.1-forge-47.2.0', '1.20.1'),
    ('neoforge-21.1.65', '21.1.65'),
    ('1.21.11', '1.21.11'),
    ('quilt-loader-0.26.0-1.21.1', '1.21.1'),
]
for profile_id, expected in PROFILES:
    got = extract_mc_version(profile_id)
    check(got == expected,
          f"'{profile_id}': extraiu '{got}', esperado '{expected}'")

# A versao do loader (comeca com 0.) nunca pode ser confundida com a do jogo
for profile_id in ('fabric-loader-0.18.6-1.21.11', 'quilt-loader-0.26.0-1.21.1'):
    got = extract_mc_version(profile_id)
    check(not got.startswith('0.'),
          f"'{profile_id}': devolveu a versao do loader ({got}) em vez da do jogo")

# Entrada vazia ou estranha nao pode lancar
for weird in ('', None, '---', 'latest-release', 'my custom profile'):
    try:
        extract_mc_version(weird)
    except Exception as e:  # noqa: BLE001
        FAILURES.append(f"extract_mc_version({weird!r}) lancou {e}")

if FAILURES:
    print("FALHAS:")
    for f in FAILURES:
        print("  -", f)
    sys.exit(1)

print(f"Gerenciador de mods: {len(NAMES)} nomes, {len(PROFILES)} perfis, "
      f"todas as verificacoes passaram")
