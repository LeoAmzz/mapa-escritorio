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
- `mesa-01` … `mesa-25`, `escritorio-1`, `dra-julia`, `juridico-silvio`, `diretoria`:
  pontos de entrada (`startLayer = true`). Lista em `PONTOS_DE_ENTRADA.md`; use `#nome` no link do mapa.

As colisões ficam na propriedade `collides` dos tiles (paredes, mesas, plantas, água...). Cadeiras e sofás não colidem.

## Mesa de cada pessoa

Quem tem mesa definida e abre o link do mapa **sem `#`** nasce na recepção e é levado direto para a
própria mesa. Convidados (sem mesa) continuam na recepção. Quem abre com `#ponto` no link vai para
aquele ponto, como antes.

1. Copie `mesas.exemplo.csv` para `mesas.local.csv` e coloque uma pessoa por linha: `e-mail;ponto`
   (por exemplo `fulana@empresa.com;mesa-07`). O ponto é um dos nomes de `PONTOS_DE_ENTRADA.md`.
2. Rode `python tools/build_map.py`. Ele gera `scripts/mesas.json` e avisa se algum ponto não existe
   ou se duas pessoas estão na mesma mesa.
3. Publique (commit e push) como de costume.

O `mesas.local.csv` fica só no seu PC (está no `.gitignore`). No GitHub vai apenas o hash de cada
e-mail, então ninguém lê a lista no repositório público. Quem já souber um e-mail ainda consegue
testar se ele está na lista; para dados realmente sigilosos, use o servidor próprio.

O script (`scripts/boas-vindas.js`) compara o hash com o identificador da conta no WorkAdventure
(`WA.player.id`). No console do navegador (F12) aparece `[mesas] identificador desta conta: ...`:
se não for o e-mail, use na lista exatamente o identificador que aparece ali.

## Publicar no servidor

Copie `escritorio.tmj` e a pasta `tilesets/` juntos para onde o WorkAdventure serve os mapas, mantendo o caminho relativo
`tilesets/escritorio.png`.

> Se editar o mapa à mão no Tiled, rodar o script de novo sobrescreve `escritorio.tmj`.
