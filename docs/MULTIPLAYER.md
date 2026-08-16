# Jogar com amigos no MineDrakk

Guia prático para jogar multiplayer com contas offline (sem licença do
Minecraft: Java Edition).

## O que funciona, e o que não funciona

| Modo | Conta offline funciona? | Por quê |
|---|---|---|
| Singleplayer | ✅ Sim | Não há validação |
| **LAN** (mesma rede Wi-Fi) | ✅ Sim | Validação desligada por padrão |
| **Servidor com `online-mode=false`** | ✅ Sim | O servidor não consulta a Mojang |
| **Rede virtual** (ZeroTier, Radmin) | ✅ Sim | Simula uma LAN pela internet |
| Servidor com `online-mode=true` | ❌ Não | O servidor valida a sessão na Mojang |
| Servidores públicos grandes (Hypixel, Mineplex) | ❌ Não | Usam `online-mode=true` |

> A recusa em servidores online **não vem do launcher** — quem valida é o
> servidor da Mojang. Nenhuma alteração no MineDrakk muda isso.

---

## Opção 1 — LAN (mais simples)

Para quem está na **mesma rede Wi-Fi**.

1. Um jogador abre um mundo singleplayer
2. Pressiona `Esc` → **Abrir para LAN** → **Iniciar mundo em LAN**
3. Os outros vão em **Multijogador** — o mundo aparece sozinho

Se não aparecer, use **Conexão direta** com o IP de quem hospedou
(ex.: `192.168.0.15:25565`).

**Requisito:** todos no mesmo Wi-Fi. Redes de escola/empresa costumam
bloquear esse tipo de tráfego.

---

## Opção 2 — Rede virtual (amigos em cidades diferentes)

Faz vários aparelhos se enxergarem como se estivessem na mesma LAN.

| Serviço | Observação |
|---|---|
| [ZeroTier](https://www.zerotier.com/) | Grátis até 25 dispositivos, tem app Android |
| [Radmin VPN](https://www.radmin-vpn.com/) | Grátis, só Windows |
| Hamachi | Grátis até 5 pessoas |

**Com ZeroTier:**

1. Crie uma rede em [my.zerotier.com](https://my.zerotier.com) e anote o Network ID
2. Todos instalam o app ZeroTier e entram com esse ID
3. Você autoriza cada dispositivo no painel
4. Um jogador abre o mundo para LAN
5. Os outros usam **Conexão direta** com o IP ZeroTier do host
   (aparece no app, algo como `10.147.x.x`)

---

## Opção 3 — Servidor dedicado

Melhor para jogar sempre no mesmo mundo, com o servidor no ar mesmo quando
ninguém está jogando.

### Servidor próprio (PC ou VPS)

1. Baixe o `server.jar` da versão desejada em
   [minecraft.net/download/server](https://www.minecraft.net/download/server)
2. Rode uma vez para gerar os arquivos:
   ```bash
   java -Xmx2G -jar server.jar nogui
   ```
3. Aceite a licença em `eula.txt` (`eula=true`)
4. **Edite `server.properties`:**
   ```properties
   online-mode=false
   max-players=10
   ```
5. Inicie de novo. No celular, use **Conexão direta** com `IP:25565`

> `online-mode=false` é o que permite contas offline. Em contrapartida, o
> servidor não verifica identidade — só use com gente conhecida, e prefira
> manter uma whitelist (`white-list=true` + `/whitelist add <nick>`).

### Hospedagem gratuita

| Serviço | Observação |
|---|---|
| [Aternos](https://aternos.org) | Grátis, hiberna quando vazio, permite `online-mode=false` |
| [Falixnodes](https://falixnodes.net) | Grátis com limitações |
| [Minehut](https://minehut.com) | Grátis, alguns planos exigem online-mode |

No painel do serviço, procure `online-mode` nas configurações e deixe como
`false`.

### VPS (mais estável)

Contabo, Hetzner ou Oracle Cloud (tem plano sempre-grátis). Custo típico:
R$ 20–40/mês para 2–4 GB de RAM, suficiente para 5–10 jogadores.

---

## Entrar direto no servidor ao abrir o jogo

O MineDrakk pode pular o menu e conectar automaticamente ao seu servidor.

1. Toque no ícone de editar perfil (ao lado do seletor de versão)
2. Preencha **"Join server on launch (1.20+)"** com o endereço
   (ex.: `meuservidor.com` ou `192.168.0.10:25565`)
3. Salve e toque em Jogar

> Requer **Minecraft 1.20 ou superior** — a flag `--quickPlayMultiplayer` não
> existe em versões anteriores. Em versões antigas o campo é ignorado e o jogo
> abre no menu normalmente, sem erro.

Deixe o campo vazio para voltar ao comportamento padrão.

Para gerenciar **vários servidores**, use a lista do próprio Minecraft
(Multijogador → Adicionar servidor) — ela já guarda quantos você quiser, com
ping e ícone.

---

## Nicks diferentes para cada jogador

**Importante:** cada pessoa precisa de um nick **diferente**.

Servidores offline identificam o jogador por um UUID derivado do nick
(`md5("OfflinePlayer:" + nick)`). Dois jogadores com o mesmo nick recebem o
mesmo UUID e o servidor os trata como a mesma pessoa — inventário, posição e
permissões se misturam.

O MineDrakk já gera esse UUID corretamente. Só garanta que ninguém repita nick.

---

## Problemas comuns

**"Failed to verify username"**
O servidor está com `online-mode=true`. Mude para `false` ou use uma conta
licenciada.

**"Connection refused" / "Connection timed out"**
* Confirme IP e porta (padrão `25565`)
* O servidor está rodando?
* Em servidor caseiro: libere a porta 25565 no roteador (*port forwarding*)
* Firewall do PC pode estar bloqueando

**O mundo LAN não aparece na lista**
Use **Conexão direta** com o IP do host. Alguns roteadores bloqueiam a
descoberta automática.

**"Outdated server" / "Outdated client"**
A versão do jogo precisa ser **exatamente** a mesma do servidor.
