#!/usr/bin/env bash
#
# get_apk.sh - localiza o APK gerado pelo build e copia para a raiz do projeto
# com um nome facil de achar.
#
# Desde que o build passou a gerar APKs separados por arquitetura, este script
# escolhe automaticamente o menor APK que funciona no aparelho conectado. Se
# nao houver aparelho conectado, prefere arm64-v8a (praticamente todo celular
# desde 2017) e informa como pegar o universal.
#
# Uso:
#     bash scripts/get_apk.sh              # escolha automatica
#     bash scripts/get_apk.sh universal    # forca o APK com todas as ABIs
#     bash scripts/get_apk.sh arm64-v8a    # forca uma ABI especifica
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

cd "$PROJECT_ROOT"

WANTED="${1:-}"

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

# ---------------------------------------------------------------------------
# Descobre a ABI do aparelho conectado, se houver um
# ---------------------------------------------------------------------------
detect_device_abi() {
    local adb="${HOME}/Android/Sdk/platform-tools/adb"
    command -v adb >/dev/null 2>&1 && adb="$(command -v adb)"
    [ -x "$adb" ] || return 1
    # Só faz sentido se houver exatamente um aparelho pronto
    local count
    count="$("$adb" devices 2>/dev/null | grep -cw 'device' || true)"
    [ "$count" = "1" ] || return 1
    "$adb" shell getprop ro.product.cpu.abi 2>/dev/null | tr -d '\r\n'
}

# Escolhe entre os APKs disponiveis o que casa com o padrao dado
pick_by_pattern() {
    local pattern="$1"
    for apk in "${APKS[@]}"; do
        case "$apk" in
            */debug/*"$pattern"*) echo "$apk"; return 0 ;;
        esac
    done
    for apk in "${APKS[@]}"; do
        case "$apk" in
            *"$pattern"*) echo "$apk"; return 0 ;;
        esac
    done
    return 1
}

CHOSEN=""
REASON=""

if [ -n "$WANTED" ]; then
    CHOSEN="$(pick_by_pattern "$WANTED" || true)"
    [ -n "$CHOSEN" ] || die "Nenhum APK correspondente a '$WANTED'."
    REASON="escolhido por voce"
else
    DEVICE_ABI="$(detect_device_abi || true)"
    if [ -n "${DEVICE_ABI:-}" ]; then
        CHOSEN="$(pick_by_pattern "$DEVICE_ABI" || true)"
        [ -n "$CHOSEN" ] && REASON="corresponde ao aparelho conectado (${DEVICE_ABI})"
    fi
    if [ -z "$CHOSEN" ]; then
        CHOSEN="$(pick_by_pattern "arm64-v8a" || true)"
        [ -n "$CHOSEN" ] && REASON="arm64-v8a, compativel com quase todo celular atual"
    fi
    if [ -z "$CHOSEN" ]; then
        CHOSEN="$(pick_by_pattern "universal" || true)"
        [ -n "$CHOSEN" ] && REASON="universal (todas as arquiteturas)"
    fi
    if [ -z "$CHOSEN" ]; then
        CHOSEN="$(ls -t "${APKS[@]}" | head -1)"
        REASON="mais recente"
    fi
fi

DEST="${PROJECT_ROOT}/MineDrakk.apk"
cp "$CHOSEN" "$DEST"

log "APK copiado para:"
echo "    ${DEST}"
echo "    tamanho: $(du -h "$DEST" | cut -f1)"
echo "    origem:  ${CHOSEN#./}"
echo "    motivo:  ${REASON}"
echo

if [ -z "$WANTED" ]; then
    echo "Para instalar em um aparelho de outra arquitetura, use o universal:"
    echo "    bash scripts/get_apk.sh universal"
    echo
fi

log "Para instalar por cabo USB (com Depuracao USB ativada no celular):"
ADB="${HOME}/Android/Sdk/platform-tools/adb"
if [ -x "$ADB" ]; then
    echo "    $ADB install -r \"$DEST\""
else
    echo "    adb install -r \"$DEST\""
fi
echo
log "Ou copie o arquivo MineDrakk.apk para o celular e toque nele."
