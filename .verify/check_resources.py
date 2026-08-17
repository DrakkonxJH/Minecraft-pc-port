#!/usr/bin/env python3
"""
Verifica que toda referencia @string/@drawable/@color/@dimen/@array usada nos
layouts, drawables e telas de preferencia do app existe de fato.

Esse tipo de erro so apareceria no aapt2, e como nao ha JDK/SDK no ambiente de
desenvolvimento do agente, um typo em "@drawable/ic_github" so seria descoberto
na maquina do usuario. As dependencias externas (sdp/ssp, androidx, android:)
sao ignoradas porque nao estao no repositorio.
"""
import os
import re
import sys
import xml.etree.ElementTree as ET

RES = 'app_pojavlauncher/src/main/res'
# @dimen/_12sdp e @dimen/_9ssp vem da biblioteca portrait-sdp, nao do repositorio
EXTERNAL_DIMEN = re.compile(r'^_\d+(sdp|ssp)$')
# Tipos que valem a pena checar; "id" e "style" tem regras proprias de resolucao
TYPES = {'string', 'drawable', 'color', 'dimen', 'array', 'mipmap', 'integer'}

defined = {t: set() for t in TYPES}

# 0) Todo XML precisa ser bem formado. Um "--" dentro de comentario, por
# exemplo, e proibido pela especificacao XML e derruba o aapt2 com uma
# mensagem pouco obvia.
for _root, _dirs, _files in os.walk(RES):
    for _f in _files:
        if not _f.endswith('.xml'):
            continue
        _path = os.path.join(_root, _f)
        try:
            ET.parse(_path)
        except ET.ParseError as _e:
            print(f"XML malformado: {_path}: {_e}")
            sys.exit(1)

# 0b) Recursos duplicados na mesma pasta.
# No Android o nome do recurso e o nome do arquivo SEM extensao, entao
# "notif_icon.png" e "notif_icon.xml" na mesma pasta sao o MESMO recurso e o
# merge falha com "Duplicate resources". E facil criar essa colisao sem
# perceber ao adicionar um vetor para um icone que ja existia como bitmap --
# aconteceu duas vezes neste projeto.
_dup_problems = []
for _entry in sorted(os.listdir(RES)):
    _dir = os.path.join(RES, _entry)
    if not os.path.isdir(_dir):
        continue
    _seen = {}
    for _f in sorted(os.listdir(_dir)):
        if not os.path.isfile(os.path.join(_dir, _f)):
            continue
        _base = _f.split('.')[0]  # cobre tambem os nine-patch (.9.png)
        _seen.setdefault(_base, []).append(_f)
    for _base, _files in _seen.items():
        if len(_files) > 1:
            _dup_problems.append(f"{_entry}/{_base}: {_files}")

if _dup_problems:
    print("Recursos duplicados (o merge do Android vai falhar):")
    for _p in _dup_problems:
        print("  -", _p)
    print("\nDois arquivos com o mesmo nome-base na mesma pasta sao o mesmo "
          "recurso.\nRenomeie um deles ou remova o que nao for usado.")
    sys.exit(1)

# 1) Recursos definidos por valor (<string name=...>, <color name=...>, ...)
for root, _, files in os.walk(RES):
    base = os.path.basename(root)
    if not base.startswith('values'):
        continue
    for f in files:
        if not f.endswith('.xml'):
            continue
        try:
            tree = ET.parse(os.path.join(root, f))
        except ET.ParseError as e:
            print(f"XML invalido: {os.path.join(root, f)}: {e}")
            sys.exit(1)
        for el in tree.getroot():
            name = el.get('name')
            if not name:
                continue
            tag = el.tag
            if tag in ('string', 'color', 'dimen', 'integer'):
                defined[tag].add(name)
            elif tag in ('string-array', 'integer-array', 'array'):
                defined['array'].add(name)
            elif tag == 'item':
                t = el.get('type')
                if t in defined:
                    defined[t].add(name)

# 2) Recursos definidos por arquivo (res/drawable/foo.xml -> @drawable/foo)
for root, _, files in os.walk(RES):
    base = os.path.basename(root)
    folder = base.split('-')[0]
    if folder not in ('drawable', 'mipmap'):
        continue
    for f in files:
        name = f.split('.')[0]  # remove .9.png tambem
        defined[folder].add(name)

# 3b) Recursos gerados pelo Gradle via resValue (nao existem em res/)
with open('app_pojavlauncher/build.gradle', encoding='utf-8') as fh:
    for rtype, rname in re.findall(
            r"""resValue\s+['"](\w+)['"]\s*,\s*['"]([\w.]+)['"]""", fh.read()):
        if rtype in defined:
            defined[rtype].add(rname)

# 3c) Drawables que vem de bibliotecas externas (android_gamepad_remapper)
LIBRARY_DRAWABLES = {
    'button_a', 'button_b', 'button_x', 'button_y', 'button_select', 'button_start',
    'dpad_up', 'dpad_down', 'dpad_left', 'dpad_right',
    'shoulder_left', 'shoulder_right', 'trigger_left', 'trigger_right',
    'stick_left', 'stick_right', 'stick_left_click', 'stick_right_click',
}
defined['drawable'] |= LIBRARY_DRAWABLES

# 3) Referencias usadas
REF = re.compile(r'"@(?:\+)?(string|drawable|color|dimen|array|mipmap|integer)/([A-Za-z0-9_.]+)"')
missing = []
SCAN_DIRS = ['layout', 'xml', 'drawable', 'menu', 'values']
for root, _, files in os.walk(RES):
    folder = os.path.basename(root).split('-')[0]
    if folder not in SCAN_DIRS:
        continue
    for f in files:
        if not f.endswith('.xml'):
            continue
        path = os.path.join(root, f)
        with open(path, encoding='utf-8') as fh:
            content = fh.read()
        for rtype, rname in REF.findall(content):
            if rtype == 'dimen' and EXTERNAL_DIMEN.match(rname):
                continue  # vem da biblioteca portrait-sdp
            if rname not in defined[rtype]:
                missing.append(f"{path}: @{rtype}/{rname} nao existe")

# 4) Referencias a R.* no codigo Java, para os tipos que sabemos mapear.
# O (?<!android\.) evita casar android.R.string.ok, que e do framework.
JAVA_REF = re.compile(
    r'(?<!android\.)\bR\.(string|drawable|color|dimen|array|mipmap|integer)\.([A-Za-z0-9_]+)')
for root, _, files in os.walk('app_pojavlauncher/src/main/java'):
    for f in files:
        if not f.endswith('.java'):
            continue
        path = os.path.join(root, f)
        with open(path, encoding='utf-8') as fh:
            content = fh.read()
        for rtype, rname in JAVA_REF.findall(content):
            if rtype == 'dimen' and EXTERNAL_DIMEN.match(rname):
                continue
            if rname not in defined[rtype]:
                missing.append(f"{path}: R.{rtype}.{rname} nao existe")

if missing:
    print("Referencias quebradas:")
    for m in sorted(set(missing)):
        print("  -", m)
    sys.exit(1)

total = sum(len(v) for v in defined.values())
print(f"Recursos: {total} definidos, nenhuma referencia quebrada")
