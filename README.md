# Mapa WorkAdventure — Escritório

Mapa do escritório virtual, montado com os tilesets oficiais do WorkAdventure.

| Arquivo | O que é |
|---|---|
| `escritorio.tmj` | Mapa (abre no Tiled e roda no WorkAdventure) |
| `tilesets/wa/` | Tilesets oficiais do WorkAdventure + `LICENSE.assets` |
| `tilesets/amz.png` | Tiles próprios: logo da MAJU e rótulos das salas |
| `assets/maju_logo.png` | Logo usado na recepção e na diretoria |
| `preview.png` / `preview_2x.png` | Prévia do mapa (tamanho real / ampliada 2×) |
| `preview_areas.png` | Áreas de Jitsi (laranja), área silenciosa (azul), recepção (verde) e pontos de entrada (rosa) |
| `PONTOS_DE_ENTRADA.md` | Lista dos pontos de entrada por mesa |
| `tools/build_map.py` | Gera tudo acima: `python tools/build_map.py` |

## Camadas

- `start`, `mesa-01` … `diretoria`, `collisions`: ficam por baixo do piso (como no mapa oficial do WorkAdventure).
  `start` é a recepção (convidados); as demais têm `startLayer = true` e são usadas com `#nome` no link.
- `floor`, `floor2`, `walls`, `deco1`, `deco2`, `furniture1-3`, `labels`: abaixo do personagem
- `floorLayer`: áreas (`jitsiRoom`, `silent`)
- `above1`, `above2`: tampo das mesas, copa das árvores e plantas (acima do personagem)

As colisões ficam na camada `collisions` (tile BLOCK do `WA_Special_Zones`, com `collides = true`).

## Licença dos tilesets

Os arquivos em `tilesets/wa/` são do WorkAdventure e seguem a *WorkAdventure specific resources license*
(`tilesets/wa/LICENSE.assets`): uso e modificação permitidos apenas em mapas para WorkAdventure.

## Publicação

O mapa é servido pelo GitHub Pages:
`https://office.amzlab.site/_/global/leoamzz.github.io/mapa-escritorio/escritorio.tmj`

> Se editar o mapa à mão no Tiled, rodar o script de novo sobrescreve `escritorio.tmj`.
