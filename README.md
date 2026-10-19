# Mapa WorkAdventure — Escritório

Mapa gerado por código (pixel art 32×32), no layout da referência.

| Arquivo | O que é |
|---|---|
| `escritorio.tmj` | Mapa (abre no Tiled e roda no WorkAdventure) |
| `tilesets/escritorio.png` | Tileset gerado (piso, paredes, móveis, rótulos) |
| `preview.png` | Prévia do mapa (tamanho real) |
| `preview_2x.png` | Prévia ampliada 2×, como aparece com zoom no jogo |
| `comparacao.png` | Trecho do salão antes/depois do detalhamento dos tiles |
| `preview_areas.png` | Prévia com as áreas de Jitsi (laranja), área silenciosa (azul) e o spawn (verde) |
| `assets/maju_logo.png` | Logo usado no tapete do salão e na placa da diretoria |
| `tools/build_map.py` | Gera tudo acima: `python tools/build_map.py` |

## Camadas

- `floor`, `walls`, `furniture`, `labels`: abaixo do personagem
- `floorLayer`: camada de objetos com as áreas (`class: area`, propriedade `jitsiRoom`)
- `above`: copa das árvores (acima do personagem)
- `start`: entrada padrão, na recepção (convidados)
- `mesa-01` … `mesa-20`, `baia-1` … `baia-4`, `escritorio-1`, `dra-julia`, `juridico-silvio`, `diretoria`:
  pontos de entrada (`startLayer = true`). Lista em `PONTOS_DE_ENTRADA.md`; use `#nome` no link do mapa.

As colisões ficam na propriedade `collides` dos tiles (paredes, mesas, plantas, água...). Cadeiras e sofás não colidem.

## Publicar no servidor

Copie `escritorio.tmj` e a pasta `tilesets/` juntos para onde o WorkAdventure serve os mapas, mantendo o caminho relativo
`tilesets/escritorio.png`.

> Se editar o mapa à mão no Tiled, rodar o script de novo sobrescreve `escritorio.tmj`.
