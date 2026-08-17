#!/usr/bin/env bash
#
# fetch_jre.sh - baixa os runtimes Java necessarios para o MineDrakk Java.
#
# Resolve o bloqueio B1 da AUDITORIA.md: os JREs nao sao versionados no
# repositorio e o workflow original dependia de artefatos de GitHub Actions,
# que EXPIRAM (90 dias por padrao). Este script usa as *releases* do
# angelauramc-openjdk-build, que sao permanentes.
#
# Uso:
#     bash scripts/fetch_jre.sh            # baixa JRE 8, 17 e 21 (padrao)
#     bash scripts/fetch_jre.sh 8          # apenas o JRE 8
#     bash scripts/fetch_jre.sh 8 17 21 25
#
#     MINEDRAKK_JRE_ARCHES=arm64 bash scripts/fetch_jre.sh
#         baixa apenas a arquitetura indicada
#
# TAMANHO DO APK: por padrao baixa as quatro arquiteturas (arm, arm64, x86,
# x86_64) de cada runtime. Como os runtimes ficam em assets/, e assets NAO sao
# divididos pelo splits.abi, todas elas acabam dentro de TODO APK gerado --
# inclusive o de arm64. Baixar so a arquitetura do seu aparelho reduz bastante
# o APK:
#
#     MINEDRAKK_JRE_ARCHES=arm64 bash scripts/fetch_jre.sh 21
#
# O APK resultante so roda em aparelhos arm64 (praticamente todos desde 2017).
# Para distribuir a terceiros, gere com todas as arquiteturas.
#
# Requisitos: bash, curl, tar (com suporte a xz), sha256sum
#
set -euo pipefail

REPO="AngelAuraMC/angelauramc-openjdk-build"
BASE_URL="https://github.com/${REPO}/releases/download"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSETS_DIR="${SCRIPT_DIR}/../app_pojavlauncher/src/main/assets/components"

# Arquiteturas nomeadas como o app espera (Architecture.archAsString()).
# Pode ser restringido por MINEDRAKK_JRE_ARCHES (lista separada por espaco ou
# virgula) para gerar um APK menor -- ver o cabecalho deste arquivo.
if [ -n "${MINEDRAKK_JRE_ARCHES:-}" ]; then
    IFS=', ' read -r -a ARCHES <<< "$MINEDRAKK_JRE_ARCHES"
    for a in "${ARCHES[@]}"; do
        case "$a" in
            arm|arm64|x86|x86_64) ;;
            *) printf '[x] Arquitetura invalida: %s (use arm, arm64, x86, x86_64)\n' "$a" >&2
               exit 1 ;;
        esac
    done
else
    ARCHES=(arm arm64 x86 x86_64)
fi

# Mapeia a versao do Java para: <tag da release>:<diretorio de destino>
jre_target() {
    case "$1" in
        8)  echo "download_jre8:jre" ;;
        17) echo "download_jre17:jre-new" ;;
        21) echo "download_jre21:jre-21" ;;
        25) echo "download_jre25:jre-25" ;;
        *)  return 1 ;;
    esac
}

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[!]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[x]\033[0m %s\n' "$*" >&2; exit 1; }

command -v curl >/dev/null || die "curl nao encontrado"
command -v tar  >/dev/null || die "tar nao encontrado"

VERSIONS=("$@")
if [ ${#VERSIONS[@]} -eq 0 ]; then
    VERSIONS=(8 17 21)
fi

for version in "${VERSIONS[@]}"; do
    mapping="$(jre_target "$version")" || die "Versao de JRE nao suportada: $version"
    tag="${mapping%%:*}"
    dirname="${mapping##*:}"
    dest="${ASSETS_DIR}/${dirname}"

    log "JRE ${version} -> ${dest}"
    mkdir -p "$dest"

    # O app (AsyncAssetManager) espera, dentro do diretorio do componente:
    #   version              -> identificador do runtime
    #   universal.tar.xz     -> parte independente de arquitetura
    #   bin-<arch>.tar.xz    -> binarios por arquitetura
    #
    # As releases publicam um tarball por arquitetura, entao usamos o de cada
    # arquitetura como bin-<arch>.tar.xz e geramos um universal.tar.xz vazio
    # quando a release nao fornece um separadamente.
    ok=0
    for arch in "${ARCHES[@]}"; do
        asset="jre${version}-android-${arch}.tar.xz"
        url="${BASE_URL}/${tag}/${asset}"
        out="${dest}/bin-${arch}.tar.xz"

        printf '    %-28s ' "${asset}"
        if curl -fsSL --retry 3 --retry-delay 2 -o "${out}.part" "$url" 2>/dev/null; then
            mv "${out}.part" "$out"
            printf 'ok (%s)\n' "$(du -h "$out" | cut -f1)"
            ok=$((ok + 1))
        else
            rm -f "${out}.part"
            printf 'indisponivel\n'
        fi
    done

    [ "$ok" -gt 0 ] || die "Nenhuma arquitetura baixada para o JRE ${version}. Verifique a rede ou a tag '${tag}'."

    # universal.tar.xz: exigido pelo AsyncAssetManager. Se a release nao trouxer
    # um, criamos um tarball vazio valido para nao quebrar a extracao.
    if [ ! -f "${dest}/universal.tar.xz" ]; then
        tmp="$(mktemp -d)"
        tar -cJf "${dest}/universal.tar.xz" -C "$tmp" . 2>/dev/null || \
            warn "Nao foi possivel gerar universal.tar.xz (tar sem suporte a xz?)"
        rmdir "$tmp" 2>/dev/null || true
    fi

    # Arquivo de versao: identifica o runtime instalado e dispara a reinstalacao
    # quando muda. Usamos o hash do conteudo baixado para invalidar corretamente.
    if command -v sha256sum >/dev/null; then
        (cd "$dest" && cat bin-*.tar.xz 2>/dev/null | sha256sum | cut -c1-16) > "${dest}/version"
    else
        printf '%s-%s\n' "$tag" "$(date +%Y%m%d)" > "${dest}/version"
    fi

    log "JRE ${version}: ${ok}/${#ARCHES[@]} arquiteturas, versao $(cat "${dest}/version")"
done

echo
log "Concluido. Agora compile com:"
echo "    ./gradlew :app_pojavlauncher:assembleDebug"
