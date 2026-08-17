#!/usr/bin/env python3
"""
Verifica que todo findViewById(R.id.X) tem um @+id/X declarado em algum layout.

Isso NAO e pego pelo compilador: R.id.X existe assim que qualquer layout o
declara, entao remover ou renomear um id em um layout especifico compila
normalmente e devolve null em runtime -- resultando em NullPointerException ao
tocar na tela. O risco e concreto ao reescrever um layout inteiro, que foi o
caso de fragment_select_auth_method.xml.
"""
import os
import re
import sys

RES = 'app_pojavlauncher/src/main/res'
JAVA = 'app_pojavlauncher/src/main/java'

declared = set()
for root, _, files in os.walk(RES):
    folder = os.path.basename(root).split('-')[0]
    if folder not in ('layout', 'menu', 'xml', 'values', 'drawable'):
        continue
    for f in files:
        if not f.endswith('.xml'):
            continue
        with open(os.path.join(root, f), encoding='utf-8') as fh:
            content = fh.read()
        declared |= set(re.findall(r'@\+id/([A-Za-z0-9_]+)', content))
        # <item name="foo" type="id"/> em values/
        declared |= set(re.findall(
            r'<item[^>]*name="([A-Za-z0-9_]+)"[^>]*type="id"', content))
        declared |= set(re.findall(
            r'<item[^>]*type="id"[^>]*name="([A-Za-z0-9_]+)"', content))

# Ids definidos pelo layout interno da androidx.preference, nao por nos
EXTERNAL = {'seekbar', 'seekbar_value'}

used = {}
# O (?<!android\.) descarta android.R.id.content, android.R.id.title,
# android.R.id.copy etc., que sao do framework e sempre existem.
FIND = re.compile(r'(?<!android\.)\bR\.id\.([A-Za-z0-9_]+)')
for root, _, files in os.walk(JAVA):
    for f in files:
        if not f.endswith('.java'):
            continue
        path = os.path.join(root, f)
        with open(path, encoding='utf-8') as fh:
            for lineno, line in enumerate(fh, 1):
                if line.lstrip().startswith('//'):
                    continue
                for name in FIND.findall(line):
                    used.setdefault(name, []).append(f"{path}:{lineno}")

missing = []
for name, places in sorted(used.items()):
    if name in declared or name in EXTERNAL:
        continue
    missing.append(f"R.id.{name} nunca e declarado em nenhum layout\n      " +
                   "\n      ".join(places[:3]))

if missing:
    print("Ids referenciados no Java mas ausentes dos layouts:")
    for m in missing:
        print("  -", m)
    sys.exit(1)

print(f"View ids: {len(used)} referenciados no Java, todos declarados "
      f"({len(declared)} ids no total)")
