# Comparativo: PojavLauncher × Amethyst-Android

**Data:** 16 de agosto de 2026

| | PojavLauncher (nossa base) | Amethyst-Android |
|---|---|---|
| Repositório | `PojavLauncherTeam/PojavLauncher` | `AngelAuraMC/Amethyst-Android` |
| Último commit | `b12ad04` — 23/09/2025 — *"Discontinued"* | `360d708` — **16/08/2026** (hoje) |
| Commits desde 2025 | 0 (só o de encerramento) | **499** |
| Status | 💀 Morto | ✅ Ativo, ~30 commits/mês |
| `applicationId` | `net.kdt.pojavlaunch` | `org.angelauramc.amethyst` |
| Licença | LGPLv3 | LGPLv3 (mesma) |

**Conclusão antecipada:** o Amethyst é objetivamente superior como base técnica. Mas ele **não corrigiu nenhum** dos bugs de qualidade de código que identifiquei na auditoria — ele avançou em *features* e *toolchain*, não em higiene de código. Isso define exatamente a nossa oportunidade.

---

## 1. Verificação: o Amethyst corrigiu os bugs da auditoria?

Testei um a um, no código atual deles:

| Item da auditoria | Amethyst corrigiu? | Evidência |
|---|---|---|
| §5.1 NPE em `checkRules` (`rule.os.name`) | ❌ **Não** | `Tools.java:1159` — linha idêntica |
| §5.2 `AIOOBE`/`NumberFormatException` em `preProcessLibraries` | ❌ **Não** | `Tools.java:1169-1173` — idêntico |
| §5.3 Comparação de versão errada (`major>=5 && minor>=13`) | ❌ **Não** | idêntico |
| §5.4 `getFileName` off-by-one (`substring(i)` em vez de `i+1`) | ❌ **Não** | `FileUtils.java:24` — idêntico |
| §4.1 5 tokens vazando em `Log.i` | ❌ **Não** | `MicrosoftBackgroundLogin.java:126,155,186,222,258` |
| §4.3 Zip Slip em `ZipUtils.zipExtract` | ❌ **Não** | `ZipUtils.java:39-53` — idêntico |
| §4.4 `client_id` legado da Mojang | ❌ **Não** | mesmo `00000000402b5328` |
| §3.3 Keystore de release versionada | ❌ **Não** | trocaram `upload.jks` por `aamc_upload.jks` — **agora são duas** |
| Testes automatizados | ❌ **Não** | zero, igual |
| §6 `onBackPressed` / `onActivityResult` deprecados | ⚠️ **Parcial** | migraram `JavaGUILauncherActivity` para `OnBackPressedDispatcher` e vários para `registerForActivityResult`; `LauncherActivity.onBackPressed` continua |

**Leitura:** os 15 itens das Fases 2 e 3 do nosso plano continuam 100% válidos e são contribuição original nossa. O Amethyst não é um substituto para a auditoria — é um substituto para a *infraestrutura*.

---

## 2. O que o Amethyst resolveu (e vale pegar)

### 2.1 🟢 CRÍTICO — NDK 27 e o problema de 16 KB page size

Este é **o** item que sozinho justifica a comparação.

```
Pojav:    ndkVersion = "25.2.9519653"   APP_STL := system
Amethyst: ndkVersion = "27.3.13750724"  APP_STL := c++_shared
                                        APP_ABI := armeabi-v7a arm64-v8a x86 x86_64
```

Analisei o alinhamento de segmento `PT_LOAD` de todas as `.so` dos dois repos:

**PojavLauncher (nossa base) — arm64-v8a:**
```
align 4096  (4 KB)  → 10 libs  ← QUEBRADAS em dispositivos de 16 KB
align 16384 (16 KB) →  1 lib
align 65536 (64 KB) →  2 libs
```
Também 12/12 libs em 4 KB no armeabi-v7a e 11/11 no x86_64.

**Amethyst — arm64-v8a:**
```
align 4096  →  1 lib (libVkLayer_khronos_timeline_semaphore.so)
align 16384 →  1 lib (libvulkan_freedreno.so)
align 65536 →  1 lib (libunpack200.so)
```

