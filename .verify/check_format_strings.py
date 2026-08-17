#!/usr/bin/env python3
"""
Verifica que os placeholders (%d, %s, %.2f...) das strings traduzidas batem com
os da string base em ingles.

Uma incompatibilidade aqui NAO e erro de compilacao: vira um
IllegalFormatConversionException em tempo de execucao, no aparelho do usuario,
e so na lingua afetada. Como o app tem ~60 traducoes e acabamos de adicionar
strings novas com quatro argumentos, vale checar automaticamente.
"""
import os
import re
import sys
import xml.etree.ElementTree as ET

RES = 'app_pojavlauncher/src/main/res'
BASE = os.path.join(RES, 'values', 'strings.xml')

# %1$s, %2$.2f, %d, %s ... O flag de espaco e omitido de proposito: sem ele,
# um "100% is" (percentual literal em texto corrido) nao e confundido com uma
# conversao "% i".
FORMAT = re.compile(r'%(?:(\d+)\$)?[-+#0]*[\d.]*([a-zA-Z])')

# Conversoes que o Java realmente aceita. Qualquer outra letra depois de "%"
# e percentual literal em texto, nao placeholder.
VALID_CONVERSIONS = set('sdfegxobcahnSDFEGXOBCAHN')


def signature(text):
    """
    Assinatura posicional dos placeholders: {posicao: tipo}.
    Para argumentos implicitos (%s sem indice) a posicao e a ordem de aparicao.
    Tipos numericos equivalentes sao normalizados: o que quebra em runtime e
    passar um int onde se espera texto, nao %d vs %.2f.
    """
    result = {}
    implicit = 0
    for index, conv in FORMAT.findall(text):
        if conv not in VALID_CONVERSIONS:
            continue
        if index:
            pos = int(index)
        else:
            implicit += 1
            pos = implicit
        kind = {'d': 'num', 'f': 'num', 'e': 'num', 'x': 'num', 'o': 'num'}.get(
            conv.lower(), conv.lower())
        result[pos] = kind
    return result


def load(path):
    strings = {}
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as e:
        print(f"XML invalido: {path}: {e}")
        sys.exit(1)
    for el in root:
        if el.tag == 'string' and el.get('name'):
            strings[el.get('name')] = ''.join(el.itertext())
    return strings


base = load(BASE)
problems = []

for folder in sorted(os.listdir(RES)):
    if not folder.startswith('values-'):
        continue
    path = os.path.join(RES, folder, 'strings.xml')
    if not os.path.exists(path):
        continue
    for name, text in load(path).items():
        if name not in base:
            continue
        want = signature(base[name])
        got = signature(text)
        # So reportamos o que quebra de verdade em runtime: um placeholder que a
        # traducao usa e a base nao (argumento inexistente -> MissingFormatArgument)
        # ou um tipo diferente na mesma posicao (int onde se espera texto ->
        # IllegalFormatConversion). Uma traducao com MENOS placeholders e
        # inofensiva: o Java simplesmente ignora os argumentos sobrando.
        for pos, kind in got.items():
            if pos not in want:
                problems.append(
                    f"{folder}/{name}: usa %{pos}$ mas a base so tem {len(want)} argumento(s)")
            elif want[pos] != kind:
                problems.append(
                    f"{folder}/{name}: posicao {pos} e '{want[pos]}' na base e '{kind}' na traducao")

# Placeholders nao contiguos na propria base (ex.: usa %1 e %3 mas nao %2)
for name, text in base.items():
    sig = signature(text)
    if sig and sorted(sig) != list(range(1, len(sig) + 1)):
        problems.append(f"values/{name}: indices nao contiguos {sorted(sig)}")

if problems:
    print("Placeholders incompativeis (causariam crash em runtime):")
    for p in problems:
        print("  -", p)
    sys.exit(1)

print(f"Format strings: {len(base)} strings base conferidas, nenhuma divergencia")
