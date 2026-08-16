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
* **JDK 21** ([Temurin](https://adoptium.net/)) — ou JDK 17
* Android SDK com **API 37**, **Build-Tools 36.0.0** e **NDK 27.3.13750724**

### Instalando o Android SDK

**Não precisa do Android Studio.** Use o script pronto:

```bash
bash scripts/setup_android_sdk.sh
```

Ele baixa as command-line tools oficiais do Google, aceita as licenças, instala
exatamente os componentes que o build exige e escreve o `local.properties`.
São ~2 GB de download.

Se você **já tem o Android Studio**, aponte para o SDK existente:

```bash
bash scripts/setup_android_sdk.sh --link-only
```

Nesse caso, confirme no **SDK Manager** que estão instalados:
API 37, Build-Tools 36.0.0 e NDK 27.3.13750724
(aba *SDK Tools* → marcar *Show Package Details* para ver as versões exatas).

> **Erro `SDK location not found`?** É exatamente isso que o script resolve.
> O `local.properties` guarda o caminho do SDK e é ignorado pelo Git de
> propósito: ele muda de máquina para máquina.

> **Sobre a API 37:** o pacote mudou de nome (`android-37` → `android-37.0`)
> quando a API 37 saiu de preview, e pode não estar no canal estável.
> O script detecta o nome correto automaticamente e, se a 37 não existir,
> instala a **android-36** e ajusta o `compileSdk` do projeto para 36.
> Isso **não afeta** o `targetSdk 36`, que é o exigido pela Google Play —
> nenhuma das AARs do projeto precisa de `compileSdk` acima de 36
> (verificado: todas declaram `minCompileSdk=1`).

### Submódulos

O projeto declara 4 submódulos no `.gitmodules`, mas **apenas um está de fato
registrado** na árvore do Git (verificado com `git ls-files -s`):

| Submódulo | Registrado? | Necessário? |
|---|---|---|
| `MioLibPatcher` | ✅ sim | **Sim** — entra em `settings.gradle` como projeto Gradle |
| `MobileGlues` | ❌ não | Não — o renderer vem pronto em `libs/MobileGlues-release.aar` |
| `jni/SDL` | ❌ não | Não — os headers SDL3 estão versionados em `jni/include/SDL3/` |
| `jni/sdl2-compat` | ❌ não | Não — não é referenciado pelo build |

Ou seja: basta o `MioLibPatcher`. Os outros três são entradas herdadas do
Amethyst que nunca chegaram a ter conteúdo registrado neste fork — o comando
abaixo simplesmente os ignora, sem erro:

```bash
git submodule update --init --recursive
```

Sintoma de submódulo faltando:
`Project with path ':MioLibPatcher' could not be found`.

### Passos

```bash
# 1. Clonar com submódulos
git clone --recursive https://github.com/DrakkonxJH/Minecraft-pc-port.git
cd Minecraft-pc-port
git checkout arena/01a00b26-minecraft-pc-port
git submodule update --init --recursive   # se esqueceu o --recursive

# 2. Android SDK + NDK (ou --link-only se já tem o Studio)
bash scripts/setup_android_sdk.sh

# 3. Runtimes Java (resolve o bloqueio B1)
bash scripts/fetch_jre.sh 8 17 21

# 4. Lista de idiomas (obrigatório, senão faltam traduções)
bash scripts/languagelist_updater.sh

# 5. Compilar
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

**Build falha com "SDK location not found"** — rode `bash scripts/setup_android_sdk.sh`
(ou `--link-only` se já tem o SDK). Ele gera o `local.properties` com o caminho correto.

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

---

## ⚠️ CI não roda? Conta travada por billing

**Diagnóstico concluído em 16/08/2026.** Mensagem exata devolvida pelo GitHub:

> `The job was not started because your account is locked due to a billing issue.`

### O que já foi descartado

| Verificação | Resultado |
|---|---|
| YAML do workflow | ✅ válido — sem tabs, sem BOM, sem CRLF |
| Arquivo no GitHub | ✅ presente e íntegro |
| Runner `ubuntu-22.04` | ✅ ativo |
| Workflow registrado | ✅ sim (após tornar público) |
| Job criado e iniciado | ❌ **bloqueado pelo billing** |

O problema **não é o código nem o workflow**. Tornar o repositório público
**não resolve**: a trava é na **conta**, e afeta Actions em qualquer
repositório — público ou privado.

### Solução: destravar a conta

1. Acesse **https://github.com/settings/billing**
2. Procure o aviso de conta bloqueada / pagamento pendente
3. Atualize ou adicione um **método de pagamento válido**
   * Mesmo no plano Free isso pode ser exigido se houve cobrança falha,
     assinatura pendente (Copilot, Pro) ou uso de Actions acima da cota em
     repositório privado
4. Se não houver aviso visível, abra um chamado em
   **https://support.github.com** citando a mensagem exata acima

Depois de destravar, force um novo build:

```bash
git commit --allow-empty -m "Testa CI"
git push
```

### Enquanto isso: compile localmente

**Esta é a via que não depende de ninguém** — veja a *Opção B* no topo deste
documento. Com o `scripts/fetch_jre.sh` já pronto, são 4 comandos:

```bash
bash scripts/fetch_jre.sh 8 17 21
bash scripts/languagelist_updater.sh
./gradlew :app_pojavlauncher:assembleDebug
```

### Alternativa: espelhar o repositório

Se a conta demorar a destravar, você pode criar um repositório em **outra conta
GitHub** (ou GitLab CI, que tem plano gratuito próprio) e usá-lo só para gerar
os APKs:

```bash
git remote add espelho https://github.com/OUTRA_CONTA/MineDrakk.git
git push espelho arena/01a00b26-minecraft-pc-port
```