O Amethyst **removeu quase todas as `.so` do repositório**: de 46 arquivos / 128 MB para **7 arquivos / 16 MB**. As bibliotecas agora vêm empacotadas como **AARs versionados** em `app_pojavlauncher/libs/`, compilados por CIs próprias com NDK moderno:

```
lwjgl-3.3.3-natives-release.aar   16 MB
lwjgl-3.4.1-natives-release.aar   16 MB
spirv-cross-natives.aar           31 MB
kopper-zink-release.aar           16 MB
angle-release.aar                  9 MB
krypton_wrapper-release.aar        9 MB
imgui-java-release.aar             8 MB
MobileGlues-release.aar            7.8 MB
SDL-release.aar                    4 MB
openal-soft-release.aar            2.9 MB
zstd-jni-release.aar               1 MB
```

Isso resolve **de uma vez** o item mais caro da nossa Fase 4 (§3.2 da auditoria). Era o trabalho que eu estimei como "o que decide a viabilidade a longo prazo" — recompilar OSMesa, OpenAL, gl4es e freedreno. Eles já fizeram.

> ⚠️ Ressalva importante: `targetSdk` deles ainda é **34**, igual ao nosso. Eles arrumaram a toolchain nativa mas **não** fizeram a migração de targetSdk. O bloqueio B2 da auditoria (Play Store, API 36) permanece nos dois. O `compileSdk` deles já está em **37**, o que facilita — falta só subir o target e tratar edge-to-edge.

### 2.2 🟢 CRÍTICO — B1 resolvido: JREs com CI próprio

```yaml
# Amethyst
repo: AngelAuraMC/angelauramc-openjdk-build
branch: buildjre8
```
Eles forkaram o build do OpenJDK para a própria organização. Nossa auditoria apontou que os artefatos do `PojavLauncherTeam/android-openjdk-build-multiarch` provavelmente expiraram — o Amethyst tem CI viva gerando os deles.

Detalhe relevante: no workflow atual **só o JRE 8 está ativo**; JRE 17, 21 e 25 estão comentados. Há um passo comentado apontando para `FCL-Team/Android-OpenJDK-Build` branch `Build_JRE_25` — sinal de que estão migrando de fonte. Vale investigar o estado real antes de copiar.

Também trocaram `workflow_conclusion: success` → `completed`, o que torna o download mais tolerante.

### 2.3 🟢 Toolchain de build modernizada

| | Pojav | Amethyst |
|---|---|---|
| AGP | 8.7.2 | **9.3.1** |
| Gradle | 8.13 | **9.6.1** |
| compileSdk | 34 | **37** |
| Build cache / paralelismo | — | `org.gradle.caching=true`, `org.gradle.parallel=true`, `org.gradle.tooling.parallel=true` |
| `lintOptions` (removido no AGP 9) | `lintOptions` | `lint { }` (sintaxe nova) |
| Windows | — | `APP_SHORT_COMMANDS=true` (corrige limite de linha de comando) |
| `packagingOptions` | `pickFirst` (deprecado) | `pickFirsts +=`, `keepDebugSymbols +=` |
| Nome do app por buildType | fixo | `resValue "string", "app_name", "Amethyst (Debug)"` — debug e release lado a lado |

Migrar para AGP 9 sozinho é trabalhoso (o `build.gradle` raiz do Pojav usa `Runtime.exec("git")` e `exec {}` na configuração, incompatível com Gradle 9). **Eles já pagaram esse custo.**

### 2.4 🟢 Renderers: 3 → 5

```diff
  opengles2                          # Pojav: gl4es_extra 1.1.4
+ opengles2                          # Amethyst: BZLZHH/NG-GL4ES (Krypton Wrapper) — substituído
+ opengles3_desktopgl_zink_kopper    # NOVO — Kopper Zink backport (Swung), Mesa 23.0.4
  vulkan_zink                        # osmesa 23.0.4 (Pojav usava virglrenderer)
+ opengles_mobileglues               # NOVO — MobileGlues (submódulo MobileGL-Dev)
  opengles3_ltw
```

