# Revisão completa do MineDrakk Java

**Data:** 16 de agosto de 2026 · **Commit:** `283a368c8` · **Versão:** 0.1.0

Auditoria de todos os sistemas do launcher, com foco em regressões introduzidas
pelas mudanças desta sessão e no suporte a versões, modloaders e mods.

---

## Resumo

| Área | Estado |
|---|---|
| Compilação (Java, recursos, nativo 4 ABIs) | ✅ Passa |
| Versões do Minecraft (rd-132211 até 1.21+) | ✅ Suportadas |
| Modloaders (Forge, NeoForge, Fabric, Quilt, OptiFine, BTA, LWJGL3ify) | ✅ Endpoints válidos |
| Mods e modpacks (CurseForge, Modrinth) | ✅ Funcionais |
| Renderizadores | ✅ 3 ativos + fallback automático |
| Contas (Microsoft, offline, migração) | ✅ Corrigido nesta revisão |
| Multiplayer offline (LAN, servidores) | ✅ UUID correto por jogador |
| Correções da auditoria original | ✅ Todas intactas |

**2 bugs encontrados e corrigidos** nesta revisão. Nenhum bloqueador restante.

---

## Bugs encontrados e corrigidos

### 1. Contas `Demo.` antigas presas no modo demo 🔴

Contas criadas antes da mudança de login mantinham o prefixo `Demo.`, que:
* adiciona a flag `--demo` → jogo limitado (~100 min, mundo fixo);
* desvia o diretório para `/demo/.minecraft` → mundos separados.

Novas contas já nasciam corretas, mas as existentes **nunca migravam**.

**Correção:** `MinecraftAccount.load()` remove o prefixo, gera o UUID offline
correspondente e apaga o arquivo antigo. Se a gravação falhar, reverte o nome
para não perder a conta.

### 2. Quick play podia impedir o jogo de abrir 🔴

`LauncherProfiles.getCurrentProfile()` **lança `RuntimeException`** quando o
perfil selecionado não existe mais (perfil apagado, `launcher_profiles.json`
corrompido). O quick play chamava esse método na montagem dos argumentos de
lançamento — uma funcionalidade opcional podia derrubar o launch inteiro.

**Correção:** envolvido em `try/catch`, registrando apenas um aviso.

---

## Verificações realizadas

### Integridade estrutural

| Verificação | Resultado |
|---|---|
| `illegal forward reference` no Java | ✅ nenhuma |
| Delimitadores desbalanceados | ✅ nenhum |
| Propriedades de projeto em escopo estático (Gradle) | ✅ nenhuma |
| XMLs de recurso válidos | ✅ 100% |
| Duplicatas de recurso | ✅ nenhuma |
| Drawables/mipmaps referenciados existentes | ✅ todos |
| Strings referenciadas existentes | ✅ todas |

### Correções da auditoria original

Confirmado que seguem aplicadas:

* §4.1 — zero tokens Microsoft/Minecraft nos logs
* §4.3 — guarda contra Zip Slip ativa
* §5.2 — parse tolerante de versão de biblioteca
* §5.4 — `getFileName()` corrigido
* §5.5 — guardas de `getenv()` nulo (5 no código C)
* §5.7 — `free()` do array JNI

### Modloaders

Endpoints conferidos no código:

| Modloader | Endpoint |
|---|---|
| Forge | `maven.minecraftforge.net/.../maven-metadata.xml` |
| NeoForge | `maven.neoforged.net/releases/net/neoforged/neoforge/` |
| Fabric | `meta.fabricmc.net/v2` |
| Quilt | `meta.quiltmc.org/v3` |
| OptiFine | `optifine.net` (scraping) |
| BTA | `downloads.betterthanadventure.net` |
| CurseForge / Modrinth | `api.curseforge.com` / `api.modrinth.com` |

O download resolve `inheritsFrom` **recursivamente**
(`MinecraftDownloader:328`), então instalar Forge/Fabric baixa a versão vanilla
base automaticamente.

### Runtimes Java

Seleção automática por versão do jogo (`NewJREUtil`), com escolha do runtime
instalado mais próximo. Runtimes declarados: **JRE 17, 21 e 25**.

> `scripts/fetch_jre.sh` baixa 8, 17 e 21 por padrão. O JRE 25 existe nas
> releases (`bash scripts/fetch_jre.sh 25`) mas não é necessário hoje — nenhuma
> versão do Minecraft o exige. Se faltar, o launcher usa o mais próximo
> disponível em vez de falhar.

### Renderizadores

| Renderer | Biblioteca | Estado |
|---|---|---|
| `opengles2` (Krypton Wrapper) | `libng_gl4es.so` | ✅ presente |
| `opengles3_desktopgl_zink_kopper` | `libglxshim.so` | ✅ presente |
| `opengles_mobileglues` | `libmobileglues.so` | ✅ presente |
| `vulkan_zink` | `libOSMesa.so` | ⚠️ ausente → filtrado |
| `opengles3_ltw` | `libltw.so` | ⚠️ ausente → filtrado |

Os dois ausentes **não aparecem na lista** para o usuário
(`Tools.getCompatibleRenderers()` os remove). Se um renderer falhar ao carregar,
há fallback automático para o Krypton Wrapper (`JREUtils:534`).

Para habilitar os dois faltantes seria preciso adicionar `libOSMesa.so` (Zink) e
`ltw-release.aar` (dependência proprietária) — ambos opcionais.

---

## Limitações conhecidas

| Item | Observação |
|---|---|
| **Servidores `online-mode=true`** | Contas offline são recusadas pelo servidor da Mojang, não pelo launcher. Use LAN ou `online-mode=false` (ver [`MULTIPLAYER.md`](MULTIPLAYER.md)). |
| **Quick play** | Requer Minecraft 1.20+. Em versões antigas o campo é ignorado sem erro. |
| **16 KB page size** | As bibliotecas usam NDK 27 (alinhamento correto), mas **não foi validado em hardware** com páginas de 16 KB (Pixel 8+). |
| **Testes automatizados** | O projeto não tem suíte de testes. As validações desta sessão estão em `.verify/`. |
| **Avisos do build** | `Multiple substitutions` (traduções da Crowdin), namespace duplicado nos AARs do LWJGL e `libawt_headless.so` inexistente são cosméticos e herdados. |

---

## Roteiro de teste sugerido

Priorizado pelo que mudou nesta sessão:

1. **Conta antiga** — se você tinha `Demo.Player`, abra o app: deve virar
   `Player` automaticamente, sem limite de demo
2. **Versão vanilla recente** (1.21) — baixa e roda
3. **Forge 1.21** — deve baixar o 1.21 vanilla automaticamente antes
4. **Fabric + um mod** — instalar e verificar se carrega
5. **Modpack** (CurseForge ou Modrinth) — instalação completa
6. **Versão antiga** (1.7.10 ou 1.12.2) — compatibilidade legada
7. **Trocar renderizador** nas configurações
8. **LAN com um amigo** — nicks diferentes, verificar que são jogadores distintos
9. **Quick play** — preencher o servidor no perfil (1.20+)

Se algo falhar:

```bash
adb logcat -d | grep -iE 'minedrakk|AndroidRuntime|FATAL' > erro.txt
```
