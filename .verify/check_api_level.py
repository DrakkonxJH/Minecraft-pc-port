#!/usr/bin/env python3
"""
Procura usos de APIs Java/Android mais novas que o minSdk do app.

Esta e a classe de bug mais traicoeira do projeto: o codigo compila sem um
aviso sequer (o compilador so olha o sourceCompatibility, nao o minSdk), o app
instala normalmente, e so quebra com NoSuchMethodError/NoClassDefFoundError no
aparelho de quem tem Android antigo -- exatamente os usuarios que nao temos
como testar aqui.

O lint do Android pegaria isso, mas depende do SDK instalado, que nao existe
neste ambiente. Este script cobre os casos mais comuns por busca textual.

Nao pretende ser exaustivo: e uma rede de seguranca para os padroes que
sabidamente aparecem neste codigo.
"""
import os
import re
import sys

JAVA_DIRS = [
    'app_pojavlauncher/src/main/java/net/kdt',
    'app_pojavlauncher/src/main/java/com/kdt',
]
GRADLE = 'app_pojavlauncher/build.gradle'

# Descobre o minSdk real em vez de assumir
with open(GRADLE, encoding='utf-8') as fh:
    gradle = fh.read()
m = re.search(r'minSdkVersion\s+(\d+)', gradle)
MIN_SDK = int(m.group(1)) if m else 21
HAS_DESUGARING = 'coreLibraryDesugaring' in gradle

# (regex, api_minima, descricao, sugestao)
RULES = [
    (r'\.isBlank\(\)', 30, 'String.isBlank()', 'use trim().isEmpty()'),
    (r'\.strip\(\)', 30, 'String.strip()', 'use trim()'),
    (r'\bString\.join\(', 26, 'String.join()', 'concatene manualmente'),
    (r'\b(?:List|Set|Map)\.of\(', 30, 'List/Set/Map.of()',
     'use new ArrayList<>/HashSet<>/HashMap<>'),
    (r'\b(?:List|Set|Map)\.copyOf\(', 31, 'List/Set/Map.copyOf()',
     'copie com o construtor da colecao'),
    (r'\.chars\(\)', 24, 'CharSequence.chars()', 'itere com charAt()'),
    (r'\bObjects\.requireNonNullElse\(', 30, 'Objects.requireNonNullElse()',
     'use um if explicito'),
    (r'\bFiles\.(?:readAllBytes|write|copy|delete|createDirectories)\(', 26,
     'java.nio.file.Files', 'use java.io.File / streams'),
    (r'\bPaths\.get\(', 26, 'java.nio.file.Paths', 'use java.io.File'),
    (r'\bLocalDate(?:Time)?\.', 26, 'java.time', 'use java.util.Date/Calendar'),
    (r'\bDuration\.of', 26, 'java.time.Duration', 'use milissegundos em long'),
    (r'\bStandardCharsets\.', 19, 'StandardCharsets', ''),
    (r'\.getOrDefault\(', 24, 'Map.getOrDefault()', 'faca get() e cheque null'),
    (r'\.putIfAbsent\(', 24, 'Map.putIfAbsent()', 'cheque containsKey() antes'),
    (r'\.computeIfAbsent\(', 24, 'Map.computeIfAbsent()', 'cheque containsKey() antes'),
    (r'\.forEach\(', 24, 'Iterable.forEach()', 'use um for-each comum'),
    (r'\.removeIf\(', 24, 'Collection.removeIf()', 'use um Iterator explicito'),
    (r'\bOptional\.', 24, 'java.util.Optional', 'cheque null diretamente'),
]

# Trechos que sao de bibliotecas de terceiros embutidas ou ja tratados
SKIP_FILES = {
    # SDL e mantido upstream e tem seus proprios guards de versao
    'org/libsdl/app',
}

findings = []
for base in JAVA_DIRS:
    for root, _, files in os.walk(base):
        if any(skip in root.replace(os.sep, '/') for skip in SKIP_FILES):
            continue
        for f in files:
            if not f.endswith('.java'):
                continue
            path = os.path.join(root, f)
            with open(path, encoding='utf-8') as fh:
                lines = fh.readlines()

            in_block_comment = False
            # Guardas de versao no arquivo: se o arquivo inteiro so roda em
            # SDK novo, nao faz sentido reclamar
            joined = ''.join(lines)
            for lineno, line in enumerate(lines, 1):
                stripped = line.strip()
                if in_block_comment:
                    if '*/' in stripped:
                        in_block_comment = False
                    continue
                if stripped.startswith('/*'):
                    if '*/' not in stripped:
                        in_block_comment = True
                    continue
                if stripped.startswith('//') or stripped.startswith('*'):
                    continue

                for pattern, api, name, hint in RULES:
                    if api <= MIN_SDK:
                        continue
                    if HAS_DESUGARING and api <= 26:
                        continue  # desugaring cobre java.time/Files basicos
                    if not re.search(pattern, line):
                        continue
                    # Guarda de versao na propria linha ou nas 6 anteriores
                    context = ''.join(lines[max(0, lineno - 7):lineno])
                    if re.search(r'SDK_INT\s*[<>=]|VERSION_CODES|RequiresApi|'
                                 r'ChecksSdkIntAtLeast', context):
                        continue
                    findings.append(
                        (path, lineno, name, api, hint, stripped[:90]))

print(f"minSdk={MIN_SDK}  desugaring={'sim' if HAS_DESUGARING else 'nao'}")
if findings:
    print(f"\nAPIs acima do minSdk (compilam, mas quebram em aparelho antigo):")
    for path, lineno, name, api, hint, code in findings:
        suffix = f" -- {hint}" if hint else ""
        print(f"  - {path}:{lineno}")
        print(f"      {name} exige API {api}{suffix}")
        print(f"      {code}")
    sys.exit(1)

print("Nenhuma API acima do minSdk encontrada nos padroes verificados")