Com ajustes finos de driver que são conhecimento de campo puro:
```java
// Turnip fix para problemas de renderização no OneUI
if (Tools.shouldUseUBWC()) envMap.put("FD_DEV_FEATURES", "enable_tp_ubwc_flag_hint=1");
// Detecção específica de Adreno 740
private static boolean isAdreno740()
// Zink: força GL 4.6 compat
envMap.put("MESA_GL_VERSION_OVERRIDE","4.6COMPAT");
envMap.put("MESA_GLSL_VERSION_OVERRIDE","460");
```
Mais uma tela de preferências dedicada (`pref_renderer.xml`, `LauncherPreferenceRendererSettingsFragment`) com config de ANGLE, FSR 1, compute shader ext, DSA ext, timer query — escrita em JSON para o MobileGlues.

### 2.5 🟢 SDL2 integrado — input e gamepad

25 arquivos Java novos, 12 deles em `org/libsdl/app/` (SDL oficial: `SDLActivity`, `SDLControllerManager`, `SDLSurface`, `HIDDeviceManager`, `HIDDeviceBLESteamController`...). Dois submódulos: `libsdl-org/SDL` e `libsdl-org/sdl2-compat`. Dois hooks nativos novos: `native_hooks/sdl_hook.c` e `native_hooks/dlopen_hook.c`.

Isso traz suporte real a gamepad/controle (inclusive Steam Controller via BLE) em vez do mapeamento manual do Pojav. Também integração com o **TouchController** (`top.fifthlight.touchcontroller:proxy-client-android`) com vibração configurável.

### 2.6 🟢 LWJGL duplo (3.3.3 + 3.4.1)

```groovy
include ":jre_lwjgl3glfw:lwjgl-3.3.3"
include ":jre_lwjgl3glfw:lwjgl-3.4.1"
```
Permite escolher a versão do LWJGL por perfil de jogo — versões antigas do Minecraft e mods legados funcionam com 3.3.3, modernos com 3.4.1. O `build.gradle` deles gera o arquivo `version` por **hash SHA-1 do JAR** em vez do commit git — mais correto (invalida cache só quando o conteúdo muda de fato) e funciona sem git.

### 2.7 🟢 Modloaders: NeoForge e LWJGL3ify

```
fragments/NeoForgeInstallFragment.java      modloaders/NeoForgeDownloadTask.java
fragments/LWJGL3ifyInstallFragment.java     modloaders/LWJGL3ifyUtils.java
fragments/ModpackCreateFragment.java        modloaders/LWJGL3ifyDownloadTask.java
```
**NeoForge** é o modloader dominante para 1.20.2+ — o Pojav não suporta, ponto cego sério em 2026. **LWJGL3ify** permite rodar 1.7.10/1.12.2 com Java moderno (crucial para GTNH e packs antigos). Mais criação de modpacks pelo próprio launcher.

### 2.8 🟢 Robustez de rede e login

**Retry com backoff exponencial** no login Microsoft (a API `minecraftservices` é notoriamente instável):
```java
for (int retryCount = 0; retryCount < 5; ++retryCount) {
    ...
    Thread.sleep(500L * (1L << retryCount)); // 0.5s, 1s, 2s, 4s, 8s
}
```
Isso ataca diretamente o `// TODO handle connection errors !` que apontei em §5.10.

**Modo offline funcional** — `Tools.isOnline()`, e o `MinecraftDownloader` agora valida instalação local (inclusive detectando JSON de 0 bytes corrompido e resolvendo `inheritsFrom` para instâncias modadas) em vez de simplesmente falhar sem rede.

**Tratamento de conta sem perfil**: detecta usuário que comprou mas não definiu username, e cai para `Demo.Player` quando não possui o jogo — em vez do `IllegalStateException` genérico.

### 2.9 🟢 Mitigações automáticas e utilitários

