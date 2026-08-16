# Identidade visual do MineDrakk

## Arquivos-fonte

| Arquivo | Uso |
|---|---|
| `logo_icon.png` | Arte completa do ícone (dragão + fundo), referência |
| `logo_foreground.png` | Dragão isolado — camada *foreground* do adaptive icon |
| `logo_wordmark_clean.png` | Lockup horizontal "MineDrakk" com transparência tratada |
| `build_assets.py` | Gera todas as densidades a partir das artes acima |

## Regenerar os assets

```bash
python3 branding/build_assets.py
```

Produz, em `app_pojavlauncher/src/main/res/`:

* `mipmap-*/ic_launcher.png` — ícone legado (Android < 8), cantos arredondados
* `mipmap-*/ic_launcher_round.png` — variante circular
* `mipmap-*/ic_launcher_foreground.png` — adaptive icon, dentro da safe zone de 66dp
* `mipmap-*/ic_launcher_background.png` — fundo sólido
* `mipmap-*/ic_launcher_monochrome.png` — Material You (Android 13+)
* `drawable-*/ic_minedrakk_wordmark.png` — logo da tela inicial
* `assets/minedrakk.png` — arte 512px

> As imagens geradas por IA vêm **sem canal alfa**: a transparência aparece
> desenhada como xadrez. O `build_assets.py` detecta e remove esse padrão.

## Paleta

| Token | Hex | Uso |
|---|---|---|
| `brand_primary` | `#2ECC71` | Cor da marca, botão jogar, destaques |
| `brand_primary_dark` | `#10B981` | Pressionado, gradientes |
| `brand_primary_light` | `#6EE7A8` | Hover, foco |
| `background_app` | `#12161A` | Fundo principal |
| `background_status_bar` | `#0D1114` | Barra de status |
| `background_bottom_bar` | `#161B20` | Barra inferior |
| `background_card` | `#1B2127` | Cards e superfícies elevadas |
| `background_overlay` | `#232A31` | Divisores, sobreposições |
| `primary_text` | `#F2F5F3` | Texto principal |
| `secondary_text` | `#9AA6A0` | Texto secundário |

Definida em `app_pojavlauncher/src/main/res/values/colors.xml`.
