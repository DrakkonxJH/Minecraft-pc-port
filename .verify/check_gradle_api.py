#!/usr/bin/env python3
"""
Procura APIs do Android Gradle Plugin que foram removidas ou depreciadas na
versao em uso pelo projeto.

Motivacao concreta: a configuracao de versionCode por ABI foi escrita com
`android.applicationVariants`, que e o exemplo que aparece em toda a
documentacao e em praticamente todas as respostas de Stack Overflow -- mas
que foi REMOVIDO no AGP 9. O projeto usa AGP 9.3.1, entao o build quebraria
com "Could not get unknown property 'applicationVariants'" antes de compilar
uma unica classe.

Esse tipo de erro nao aparece em nenhum dos outros verificadores: o Groovy nao
e checado estaticamente, o bloco esta sintaticamente correto, e as chaves estao
balanceadas. So o Gradle real reclamaria.
"""
import os
import re
import sys

FAILURES = []
WARNINGS = []

# (regex, versao AGP em que sumiu, descricao, alternativa)
REMOVED_IN_AGP9 = [
    (r'\bandroid\.applicationVariants\b', 9,
     'android.applicationVariants',
     'use androidComponents.onVariants, ou dispense o ajuste'),
    (r'(?<!//\s)\bapplicationVariants\s*\.\s*(all|each|configureEach)\b', 9,
     'applicationVariants.all/each',
     'use androidComponents.onVariants'),
    (r'\blibraryVariants\s*\.\s*(all|each|configureEach)\b', 9,
     'libraryVariants',
     'use androidComponents.onVariants'),
    (r'\bvariant\.outputs\b.*\boutputFileName\b', 9,
     'output.outputFileName',
     'renomeie o APK depois do build, ou use a Variant Artifacts API'),
    (r'\bBaseVariantOutputImpl\b', 9,
     'BaseVariantOutputImpl (API interna)',
     'nao use APIs internas do AGP'),
    (r'\bvariant\.getAssemble\(\)', 8,
     'variant.getAssemble()',
     'use variant.assembleProvider'),
    (r'\bandroid\.dexOptions\b', 8, 'dexOptions', 'removido, nao ha substituto'),
    (r'\bandroid\.aaptOptions\b', 9, 'aaptOptions', 'use androidResources'),
    (r'\bandroid\.lintOptions\b', 9, 'lintOptions', 'use lint'),
    (r'\bandroid\.adbOptions\b', 9, 'adbOptions', 'use installation'),
    (r'\bcompileSdkVersion\s+\d', 9, 'compileSdkVersion (metodo)',
     'use compileSdk = N'),
    (r'\bbuildToolsVersion\s+["\']', 9, 'buildToolsVersion como metodo',
     'use buildToolsVersion = "..."'),
]


def strip_comments(text):
    """Remove comentarios para nao acusar codigo citado em documentacao."""
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    text = re.sub(r'^\s*//.*$', '', text, flags=re.M)
    return text


def detect_agp_version():
    """Le a versao do AGP declarada no projeto."""
    candidates = ['build.gradle', 'settings.gradle', 'gradle/libs.versions.toml']
    for path in candidates:
        if not os.path.exists(path):
            continue
        with open(path, encoding='utf-8') as fh:
            content = fh.read()
        m = re.search(r'com\.android\.(?:application|tools\.build:gradle)'
                      r'["\']?\s*[:v]?\s*version\s*[\'"]?([\d.]+)', content)
        if m:
            return m.group(1)
        m = re.search(r'id\s+[\'"]com\.android\.application[\'"]\s+version\s+'
                      r'[\'"]([\d.]+)[\'"]', content)
        if m:
            return m.group(1)
        m = re.search(r'com\.android\.tools\.build:gradle:([\d.]+)', content)
        if m:
            return m.group(1)
        m = re.search(r'agp\s*=\s*[\'"]([\d.]+)[\'"]', content)
        if m:
            return m.group(1)
    return None


agp = detect_agp_version()
agp_major = int(agp.split('.')[0]) if agp else None
print(f"AGP detectado: {agp or 'desconhecido'}")

GRADLE_FILES = []
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in
               ('.git', 'build', '.gradle', 'node_modules', '.verify')]
    for f in files:
        if f.endswith('.gradle') or f.endswith('.gradle.kts'):
            GRADLE_FILES.append(os.path.join(root, f))

for path in sorted(GRADLE_FILES):
    with open(path, encoding='utf-8') as fh:
        raw = fh.read()
    content = strip_comments(raw)
    for pattern, removed_in, name, hint in REMOVED_IN_AGP9:
        for m in re.finditer(pattern, content):
            line = content[:m.start()].count('\n') + 1
            msg = f"{path}:~{line}: {name} -- removido/alterado no AGP {removed_in}; {hint}"
            if agp_major is not None and agp_major >= removed_in:
                FAILURES.append(msg)
            else:
                WARNINGS.append(msg)

if WARNINGS:
    print("\nAvisos (ainda funciona no AGP atual, mas some numa versao futura):")
    for w in WARNINGS:
        print("  -", w)

if FAILURES:
    print("\nAPIs REMOVIDAS na versao do AGP em uso (o build vai falhar):")
    for f in FAILURES:
        print("  -", f)
    sys.exit(1)

print(f"{len(GRADLE_FILES)} arquivo(s) Gradle conferidos, "
      f"nenhuma API removida em uso")