```java
startControllableMitigation(activity, gamedir)   // detecta mod problemático via log
startOldLegacy4JMitigation(activity, gamedir)
deleteSodiumMods()  // sodium, embeddium, rubidium, xenon
hasMods(String... filenames) / getMods(...)
hasTouchController(File gameDir)
mcVersiontoInt(String mcVersion)   // comparação de versão MC decente
isPointerDeviceConnected()
printLauncherInfo(...)             // diagnóstico estruturado
```
São *listeners* de log que detectam problemas conhecidos em runtime e oferecem correção ao usuário. Conhecimento acumulado de suporte que não se recria em código.

### 2.10 🟢 Outros

- `MioLibPatcher` (submódulo próprio) e `methods_injector_agent` — patching de bibliotecas em runtime
- Ícone monocromático (Material You / Android 13+): `ic_launcher_monochrome.webp`
- Ícones em `.webp` em todas as densidades (menor que PNG)
- `android:windowSoftInputMode="adjustResize"` na `MainActivity` — corrige teclado sobrepondo o jogo
- Permissão `VIBRATE`
- JNA como dependência Maven (`net.java.dev.jna:jna:5.14.0@aar`) em vez de `.so` solta
- `bytehook` 1.0.9 → 1.0.10
- `PREF_MOUSE_GRAB_FORCE`, `PREF_KEYBOARD_PANNING`, fallback quando o usuário deleta o controle padrão
- `MathQuestionPreference` — confirmação por conta em ações destrutivas

---

## 3. O que o PojavLauncher tem de melhor

Pouco, mas não é zero:

| Item | Detalhe |
|---|---|
| **`.so` completas no repo** | Ironicamente, é uma vantagem de *reprodutibilidade*: o Pojav tem OSMesa, OpenAL, gl4es e freedreno versionados e auditáveis. No Amethyst são AARs binários opacos vindos de CIs de terceiros. Se um desses repos sumir, o Amethyst quebra igual ao Pojav hoje. |
| **`virglrenderer`** | O `vulkan_zink` do Pojav usa virgl; o Amethyst migrou para osmesa 23.0.4. Em hardware específico o virgl pode ir melhor. |
| **Base menor e mais simples** | Sem SDL, sem 4 submódulos, sem LWJGL duplo. Para entender o sistema inteiro, o Pojav é mais legível. |
| **`FAIL_ON_PROJECT_REPOS`** | `settings.gradle` do Pojav é mais estrito (`PREFER_SETTINGS` no Amethyst) — melhor prática de supply chain. |
| **Sem `enableJetifier`** | O Amethyst ativou `android.enableJetifier=true`, que é legado (converte libs de Support Library) e deixa o build mais lento. |
| **Uma keystore versionada, não duas** | O Amethyst adicionou `aamc_upload.jks` e manteve `upload.jks`. |

---

## 4. Matriz de decisão consolidada

| Área | Pojav | Amethyst | Onde nos posicionamos |
|---|---|---|---|
| Manutenção upstream | 💀 morto | ✅ ativo | **Amethyst** |
| 16 KB page size / NDK 27 | ❌ | ✅ | **Amethyst** — item mais caro, já pago |
| JREs disponíveis (B1) | ❌ expirados | ✅ CI própria | **Amethyst** |
| AGP 9 / Gradle 9.6 / compileSdk 37 | ❌ | ✅ | **Amethyst** |
| targetSdk 36 (Play Store, B2) | ❌ 34 | ❌ 34 | **Nenhum** — trabalho nosso |
| Renderers | 3 | 5 + tuning | **Amethyst** |
| SDL2 / gamepad | ❌ | ✅ | **Amethyst** |
| NeoForge / LWJGL3ify | ❌ | ✅ | **Amethyst** |
| Modo offline / retry de rede | ❌ | ✅ | **Amethyst** |
| Zip Slip (§4.3) | ❌ | ❌ | **Nenhum** — nosso |
| Tokens no log (§4.1) | ❌ | ❌ | **Nenhum** — nosso |
| Crashes de parsing (§5.1-5.4) | ❌ | ❌ | **Nenhum** — nosso |
| `getenv` NULL no C (§5.5) | ❌ | ❌ | **Nenhum** — nosso |
| Vazamento JNI (§5.7) | ❌ | ❌ | **Nenhum** — nosso |
| Keystore no repo (B3) | ❌ 1 | ❌ 2 | **Nenhum** — nosso |
| Testes automatizados | ❌ 0 | ❌ 0 | **Nenhum** — nosso |
| Criptografia de credenciais (§4.2) | ❌ | ❌ | **Nenhum** — nosso |
| client_id Microsoft (§4.4) | ❌ | ❌ | **Nenhum** — nosso |

