<h1 align="center">MineDrakk Java</h1>

*Um launcher de Minecraft: Java Edition para Android — fork unificado do [PojavLauncher](https://github.com/PojavLauncherTeam/PojavLauncher) e do [Amethyst](https://github.com/AngelAuraMC/Amethyst-Android), com correções próprias de segurança e estabilidade.*

---

## O que é

O MineDrakk Java permite rodar Minecraft: Java Edition em dispositivos Android. Ele executa uma JVM real (OpenJDK portado) no aparelho e traduz as chamadas OpenGL do jogo para OpenGL ES / Vulkan por meio de várias camadas de renderização.

Este projeto **não é um fork simples**. Ele nasce da união de duas bases:

| Origem | O que herdamos |
|---|---|
| [PojavLauncher](https://github.com/PojavLauncherTeam/PojavLauncher) | A base original do launcher (descontinuada em set/2025) |
| [Amethyst-Android](https://github.com/AngelAuraMC/Amethyst-Android) | Toolchain moderna: NDK 27, AGP 9, SDL2, 5 renderers, NeoForge, LWJGL duplo |
| **MineDrakk** | Correções de segurança e estabilidade que **nenhum dos dois** havia feito |

O histórico Git completo de ambos os projetos está preservado neste repositório.

## Por que este fork existe

Fizemos uma auditoria técnica completa das duas bases ([`AUDITORIA.md`](AUDITORIA.md) e [`COMPARATIVO-AMETHYST.md`](COMPARATIVO-AMETHYST.md)) e encontramos problemas que sobreviveram em ambas:

* **Tokens de conta Microsoft/Minecraft vazando em log**, inclusive em builds de release
* **Zip Slip** (path traversal) na extração de modpacks de terceiros
* **Crashes de parsing** que derrubavam o launcher em modpacks com versionamento incomum
* **Proteção contra sobrescrita de bibliotecas internas totalmente inoperante** por um off-by-one
* **`getenv()` sem verificação de nulo** em código nativo (SIGSEGV)
* **Vazamento de memória JNI** a cada lançamento do jogo
* **Keystore de assinatura versionada** no repositório

Todos corrigidos aqui. Veja o histórico de commits para o detalhe de cada um.

## Status

* [x] Base unificada Pojav + Amethyst com histórico preservado
* [x] Bibliotecas nativas alinhadas para 16 KB page size (NDK 27)
* [x] Correções de segurança da auditoria aplicadas
* [x] Correções de estabilidade da auditoria aplicadas
* [x] Assinatura de release desacoplada do repositório
* [ ] `targetSdk 36` (obrigatório para a Google Play desde 31/08/2026)
* [x] Runtimes Java via releases permanentes (bloqueio B1 resolvido)
* [ ] Testes automatizados
* [ ] Criptografia do armazenamento de contas
* [ ] Client ID próprio da Microsoft

## Renderizadores suportados

| Renderer | Descrição |
|---|---|
| `opengles2` | Krypton Wrapper (NG-GL4ES) |
| `opengles3_desktopgl_zink_kopper` | Kopper Zink (Mesa 23.0.4) |
| `vulkan_zink` | OSMesa + Zink |
| `opengles_mobileglues` | MobileGlues |
| `opengles3_ltw` | LTW / ANGLE (dependência proprietária opcional) |

## Compilando

### Pré-requisitos

* JDK 21 (para o Gradle) e JDK 17
* Android SDK com `compileSdk 37` e Build Tools
* Android NDK `27.3.13750724`

### Passos

```bash
# 1. Clonar com submódulos (MobileGlues, SDL, sdl2-compat, MioLibPatcher)
git clone --recursive https://github.com/DrakkonxJH/Minecraft-pc-port.git
cd Minecraft-pc-port

# 2. Baixar os runtimes Java (JRE 8/17/21)
bash scripts/fetch_jre.sh

# 3. Gerar a lista de idiomas (obrigatório antes do build)
bash scripts/languagelist_updater.sh      # Windows: scripts\languagelist_updater.bat

# 4. Compilar
./gradlew :app_pojavlauncher:assembleDebug
```

> **Não quer instalar nada?** Ative o GitHub Actions e baixe o APK pronto.
> Passo a passo em **[`docs/BUILD-E-TESTE.md`](docs/BUILD-E-TESTE.md)**.

O APK sai em `app_pojavlauncher/build/outputs/apk/debug/`.

> **Runtime Java:** o `scripts/fetch_jre.sh` baixa os JREs das *releases* do
> `angelauramc-openjdk-build`, que são permanentes (o workflow original usava
> artefatos de Actions, que expiram em 90 dias — ver bloqueio B1 da auditoria).
> Sem eles o APK compila, mas o app não inicia o jogo.

### Assinatura de release

A keystore **nunca** deve ser versionada. Configure via `app_pojavlauncher/keystore.properties`:

```properties
storeFile=/caminho/absoluto/minedrakk-release.jks
storePassword=...
keyAlias=...
keyPassword=...
```

Ou por variáveis de ambiente: `MINEDRAKK_KEYSTORE_FILE`, `MINEDRAKK_KEYSTORE_PASSWORD`,
`MINEDRAKK_KEYSTORE_ALIAS`, `MINEDRAKK_KEYSTORE_KEY_PASSWORD`.

Sem nenhuma das duas, o build de release cai para a chave de debug e **não é publicável**.

## Documentação técnica

* [`AUDITORIA.md`](AUDITORIA.md) — auditoria completa: arquitetura, bloqueios de build, segurança, bugs, dívida técnica e plano de ação
* [`COMPARATIVO-AMETHYST.md`](COMPARATIVO-AMETHYST.md) — comparação item a item entre PojavLauncher e Amethyst, com verificação de alinhamento ELF das bibliotecas nativas

## Licença

Licenciado sob [GNU LGPLv3](LICENSE), a mesma licença dos projetos originais.

## Créditos

Este projeto existe graças ao trabalho de quem veio antes:

* [Boardwalk](https://github.com/zhuowei/Boardwalk) — o launcher JVM original
* [PojavLauncher](https://github.com/PojavLauncherTeam/PojavLauncher) — a base deste launcher
* [Amethyst / AngelAuraMC](https://github.com/AngelAuraMC/Amethyst-Android) — sucessor do Pojav, origem da toolchain moderna, do SDL2 e dos renderizadores atuais

### Dependências

* [GL4ES](https://github.com/PojavLauncherTeam/gl4es) — MIT
* [OpenJDK](https://openjdk.java.net/legal/gplv2+ce.html) — GNU GPLv2 with Classpath Exception
* [LWJGL3](https://github.com/LWJGL/lwjgl3) — BSD-3
* [Mesa 3D](https://docs.mesa3d.org/license.html) — MIT
* [SDL](https://github.com/libsdl-org/SDL) — Zlib
* [MobileGlues](https://github.com/MobileGL-Dev/MobileGlues)
* [bhook](https://github.com/bytedance/bhook) — MIT
* [libepoxy](https://github.com/anholt/libepoxy) — MIT
* [MCHeads](https://mc-heads.net) — avatares de Minecraft

*Minecraft é uma marca registrada da Mojang Studios. Este projeto não é afiliado nem endossado pela Mojang ou pela Microsoft. Você precisa de uma cópia legítima do Minecraft: Java Edition para jogar.*
