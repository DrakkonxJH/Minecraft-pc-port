# Auditoria Técnica — Minecraft-pc-port (fork do PojavLauncher)

**Data:** 16 de agosto de 2026
**Base do fork:** `PojavLauncherTeam/PojavLauncher`, branch `v3_openjdk`, último commit `b12ad04` (23/09/2025, mensagem: *"Discontinued"*)
**Branch de trabalho:** `arena/01a00b26-minecraft-pc-port`
**Escopo:** cópia integral do código-fonte + análise estática de todo o sistema

---

## 1. Sumário executivo

O projeto foi **oficialmente descontinuado** pelo time original. O último commit apenas marca o abandono; o desenvolvimento real parou antes disso. O sucessor indicado pelo próprio README é o [Amethyst-Android](https://github.com/AngelAuraMC/Amethyst-Android) (AngelAuraMC), que é um fork ativo da mesma base.

A base de código é **funcional e madura**, mas carrega dívida técnica considerável e, mais importante, tem **três bloqueios duros** que impedem qualquer publicação ou build reprodutível hoje:

| # | Bloqueio | Gravidade |
|---|----------|-----------|
| B1 | O build **não funciona sem CI**: os três JREs (8/17/21) e a lib `ltw-release.aar` não estão no repositório e são baixados de workflows do GitHub do time original | 🔴 Crítico |
| B2 | `targetSdk 34` — abaixo do mínimo da Play Store desde 31/08/2026 (exige API 36 para novos apps) | 🔴 Crítico |
| B3 | Keystore de release (`upload.jks`) versionada no repositório | 🔴 Crítico |

Abaixo, o mapeamento completo.

---

## 2. Arquitetura do sistema

### 2.1 Módulos Gradle

```
PojavLauncher (root)
├── app_pojavlauncher   → app Android (AGP 8.7.2, namespace net.kdt.pojavlaunch)
├── jre_lwjgl3glfw      → JAR Java 8: stub LWJGL3/GLFW injetado na JVM do Minecraft
├── forge_installer     → JAR agent: instalação headless de Forge
└── arc_dns_injector    → JAR agent: correção de DNS em ChromeOS/ARC
```

Os três módulos JAR compilam **para dentro** de `app_pojavlauncher/src/main/assets/components/`, e não como dependências normais. O `afterEvaluate` no `app_pojavlauncher/build.gradle` amarra isso via `tasks.mergeDebugAssets.dependsOn(...)`.

### 2.2 Como o app realmente funciona

```
LauncherActivity (processo :launcher)
   ↓ escolhe conta + perfil + versão
MinecraftDownloader  → baixa version JSON, libs, assets (com mirror BMCLAPI opcional)
   ↓
MainActivity (processo :game, isolado)
   ↓
JREUtils.launchJavaVM()
   ├── monta ~40 variáveis de ambiente (LD_LIBRARY_PATH, POJAV_RENDERER, LIBGL_ES...)
   ├── dlopen libjvm.so (OpenJDK portado, extraído de assets)
   ├── injeta caciocavallo (AWT headless), pro-grade (SecurityManager), lwjgl-glfw-classes.jar
   └── chama JNI_CreateJavaVM via libpojavexec.so
        ↓
   Minecraft roda dentro da JVM; chamadas OpenGL vão para:
        gl4es (GL desktop → GLES) | OSMesa/Zink | LTW (ANGLE) | VirGL
        ↓ egl_bridge.c → EGL → superfície Android
```

Camada nativa (`src/main/jni/`, ~39 arquivos C/H, 4 libs .so):
- `libpojavexec.so` — bridge EGL/OSMesa, launcher da JVM, ponte de input, afinidade de big cores
- `libexithook.so` — hooks de `exit()` e `chmod()` via ByteHook
- `liblinkerhook.so` — bypass de namespace do linker para carregar driver Turnip (Adreno)
- `libawt_xawt.so` — stub X11 para o AWT

### 2.3 Números do código

| Métrica | Valor |
|---|---|
| Arquivos versionados | 640 |
| Arquivos `.java` | 291 (~1,8 MB no app; 555 KB só `GLCapabilities.java` gerado) |
| Arquivos C/H | 39 (~1,2 MB) |
| Bibliotecas nativas `.so` | 46 arquivos, **128 MB** (4 ABIs) |
| Traduções | 51 diretórios `values-*` |
| **Testes automatizados** | **0** (nenhum `test/` ou `androidTest/`) |
| TODO/FIXME/HACK | 34 ocorrências |

---

## 3. Bloqueios críticos de build

### 3.1 🔴 B1 — O repositório não compila sozinho

O `.gitignore` exclui deliberadamente:
```
app_pojavlauncher/src/main/assets/components/jre        ← JRE 8
/app_pojavlauncher/src/main/assets/components/jre-new/  ← JRE 17
/app_pojavlauncher/src/main/assets/components/jre-21/   ← JRE 21
/app_pojavlauncher/libs/ltw-release.aar                 ← renderer LTW (proprietário)
```

O workflow `.github/workflows/android.yml` busca esses artefatos com `dawidd6/action-download-artifact@v9` de:
- `PojavLauncherTeam/android-openjdk-build-multiarch`, branches `buildjre8` e `buildjre17-21`
- `PojavLauncherTeam/LTW` releases

**Problema:** esses repositórios pertencem a uma organização abandonada. Artefatos de GitHub Actions **expiram (90 dias por padrão)**. Como o último build é de 2025, é praticamente certo que **os artefatos já não existem mais** — o CI vai falhar no passo "Get JRE 8".

Sem os JREs, o APK compila mas o app não roda: `AsyncAssetManager` chama `am.open("components/jre/version")` e lança `IOException`.

**Ação necessária (prioridade máxima):**
1. Baixar/rebuildar os JREs multiarch e hospedá-los você mesmo (release do seu próprio repo, ou Git LFS).
2. Alternativa mais rápida: pegar os JREs do **Amethyst-Android**, que mantém a mesma estrutura de assets e tem CI ativo.
3. Substituir o passo `action-download-artifact` por um `curl` para a sua própria release.

### 3.2 🔴 B2 — `targetSdk 34` bloqueia publicação

`app_pojavlauncher/build.gradle`:
```groovy
compileSdk = 34
minSdkVersion 21
targetSdkVersion 34
buildToolsVersion = '34.0.0'
ndkVersion = "25.2.9519653"
```

Desde **31/08/2026**, a Google Play exige API 36 (Android 16) para novos apps e updates; apps abaixo de API 35 deixam de ser visíveis para novos usuários em dispositivos recentes.[Google Play target API policy](https://median.co/blog/google-plays-target-api-level-requirement-for-android-apps)

Migrar de 34 → 36 **não é trocar um número**. O que quebra:

| Mudança do Android 15/16 | Impacto neste código |
|---|---|
| **Edge-to-edge obrigatório** (API 35+) | `Tools.setFullscreen()` usa `setSystemUiVisibility()` + `SYSTEM_UI_FLAG_*`, deprecados desde API 30 e ignorados em 35+. A superfície do jogo pode ficar sob as barras do sistema. |
| **16 KB page size obrigatório** (API 36) | ⚠️ **O mais grave.** Todas as 46 libs `.so` foram compiladas com NDK 25 e alinhamento de 4 KB. Em dispositivos com páginas de 16 KB (Pixel 8+ e sucessores) elas **não carregam**. Exige recompilar tudo com NDK r27+ e `-Wl,-z,max-page-size=16384` — incluindo OSMesa, OpenAL, gl4es e freedreno, que vêm de outros repositórios. |
| `FOREGROUND_SERVICE_*` mais restritivo | `GameService` usa `specialUse`; a Play exige justificativa aprovada caso a caso. |
| `WRITE_EXTERNAL_STORAGE` limitada a `maxSdkVersion=28` | Já tratado, ok. |

### 3.3 🔴 B3 — Keystore de release versionada

```
app_pojavlauncher/upload.jks     (2591 bytes) — keystore de upload da Google Play
app_pojavlauncher/debug.keystore (1267 bytes) — debug, aceitável
```

A `upload.jks` está no Git. A senha vem de `System.getenv("GPLAY_KEYSTORE_PASSWORD")`, então não está exposta — mas o arquivo de chave **nunca deve estar versionado**. Como o fork terá `applicationId` próprio, essa keystore é inútil para você e só representa risco.

**Ação:** remover `upload.jks` do repositório (e idealmente do histórico com `git filter-repo`), gerar keystore própria, guardar fora do Git.

---

## 4. Problemas de segurança

### 4.1 🟠 Tokens de autenticação em texto plano no log

`authenticator/microsoft/MicrosoftBackgroundLogin.java`:
```java
:117  Log.i("MicrosoftLogin", "isRefresh=" + isRefresh + ", authCode= " + authcode);
:146  Log.i("MicrosoftLogin", "Acess Token = " + jo.getString("access_token"));
:177  Log.i("MicrosoftLogin", "Xbl Token = " + jo.getString("Token"));
:213  Log.i("MicrosoftLogin", "Xbl Xsts = " + token + "; Uhs = " + uhs);
:249  Log.i("MicrosoftLogin", "MC token: " + jo.getString("access_token"));
```
Cinco tokens de conta Microsoft/Minecraft gravados em `Log.i` **em builds de release** (não há guarda `BuildConfig.DEBUG`). Qualquer app com permissão de leitura de log, ou um bug report enviado pelo usuário, vaza a conta inteira.

**Correção:** remover ou envolver em `if (BuildConfig.DEBUG)`.

### 4.2 🟠 Credenciais de conta em JSON sem criptografia

`value/MinecraftAccount.java`:
```java
public String save(String outPath) throws IOException {
    Tools.write(outPath, Tools.GLOBAL_GSON.toJson(this));  // accessToken, msaRefreshToken em claro
}
```
Grava em `DIR_ACCOUNT_NEW = ctx.getFilesDir().getParent() + "/accounts"`. É armazenamento interno (protegido em dispositivos não-rooteados), mas o `msaRefreshToken` é de longa duração. Recomendado migrar para `EncryptedSharedPreferences` / Android Keystore.

### 4.3 🟠 Zip Slip (path traversal) em `ZipUtils.zipExtract`

`utils/ZipUtils.java:46`:
```java
File zipDestination = new File(destination, entryName.substring(dirNameLen));
FileUtils.ensureParentDirectory(zipDestination);
```
Nenhuma validação de que `zipDestination` fica dentro de `destination`. Um modpack malicioso com entrada `../../../../data/data/net.kdt.pojavlaunch/files/x` escreve fora do destino. Como o app instala modpacks de CurseForge/Modrinth (conteúdo de terceiros), o vetor é real.

**Correção padrão:**
```java
String canonicalDest = destination.getCanonicalPath();
if (!zipDestination.getCanonicalPath().startsWith(canonicalDest + File.separator))
    throw new IOException("Zip entry outside target dir: " + entryName);
```

`NativesExtractor.extractFromAar` está protegido por acidente (usa `FileUtils.getFileName()`, que descarta o caminho) — mas confia num efeito colateral, não numa validação.

### 4.4 🟡 Client ID legado da Microsoft

`client_id "00000000402b5328"` hardcoded em dois lugares (`MicrosoftBackgroundLogin.java:120`, `MicrosoftLoginFragment.java:58`). É o client ID público do launcher oficial da Mojang — funciona, mas é tecnicamente uso não autorizado e pode ser revogado a qualquer momento pela Microsoft, quebrando o login de todos os usuários de uma vez.

### 4.5 🟡 Verificação de SHA-1 opcional

`MinecraftDownloader.java:358` e `:382`:
```java
if(!LauncherPreferences.PREF_CHECK_LIBRARY_SHA) sha1 = null;
```
Se o usuário desativa a checagem (ou usa o mirror BMCLAPI, que não é da Mojang), JARs baixados são executados **sem qualquer verificação de integridade**. Combinado com o `SecurityManager` sendo removido no Java 17+, é execução de código arbitrário na prática.

### 4.6 🟡 Hooks nativos de `chmod` sempre retornam sucesso

`jni/native_hooks/chmod_hook.c` faz `chmod`/`fchmod` retornarem 0 sempre. É um workaround para `/sdcard` (FAT/FUSE não suporta permissões POSIX), mas mascara falhas reais de permissão em qualquer código que rode na JVM.

### 4.7 🟡 SecurityManager obsoleto

`components/security/pro-grade.jar` + `java_sandbox.policy` implementam sandbox via `SecurityManager`, que foi **deprecado no Java 17 (JEP 411) e removido no Java 24**. Nos runtimes JRE 17/21 esse sandbox já não protege efetivamente. Os patches `log4j-rce-patch-*.xml` continuam válidos e importantes.

---

## 5. Bugs e riscos de crash no código Java

### 5.1 🟠 `NullPointerException` provável em `Tools.checkRules`

`Tools.java:818`:
```java
if (rule.action.equals("allow") && rule.os != null && rule.os.name.equals("osx"))
```
`rule.os.name` pode ser `null` em version JSONs que especificam só `os.arch` ou `os.version` (comum em Forge antigo e em algumas versões modernas). Estoura NPE ao parsear a versão.

### 5.2 🟠 `ArrayIndexOutOfBounds` / `NumberFormatException` em `preProcessLibraries`

`Tools.java:827`:
```java
String[] version = libItem.name.split(":")[2].split("\\.");
...
if (Integer.parseInt(version[0]) >= 5 && Integer.parseInt(version[1]) >= 13) continue;
```
Três problemas:
- `split(":")[2]` → `AIOOBE` se o nome da lib não tiver 3 componentes (`grupo:artefato` sem versão aparece em mods).
- `version[1]` → `AIOOBE` se a versão for só `"5"`.
- `Integer.parseInt` → `NumberFormatException` em versões como `5.13.0-SNAPSHOT`, `2.0.0-beta`, `1.0.0+build1`.

Isso roda no parse de **toda** version JSON. Um único modpack com lib de versionamento incomum derruba o launcher.

### 5.3 🟠 Lógica de comparação de versão errada

Mesmo trecho: `major >= 5 && minor >= 13` não é comparação de versão. Uma lib `6.2.x` (major 6 ≥ 5, mas minor 2 < 13) **não** passa no `continue` e é forçada para JNA 5.13.0 — um **downgrade**. Deveria ser comparação lexicográfica de versão semântica.

### 5.4 🟠 `FileUtils.getFileName` retorna caminho com barra

`utils/FileUtils.java:21`:
```java
int lastSlashIndex = pathOrUrl.lastIndexOf('/');
if(lastSlashIndex == -1) return null;
return pathOrUrl.substring(lastSlashIndex);   // ← inclui a '/'
```
Deveria ser `substring(lastSlashIndex + 1)`. E retornar `null` quando não há barra (em vez do nome já limpo) força os 5 chamadores a tratar `null`. Em `NativesExtractor:71` o resultado vira `new File(mDestinationDir, "/libfoo.so")` — funciona por acidente no Java, mas é frágil e a checagem `LIBRARY_BLACKLIST.contains(entryName)` **nunca casa**, porque a blacklist certamente não tem os nomes com barra.

### 5.5 🟡 `NullPointerException` em código nativo por `getenv`

`jni/ctxbridges/gl_bridge.c:80` e `:90`:
```c
if (strncmp(getenv("POJAV_RENDERER"), "opengles3_desktopgl", 19) == 0)
int libgl_es = strtol(getenv("LIBGL_ES"), NULL, 0);
```
`getenv` pode retornar `NULL` → `strncmp`/`strtol` com ponteiro nulo = **SIGSEGV**. Só não acontece hoje porque `JREUtils` sempre define ambas — mas `LIBGL_ES` só é definida quando `LOCAL_RENDERER != null` (`JREUtils.java:227`). É um crash esperando um caminho de código onde o renderer não foi selecionado.

Mesmo padrão em `egl_bridge.c:237` (`getenv("VULKAN_PTR")`) e `egl_loader.c:35`.

### 5.6 🟡 `malloc` sem verificação

`jni/ctxbridges/gl_bridge.c:58` e `jni/utils.c:18` — `malloc` sem checar `NULL` antes de `memset`. `osm_bridge.c:28` faz certo. Baixa probabilidade, mas é crash silencioso em OOM.

### 5.7 🟡 Vazamento de memória JNI em `convert_to_char_array`

`jni/utils.c:15-27`: aloca com `malloc` e chama `GetStringUTFChars` para cada elemento. Existe `free_char_array`, mas ela libera as strings e **não dá `free` no array em si**. Vazamento por chamada.

### 5.8 🟡 Catches vazios engolindo erros

```
com/kdt/pickafile/FileListView.java:101   catch (NullPointerException e) {}
ImportControlActivity.java:180            catch (Exception ignored) {}
LauncherActivity.java:138                 catch (ParseException ignored) {}
modloaders/FabriclikeUtils.java:43        catch (...ParseException ignored) {}
```
Mais 35 `printStackTrace()` espalhados — em Android isso vai para o stderr, não para o logcat estruturado, e some do relatório de crash.

### 5.9 🟡 Race condition assumida e não resolvida

`MainActivity.java:164`: `// FIXME: is it safe for multi thread?` em `GLOBAL_CLIPBOARD`. `CallbackBridge.java:60`: `// TODO CHECK: This may cause input issue, not receive input!` — em código de input, o caminho mais sensível a latência do app.

### 5.10 🟡 `MicrosoftBackgroundLogin` sem tratamento de rede

Linha 36: `// TODO handle connection errors !`. Todo o fluxo de login está num `try/catch (Exception)` único que só faz `Log.e` + callback de erro genérico. Timeout, 429 (rate limit) e 503 são indistinguíveis para o usuário. Linha 91: `acc.clientToken = "0"; /* FIXME */`.

---

## 6. APIs obsoletas e dívida técnica

| API deprecada | Onde | Substituto |
|---|---|---|
| `onBackPressed()` | `LauncherActivity:267`, `CustomControlsActivity:80`, `GamepadMapperFragment:49`, `MicrosoftLoginFragment:116` | `OnBackPressedDispatcher` |
| `setSystemUiVisibility()` / `SYSTEM_UI_FLAG_*` | `Tools:629-638`, `JavaGUILauncherActivity:270` | `WindowInsetsControllerCompat` |
| `onActivityResult()` | `MainActivity:334` | `ActivityResultContracts` (o pacote `contracts/` já existe — migração inacabada) |
| `SecurityManager` (pro-grade) | assets/security | Removido no Java 24; sem substituto direto |

**Dependências desatualizadas** (`app_pojavlauncher/build.gradle`): `commons-codec:1.15`, `androidx.preference:1.2.0`, `androidx.annotation:1.5.0`, `constraintlayout:2.1.4`, `viewpager2:1.1.0-beta01` (**beta em produção**), `htmlcleaner:2.6.1` (2013), `bytehook:1.0.9`. JARs locais sem gerenciamento de versão: `gson-2.8.6.jar` (2019), `ExagearApacheCommons.jar`, `exp4j-SNAPSHOT.jar` (**snapshot em produção**).

**Outros pontos:**
- `Tools.java` tem **67 KB e 1400+ linhas** — God class fazendo I/O, UI, parse de JSON, launch da JVM e utilitários de string.
- `build.gradle` raiz usa `Runtime.getRuntime().exec("git ...")` e `exec {}` no bloco de configuração — incompatível com o **Gradle configuration cache** e com o Gradle 9 (o wrapper já está no 8.13, mas o plugin declara AGP 8.7.2).
- `gradle.properties` tem `org.gradle.configureondemand=true` com comentário explicando que é para conciliar Java 8 no `jre_lwjgl3glfw` com Java 11+ no app — gambiarra frágil; o CI precisa trocar de JDK 21 → 17 no meio do build.
- Zero testes automatizados.
- `scripts/languagelist_updater.sh` **precisa rodar antes do build** (gera `assets/language_list.txt`), mas nada no Gradle força isso. Se esquecer, o app compila com lista de idiomas desatualizada.

---

## 7. Plano de ação priorizado

### Fase 0 — Destravar o build (obrigatório antes de tudo)
1. Resolver os JREs 8/17/21 — hospedar em release própria ou pegar do Amethyst-Android.
2. Decidir sobre a LTW (`ltw-release.aar`): incluir, ou remover a opção de renderer `opengles3_ltw` do código (`Tools:244`, `JREUtils:217/472`).
3. Reescrever `.github/workflows/android.yml` apontando para as suas fontes.
4. Instalar JDK 17 + 21 e Android SDK/NDK, rodar `./gradlew :app_pojavlauncher:assembleDebug` e catalogar os erros **reais** de compilação (esta auditoria é estática — pode haver mais).

### Fase 1 — Identidade do fork
5. Trocar `applicationId` de `net.kdt.pojavlaunch` para o seu (o namespace/pacote Java pode ficar, para reduzir o diff).
6. Remover `upload.jks` do repositório e do histórico; gerar keystore própria.
7. Atualizar README, ícones, `app_name`; remover referências à Crowdin do time original (`crowdin.yml`).
8. Verificar conformidade com a **LGPLv3** — fork deve manter a licença e os créditos.

### Fase 2 — Segurança (rápido, alto impacto)
9. Apagar os 5 `Log.i` de tokens em `MicrosoftBackgroundLogin`.
10. Corrigir Zip Slip em `ZipUtils.zipExtract`.
11. Resolver o client ID da Microsoft (registrar app próprio no Azure AD é o correto).
12. Criptografar armazenamento de conta.

### Fase 3 — Estabilidade
13. Blindar `preProcessLibraries` e `checkRules` (§5.1–5.3) — provavelmente a maior fonte de crash em modpacks.
14. Corrigir `FileUtils.getFileName` e auditar os 5 chamadores.
15. Guardas de `NULL` em todo `getenv` do C.
16. Corrigir o vazamento JNI em `utils.c`.
17. Substituir catches vazios e `printStackTrace` por log estruturado.

### Fase 4 — Modernização (esforço grande)
18. **16 KB page size** — recompilar todas as libs nativas com NDK r27+. Este é o item de maior esforço e o que decide a viabilidade a longo prazo.
19. `compileSdk`/`targetSdk` → 36; migrar edge-to-edge, `OnBackPressedDispatcher`, `ActivityResultContracts`.
20. Atualizar dependências; eliminar o `viewpager2` beta e o `exp4j` snapshot.
21. Modernizar os `build.gradle` (eliminar `exec` na configuração, habilitar configuration cache).
22. Quebrar `Tools.java`; introduzir testes unitários no que é lógica pura (parsing de versão, resolução de libs, utilitários de arquivo).

---

## 8. Recomendação estratégica

Antes de investir na Fase 4, vale comparar com o **Amethyst-Android**. É o sucessor oficial, parte exatamente da mesma base, e provavelmente já resolveu B1 (JREs) e possivelmente o 16 KB page size. Duas rotas:

- **Fork do PojavLauncher (atual):** controle total, base congelada e conhecida, mas você absorve sozinho o custo de recompilar toda a toolchain nativa.
- **Rebase sobre o Amethyst:** herda as correções já feitas e o CI funcionando, ao custo de depender de um upstream de terceiros.

Uma via intermediária razoável: manter este fork como base e **portar seletivamente** do Amethyst o que resolve B1 e o 16 KB — os dois itens onde o trabalho pesado é reproduzir builds nativos de OSMesa, OpenAL, gl4es e freedreno.

---

*Auditoria estática. Não inclui análise dinâmica, profiling, teste em dispositivo, nem revisão do código gerado (`GLCapabilities.java`, `AWTInputEvent.java`) e das dependências binárias (`.so`, `.jar`).*