**Placar:** Amethyst vence em **9 áreas de infraestrutura**. Empate em **10 áreas de qualidade/segurança** — todas ainda abertas, todas mapeadas na nossa auditoria.

---

## 5. Recomendação

### Rebase sobre o Amethyst, aplicar a auditoria por cima

O caminho de menor esforço e maior resultado:

```
Amethyst (infraestrutura moderna: NDK 27, AGP 9, SDL2, 5 renderers, NeoForge, JREs)
   +
Nossa auditoria (15 correções de segurança/estabilidade que ninguém fez)
   +
targetSdk 36 (que nenhum dos dois fez — e é obrigatório para a Play Store)
   =
Diferencial real do nosso fork
```

Tentar portar manualmente as conquistas do Amethyst para a base do Pojav significaria refazer: migração AGP 8→9, recompilação de toda a toolchain nativa para 16 KB, integração do SDL2 (25 arquivos + 2 submódulos + 2 hooks nativos), LWJGL duplo, 2 modloaders. São **499 commits** de trabalho. Não faz sentido econômico.

**O inverso é barato:** as correções da auditoria são pontuais e cirúrgicas — a maioria é de 1 a 15 linhas, em arquivos que os dois repos têm idênticos. Elas se aplicam sobre o Amethyst quase sem conflito.

### Plano revisado

**Fase A — Rebase**
1. Adicionar o Amethyst como remote e trazer a árvore para a nossa branch, preservando o histórico da auditoria.
2. Inicializar os 4 submódulos (`MobileGlues`, `SDL`, `sdl2-compat`, `MioLibPatcher`).
3. Verificar o estado real dos JREs (só o 8 está ativo no CI deles).
4. Trocar identidade: `applicationId`, nome, ícones, keystore própria; remover `aamc_upload.jks` e `upload.jks`.

**Fase B — Aplicar a auditoria** (nosso diferencial, ~15 correções)
5. §4.1 tokens no log · §4.3 Zip Slip · §4.2 criptografia de conta · §4.4 client_id
6. §5.1-5.4 crashes de parsing · §5.5 `getenv` NULL · §5.6 `malloc` · §5.7 vazamento JNI
7. §5.8 catches vazios · §6 `onBackPressed` restante

**Fase C — targetSdk 36** (o que nenhum dos dois fez)
8. `targetSdk 34 → 36`, edge-to-edge, `WindowInsetsControllerCompat`
9. Validar 16 KB nas AARs do Amethyst em dispositivo/emulador real
10. Justificativa de `FOREGROUND_SERVICE_SPECIAL_USE` para a Play Store

**Fase D — Qualidade**
11. Primeiros testes unitários na lógica pura (parsing de versão, resolução de libs, `FileUtils`)
12. Quebrar `Tools.java` (que no Amethyst cresceu ainda mais: 675 linhas de diff a mais que o Pojav)

### Ponto de atenção sobre licença

Ambos são **LGPLv3**. Fazer rebase sobre o Amethyst é permitido, mas exige manter a licença, os avisos de copyright e creditar tanto o PojavLauncher quanto o Amethyst. O README deles já dá o exemplo de como encadear os créditos (Boardwalk → PojavLauncher → Amethyst).

---

*Comparação estática de código-fonte e configuração de build. Alinhamento ELF verificado programaticamente lendo os cabeçalhos `PT_LOAD` das bibliotecas dos dois repositórios.*
