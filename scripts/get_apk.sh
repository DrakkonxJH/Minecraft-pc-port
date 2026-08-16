#!/usr/bin/env bash
#
# get_apk.sh - localiza o APK gerado pelo build e copia para a raiz do projeto
# com um nome facil de achar.
#
# Uso:
#     bash scripts/get_apk.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

cd "$PROJECT_ROOT"

log "Procurando APKs em ${PROJECT_ROOT}..."
mapfile -t APKS < <(find . -name '*.apk' -path '*/outputs/apk/*' -type f 2>/dev/null | sort)

if [ "${#APKS[@]}" -eq 0 ]; then
    warn "Nenhum APK encontrado."
    echo
    echo "O build provavelmente ainda nao rodou (ou falhou). Compile com:"
    echo "    ./gradlew :app_pojavlauncher:assembleDebug"
    echo
    echo "Se voce acabou de rodar 'git pull', precisa recompilar para pegar"
    echo "as correcoes mais recentes."
    exit 1
fi

echo
printf '%-62s %10s  %s\n' "ARQUIVO" "TAMANHO" "MODIFICADO"
printf '%s\n' "--------------------------------------------------------------------------------------------"
for apk in "${APKS[@]}"; do
    printf '%-62s %10s  %s\n' \
        "${apk#./}" \
        "$(du -h "$apk" | cut -f1)" \
        "$(date -r "$apk" '+%d/%m %H:%M')"
done
echo

# Pega o debug se existir, senao o mais recente
CHOSEN=""
for apk in "${APKS[@]}"; do
    case "$apk" in
        */debug/*) CHOSEN="$apk"; break ;;
    esac
done
[ -z "$CHOSEN" ] && CHOSEN="$(ls -t "${APKS[@]}" | head -1)"

DEST="${PROJECT_ROOT}/MineDrakk.apk"
cp "$CHOSEN" "$DEST"

log "APK copiado para:"
echo "    ${DEST}"
echo "    tamanho: $(du -h "$DEST" | cut -f1)"
echo

log "Para instalar por cabo USB (com Depuracao USB ativada no celular):"
ADB="${HOME}/Android/Sdk/platform-tools/adb"
if [ -x "$ADB" ]; then
    echo "    $ADB install -r \"$DEST\""
else
    echo "    adb install -r \"$DEST\""
fi
echo
log "Ou copie o arquivo MineDrakk.apk para o celular e toque nele."
