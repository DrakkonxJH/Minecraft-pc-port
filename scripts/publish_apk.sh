#!/usr/bin/env bash
#
# publish_apk.sh - publica o APK compilado como uma GitHub Release,
# para que voce (ou qualquer pessoa) possa baixa-lo direto pelo navegador
# do celular, sem precisar de cabo.
#
# Por que uma Release e nao um commit:
#   O APK tem ~250-350 MB. O GitHub REJEITA arquivos acima de 100 MB dentro
#   do repositorio Git, mas aceita ate 2 GB como anexo de Release.
#
# Uso:
#     bash scripts/publish_apk.sh              # versao automatica (data + hash)
#     bash scripts/publish_apk.sh v0.1-teste   # tag escolhida por voce
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "$PROJECT_ROOT"

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

command -v gh >/dev/null || die "GitHub CLI (gh) nao encontrado. Instale: https://cli.github.com
Alternativa sem gh: crie a release pelo site em
  https://github.com/DrakkonxJH/Minecraft-pc-port/releases/new
e arraste o arquivo MineDrakk.apk para a area de anexos."

gh auth status >/dev/null 2>&1 || die "gh nao autenticado. Rode: gh auth login"

# --- localiza o APK ---------------------------------------------------------
APK=""
for candidate in \
    "${PROJECT_ROOT}/MineDrakk.apk" \
    "${PROJECT_ROOT}/app_pojavlauncher/build/outputs/apk/debug/app_pojavlauncher-debug.apk"
do
    [ -f "$candidate" ] && { APK="$candidate"; break; }
done

if [ -z "$APK" ]; then
    APK="$(find . -name '*.apk' -path '*/outputs/apk/debug/*' -type f 2>/dev/null | head -1)"
fi

[ -n "$APK" ] || die "Nenhum APK encontrado. Compile primeiro:
    ./gradlew :app_pojavlauncher:assembleDebug"

SIZE="$(du -h "$APK" | cut -f1)"
log "APK: ${APK#$PROJECT_ROOT/} (${SIZE})"

# --- monta a tag ------------------------------------------------------------
TAG="${1:-debug-$(date +%Y%m%d)-$(git rev-parse --short HEAD)}"
COMMIT="$(git rev-parse --short HEAD)"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"

# Nome amigavel para quem baixa
UPLOAD_NAME="MineDrakk-${TAG}.apk"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
cp "$APK" "${TMP_DIR}/${UPLOAD_NAME}"
( cd "$TMP_DIR" && sha256sum "$UPLOAD_NAME" > "${UPLOAD_NAME}.sha256" )

NOTES="$(cat <<EOF
Build de teste do **MineDrakk Java**.

| | |
|---|---|
| Commit | \`${COMMIT}\` |
| Branch | \`${BRANCH}\` |
| Tipo | debug (assinado com a chave de debug) |
| Tamanho | ${SIZE} |

### Instalação

1. Baixe o \`.apk\` abaixo pelo navegador do celular
2. Toque no arquivo baixado
3. Autorize **"instalar de fontes desconhecidas"** se o Android pedir

Instala como **MineDrakk Java (Debug)** e convive com PojavLauncher ou
Amethyst no mesmo aparelho.

> Build de debug: não é publicável na Play Store e é mais lento que um
> build de release. Serve para testar.
EOF
)"

log "Criando a release '${TAG}'..."
if gh release view "$TAG" --repo DrakkonxJH/Minecraft-pc-port >/dev/null 2>&1; then
    warn "A release '${TAG}' ja existe; enviando o APK por cima."
    gh release upload "$TAG" \
        "${TMP_DIR}/${UPLOAD_NAME}" "${TMP_DIR}/${UPLOAD_NAME}.sha256" \
        --repo DrakkonxJH/Minecraft-pc-port --clobber
else
    gh release create "$TAG" \
        "${TMP_DIR}/${UPLOAD_NAME}" "${TMP_DIR}/${UPLOAD_NAME}.sha256" \
        --repo DrakkonxJH/Minecraft-pc-port \
        --title "MineDrakk Java — ${TAG}" \
        --notes "$NOTES" \
        --prerelease
fi

echo
log "Pronto. Baixe pelo celular em:"
echo "    https://github.com/DrakkonxJH/Minecraft-pc-port/releases/tag/${TAG}"
