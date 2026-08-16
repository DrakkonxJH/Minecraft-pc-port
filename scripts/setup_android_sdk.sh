#!/usr/bin/env bash
#
# setup_android_sdk.sh - instala o Android SDK/NDK necessario para o MineDrakk Java
# sem precisar do Android Studio.
#
# Baixa as command-line tools oficiais do Google e instala exatamente os
# componentes que o build exige, depois escreve o local.properties.
#
# Uso:
#     bash scripts/setup_android_sdk.sh                 # instala em ~/Android/Sdk
#     bash scripts/setup_android_sdk.sh /caminho/do/sdk # instala onde voce quiser
#
# Se voce JA tem o Android Studio instalado, nao precisa deste script:
#     bash scripts/setup_android_sdk.sh --link-only
# apenas detecta o SDK existente e escreve o local.properties.
#
set -euo pipefail

# Versoes exigidas por app_pojavlauncher/build.gradle
readonly COMPILE_SDK=37
readonly BUILD_TOOLS="36.0.0"
readonly NDK_VERSION="27.3.13750724"
readonly CMDLINE_TOOLS_URL="https://dl.google.com/android/repository/commandlinetools-linux-13114758_latest.zip"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

write_local_properties() {
    local sdk_dir="$1"
    local target="${PROJECT_ROOT}/local.properties"
    # local.properties e ignorado pelo git de proposito: o caminho e por maquina.
    printf 'sdk.dir=%s\n' "$sdk_dir" > "$target"
    log "local.properties escrito: sdk.dir=${sdk_dir}"
}

detect_existing_sdk() {
    local candidates=(
        "${ANDROID_HOME:-}"
        "${ANDROID_SDK_ROOT:-}"
        "$HOME/Android/Sdk"
        "$HOME/.local/share/Android/Sdk"
        "/usr/lib/android-sdk"
        "/opt/android-sdk"
    )
    for c in "${candidates[@]}"; do
        [ -n "$c" ] && [ -d "$c/platforms" ] && { echo "$c"; return 0; }
    done
    return 1
}

# --- modo --link-only: so aponta para um SDK ja instalado -------------------
if [ "${1:-}" = "--link-only" ]; then
    if sdk="$(detect_existing_sdk)"; then
        log "SDK encontrado em ${sdk}"
        write_local_properties "$sdk"
        exit 0
    fi
    die "Nenhum SDK encontrado. Rode sem --link-only para instalar."
fi

SDK_DIR="${1:-$HOME/Android/Sdk}"

command -v curl    >/dev/null || die "curl nao encontrado"
command -v unzip   >/dev/null || die "unzip nao encontrado (sudo apt install unzip)"
command -v java    >/dev/null || die "java nao encontrado (instale o JDK 21)"

java_major="$(java -version 2>&1 | head -1 | grep -oE '[0-9]+' | head -1)"
[ "$java_major" -ge 17 ] 2>/dev/null || warn "JDK ${java_major} detectado; o build espera 17 ou 21"

log "Instalando o Android SDK em: ${SDK_DIR}"
mkdir -p "$SDK_DIR"

# --- command-line tools -----------------------------------------------------
SDKMANAGER="${SDK_DIR}/cmdline-tools/latest/bin/sdkmanager"
if [ ! -x "$SDKMANAGER" ]; then
    log "Baixando as command-line tools do Android..."
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' EXIT
    curl -fsSL --retry 3 -o "$tmp/cmdline.zip" "$CMDLINE_TOOLS_URL" \
        || die "Falha ao baixar as command-line tools"
    unzip -q "$tmp/cmdline.zip" -d "$tmp"
    # O zip extrai em cmdline-tools/; o sdkmanager exige o layout .../latest/
    mkdir -p "${SDK_DIR}/cmdline-tools"
    rm -rf "${SDK_DIR}/cmdline-tools/latest"
    mv "$tmp/cmdline-tools" "${SDK_DIR}/cmdline-tools/latest"
    log "Command-line tools instaladas"
else
    log "Command-line tools ja presentes"
fi

export ANDROID_HOME="$SDK_DIR"
export ANDROID_SDK_ROOT="$SDK_DIR"

# --- licencas ---------------------------------------------------------------
log "Aceitando as licencas do SDK..."
yes | "$SDKMANAGER" --sdk_root="$SDK_DIR" --licenses >/dev/null 2>&1 || true

# --- componentes ------------------------------------------------------------
log "Instalando componentes (isso baixa ~2 GB e demora)..."
"$SDKMANAGER" --sdk_root="$SDK_DIR" \
    "platform-tools" \
    "platforms;android-${COMPILE_SDK}" \
    "build-tools;${BUILD_TOOLS}" \
    "ndk;${NDK_VERSION}" \
    || die "Falha ao instalar os componentes do SDK"

write_local_properties "$SDK_DIR"

echo
log "Verificacao:"
for p in "platforms/android-${COMPILE_SDK}" "build-tools/${BUILD_TOOLS}" "ndk/${NDK_VERSION}" "platform-tools"; do
    printf '    %-34s ' "$p"
    [ -d "${SDK_DIR}/${p}" ] && echo "ok" || echo "AUSENTE"
done

echo
log "Pronto. Compile com:"
echo "    ./gradlew :app_pojavlauncher:assembleDebug"
echo
log "Opcional, para usar o adb no terminal, adicione ao ~/.bashrc:"
echo "    export ANDROID_HOME=\"${SDK_DIR}\""
echo "    export PATH=\"\$PATH:${SDK_DIR}/platform-tools\""
