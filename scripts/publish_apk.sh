#!/usr/bin/env bash
#
# publish_apk.sh - publica o APK compilado como uma GitHub Release,
# para baixar direto pelo navegador do celular, sem cabo.
#
# Por que uma Release e nao um commit:
#   O APK tem centenas de MB. O GitHub REJEITA arquivos acima de 100 MB dentro
#   do repositorio Git, mas aceita ate 2 GB como anexo de Release.
#
# Uso:
#     bash scripts/publish_apk.sh              # usa a versao de build.gradle
#     bash scripts/publish_apk.sh 0.2.0        # publica como v0.2.0
#
# A versao vem de `ext.minedrakkVersion` em app_pojavlauncher/build.gradle.
# Passar um argumento ATUALIZA esse arquivo antes de publicar, mantendo
# repositorio e APK sempre em sincronia.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
GRADLE_FILE="${PROJECT_ROOT}/app_pojavlauncher/build.gradle"
REPO="DrakkonxJH/Minecraft-pc-port"
cd "$PROJECT_ROOT"

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

command -v gh >/dev/null || die "GitHub CLI (gh) nao encontrado. Instale: https://cli.github.com
Alternativa sem gh: crie a release pelo site em
  https://github.com/${REPO}/releases/new
e arraste o MineDrakk.apk para os anexos."
gh auth status >/dev/null 2>&1 || die "gh nao autenticado. Rode: gh auth login"

current_version() {
    grep -oP 'ext\.minedrakkVersion\s*=\s*"\K[0-9]+\.[0-9]+\.[0-9]+' "$GRADLE_FILE"
}

VERSION="${1:-}"
if [ -n "$VERSION" ]; then
    [[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] \
        || die "Versao invalida: '$VERSION'. Use o formato MAJOR.MINOR.PATCH (ex.: 0.2.0)"
    OLD="$(current_version)"
    if [ "$OLD" != "$VERSION" ]; then
        sed -i "s/ext\.minedrakkVersion = \"${OLD}\"/ext.minedrakkVersion = \"${VERSION}\"/" "$GRADLE_FILE"
        log "Versao do projeto: ${OLD} -> ${VERSION}"
        warn "build.gradle foi alterado. Recompile antes de publicar:"
        warn "    ./gradlew :app_pojavlauncher:assembleDebug"
        warn "Depois rode este script de novo, sem argumentos."
        exit 0
    fi
else
    VERSION="$(current_version)"
fi
[ -n "$VERSION" ] || die "Nao consegui ler ext.minedrakkVersion de build.gradle"

TAG="v${VERSION}"
log "Publicando ${TAG}"

# --- localiza o APK ---------------------------------------------------------
APK=""
for c in "${PROJECT_ROOT}/MineDrakk.apk" \
         "${PROJECT_ROOT}/app_pojavlauncher/build/outputs/apk/debug/app_pojavlauncher-debug.apk"; do
    [ -f "$c" ] && { APK="$c"; break; }
done
[ -n "$APK" ] || APK="$(find . -name '*.apk' -path '*/outputs/apk/debug/*' -type f 2>/dev/null | head -1)"
[ -n "$APK" ] || die "Nenhum APK encontrado. Compile primeiro:
    ./gradlew :app_pojavlauncher:assembleDebug"

SIZE="$(du -h "$APK" | cut -f1)"
COMMIT="$(git rev-parse --short HEAD)"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
log "APK: ${APK#$PROJECT_ROOT/} (${SIZE})"

if [ -n "$(git status --porcelain)" ]; then
    warn "Ha alteracoes nao commitadas: a release pode nao refletir o codigo do repositorio."
fi

# --- empacota ---------------------------------------------------------------
UPLOAD_NAME="MineDrakk-${VERSION}.apk"
TMP_DIR="$(mktemp -d)"; trap 'rm -rf "$TMP_DIR"' EXIT
cp "$APK" "${TMP_DIR}/${UPLOAD_NAME}"
( cd "$TMP_DIR" && sha256sum "$UPLOAD_NAME" > "${UPLOAD_NAME}.sha256" )

NOTES="$(cat <<EOF
Build de teste do **MineDrakk Java**.

| | |
|---|---|
| Versao | \`${VERSION}\` |
| Commit | \`${COMMIT}\` |
| Branch | \`${BRANCH}\` |
| Tipo | debug (assinado com a chave de debug) |
| Tamanho | ${SIZE} |

### Instalacao

1. Baixe o \`.apk\` abaixo pelo navegador do celular
2. Toque no arquivo baixado
3. Autorize **"instalar de fontes desconhecidas"** se o Android pedir

Instala como **MineDrakk Java (Debug)** e convive com outros launchers no
mesmo aparelho.

> Build de debug: nao e publicavel na Play Store e roda mais devagar que um
> build de release. Serve para testar.
EOF
)"

# --- cria a tag no git ------------------------------------------------------
if ! git rev-parse "$TAG" >/dev/null 2>&1; then
    git tag -a "$TAG" -m "MineDrakk ${VERSION}"
    git push origin "$TAG"
    log "Tag ${TAG} criada e enviada"
fi

log "Publicando a release..."
if gh release view "$TAG" --repo "$REPO" >/dev/null 2>&1; then
    warn "A release ${TAG} ja existe; substituindo os arquivos."
    gh release upload "$TAG" \
        "${TMP_DIR}/${UPLOAD_NAME}" "${TMP_DIR}/${UPLOAD_NAME}.sha256" \
        --repo "$REPO" --clobber
else
    gh release create "$TAG" \
        "${TMP_DIR}/${UPLOAD_NAME}" "${TMP_DIR}/${UPLOAD_NAME}.sha256" \
        --repo "$REPO" \
        --title "MineDrakk Java ${VERSION}" \
        --notes "$NOTES" \
        --prerelease
fi

echo
log "Pronto. Baixe pelo celular em:"
echo "    https://github.com/${REPO}/releases/tag/${TAG}"
