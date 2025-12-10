# Trabalho Final INF1771 
## Membros:
2511704 - Sol Castilho Araújo De Moraes Sêda
1713053 - Isabelle Silva Nazareth 
2110292 - Isabel C S C T Ribeiro
## Estados da IA
- `EXPLORE`: estado padrão; caminha por células seguras priorizando menos visitadas, evitando hazards/bloqueios e penalizando riscos (breeze/flash).
- `COLLECT`: quando observa itens úteis (`blueLight`, `redLight`, `weakLight`); executa `pegar_*` e evita `greenLight`.
- `CHASE`: ao detectar inimigo (`enemy`/`enemy#N`); persegue e atira se perto ou após confirmar `hit`.
- `EVADE`: ao tomar dano ou durante janelas de evasão; tenta sair da linha de visão recuando ou virando para lado seguro.
- `SEARCH`: quando ouve passos; gira alternando lados para localizar alvo.

## Planejamento para ouro (A*)
- A partir de 100 ações (`action_counter >= 100`), se houver ouro conhecido em célula segura/visitada e o estado for `EXPLORE`/`COLLECT`/`SEARCH`, a IA roda A* sobre o grafo de células 

## Outras regras relevantes
- Se virar demais em `EXPLORE`/`SEARCH`, força um movimento à frente ou ré quando seguro. Isso foi feito para evitar um loop de giro que estava acontecendo
- Se tentar `pegar_ouro` 3x na mesma célula, descarta o spot e volta a `EXPLORE`. Isso foi feito para forçar o bot a andar e evitar um bug que acontecia dele ficar parado em um lugar com ouro em alguns casos
- Navegação: evita `hazards`/`blocked`, prefere células menos visitadas e não arriscadas; `breeze`/`flash` marcam adjacentes como arriscadas (não bloqueiam, mas são evitadas).
