# Como gerar o APK e testar no celular

## Resposta curta

**Não é possível compilar o APK neste ambiente.** O sandbox onde trabalho não tem
JDK, Android SDK nem NDK, não tem permissão de root para instalá-los, e a rede
bloqueia downloads de binários (só a API do GitHub passa). Verifiquei tudo isso
diretamente — não é suposição.

Você tem **duas opções reais**, e a primeira é bem mais fácil:

| | Onde compila | Esforço | Bom para |
|---|---|---|---|
| **A. GitHub Actions** ⭐ | Servidor do GitHub | Ativar 1 arquivo | Gerar APK sem instalar nada |
| **B. Seu PC** | Sua máquina | ~1h de setup, ~10 GB | Iterar rápido, depurar |

Nos dois casos o APK sai pronto para instalar no celular.

---

## Opção A — GitHub Actions (recomendada para começar)

O GitHub compila para você, de graça. Você não instala nada.

### 1. Ativar o workflow

Não consigo criar isso automaticamente: o app que uso não tem a permissão
`workflows` do GitHub. São 3 comandos no seu PC (ou pela interface web):

```bash
git clone https://github.com/DrakkonxJH/Minecraft-pc-port.git
cd Minecraft-pc-port
git checkout arena/01a00b26-minecraft-pc-port

mkdir -p .github/workflows
cp docs/ci-android.yml.template .github/workflows/android.yml

git add .github/workflows/android.yml
git commit -m "Ativa CI de build do APK"
git push
```

> Pela web: **Add file > Create new file**, nome `.github/workflows/android.yml`,
> e cole o conteúdo de `docs/ci-android.yml.template`.

### 2. Baixar o APK

1. Abra a aba **Actions** do repositório
2. Clique no build mais recente (leva ~15–25 min na primeira vez)
3. Na seção **Artifacts**, baixe:
   * **`MineDrakk-debug-apk`** — completo, com os runtimes Java embutidos (~250 MB). **Comece por este.**
   * **`MineDrakk-debug-apk-noruntime`** — menor (~90 MB), pede para instalar o runtime na primeira execução
4. Descompacte o `.zip` — dentro está o `.apk`

### 3. Instalar no celular

Transfira o `.apk` (cabo, Google Drive, Telegram...) e abra no aparelho.
O Android vai pedir para autorizar **"instalar apps de fontes desconhecidas"**.

O app instala como **MineDrakk Java (Debug)** e convive com PojavLauncher ou
Amethyst no mesmo aparelho — os `applicationId` são diferentes.

---

## Opção B — Compilar no seu PC

Necessário para depurar de verdade (logcat, breakpoints, iteração rápida).

### Requisitos

* **~10 GB** de disco livre e 8 GB de RAM
* **JDK 21** ([Temurin](https://adoptium.net/))
* **Android Studio** ([download](https://developer.android.com/studio)) — traz SDK e NDK
* No Android Studio, em **SDK Manager**:
  * SDK Platform **API 37**
  * **NDK 27.3.13750724** (aba *SDK Tools* > marcar *Show Package Details*)
  * Build-Tools mais recente

### Passos

```bash
# 1. Clonar COM submódulos (MobileGlues, SDL, sdl2-compat, MioLibPatcher)
git clone --recursive https://github.com/DrakkonxJH/Minecraft-pc-port.git
cd Minecraft-pc-port
git checkout arena/01a00b26-minecraft-pc-port

# Se esqueceu o --recursive:
git submodule update --init --recursive

# 2. Baixar os runtimes Java (resolve o bloqueio B1)
bash scripts/fetch_jre.sh 8 17 21

# 3. Gerar a lista de idiomas (obrigatório, senão faltam traduções)
bash scripts/languagelist_updater.sh

# 4. Compilar
./gradlew :app_pojavlauncher:assembleDebug
```

APK em: `app_pojavlauncher/build/outputs/apk/debug/`

### Instalar direto no celular por USB

Ative **Opções do desenvolvedor > Depuração USB** no aparelho, conecte e:

```bash
./gradlew :app_pojavlauncher:installDebug
# ou
adb install -r app_pojavlauncher/build/outputs/apk/debug/app_pojavlauncher-debug.apk
```

No Windows use `gradlew.bat` no lugar de `./gradlew`.

---

## O que observar nos testes

Como as correções que aplicamos são de segurança e estabilidade, vale testar
justamente os caminhos que elas tocam:

| O que testar | Por quê | Correção relacionada |
|---|---|---|
| Login com conta Microsoft | Mexemos no fluxo de log | 4.1 |
| Instalar um modpack (CurseForge/Modrinth) | Mexemos na extração de ZIP | 4.3 |
| Modpack grande com muitos mods (GTNH, ATM) | Onde os crashes de parsing apareciam | 5.1–5.3 |
| Trocar de renderizador nas configurações | Renomeamos a variável de ambiente | 5.5 |
| Iniciar o jogo várias vezes seguidas | Onde havia vazamento de memória | 5.7 |
| Versões antigas (1.7.10, 1.12.2) e novas (1.21) | Cobertura geral | — |

### Capturar logs quando algo falhar

```bash
adb logcat -c                                   # limpa
# reproduza o problema no aparelho
adb logcat -d > erro.txt                        # salva tudo
adb logcat -d | grep -iE 'minedrakk|pojav|AndroidRuntime|FATAL' > erro-filtrado.txt
```

O app também grava logs internamente em
`Android/data/com.drakkonx.minedrakk.debug/files/` (acessível por gerenciador de arquivos).

---

## Problemas comuns

**"App não instalado"** — normalmente é conflito de assinatura com uma versão
anterior. Desinstale a antiga primeiro.

**Build falha com "SDK location not found"** — crie `local.properties` na raiz:
```properties
sdk.dir=/caminho/para/Android/Sdk
```

**Build falha no NDK** — confirme a versão exata `27.3.13750724`. Outras versões
podem quebrar o alinhamento de 16 KB.

**App abre mas não inicia o jogo** — faltam os runtimes Java.
Rode `bash scripts/fetch_jre.sh` e recompile, ou use o APK completo.

**Erro de submódulo durante o build** — rode `git submodule update --init --recursive`.

---

## Limitação conhecida: 16 KB page size

As bibliotecas nativas herdadas do Amethyst estão compiladas com NDK 27, que
alinha para 16 KB por padrão. **Não conseguimos validar isso em hardware real
aqui.** Se você tiver um Pixel 8 ou mais novo (ou outro aparelho com páginas de
16 KB), esse é um teste de alto valor — é o item que decide a viabilidade do
projeto a longo prazo. Ver `AUDITORIA.md` seção 3.2.
