import nbformat as nbf

nb = nbf.v4.new_notebook()
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
img = lambda name: code(f'Image("../reports/figures/{name}.png")')

cells = [
    md("""# 01 · Diagnóstico: da estreia à queda

Etapa 4 do projeto. Responde às perguntas de diagnóstico com os dados tratados na Etapa 3:

1. Como o ARC Raiders se posicionou frente aos FPS e extraction shooters consolidados
2. Média e pico de jogadores por mês, comparados aos concorrentes
3. A queda mês a mês e a retenção no primeiro ano
4. Conversão da lista de desejos em vendas
5. Efeito das atualizações de conteúdo e dos patches de balanceamento
6. Hype (Twitch) x base de jogadores
7. Perfil dos jogadores

Etiquetas de confiança: **[O]** observado, **[E]** estimado por terceiros, **[G]** referência do gênero, **[P]** premissa. Detalhes em `data/SOURCES.md`."""),
    code("""import json, sys
from pathlib import Path
from IPython.display import Image

sys.path.insert(0, str(Path.cwd().parent / "src"))
from analysis import diagnostics

diagnostics.main()  # regenera todas as figuras e métricas desta etapa
metrics = json.loads(Path("../reports/metrics_diagnostico.json").read_text(encoding="utf-8"))"""),

    md("""## 1. Posicionamento no lançamento

O ARC Raiders estreou entre os maiores lançamentos de tiro dos últimos anos:

- **2º maior pico de estreia na Steam** entre 11 jogos comparáveis (465 mil), atrás só do Battlefield 6 (656 mil) e à frente do Helldivers 2.
- **3º em análises positivas** (82%), empatado com Rainbow Six Siege e acima de todos os extraction shooters.
- **2º em horas assistidas na Twitch** no lançamento (100 mi), atrás só do Tarkov na versão 1.0.
- **4º em unidades na Steam** (8,7 mi [E]), mesmo sendo o mais novo da lista depois do Marathon.

Fora da Steam, a Nexon reportou **pico de 960 mil jogadores simultâneos** em todas as plataformas e **10,9 mi de unidades** até dez/2025."""),
    img("01_posicionamento_lancamento"),

    md("""## 2. Jogadores por mês

A média mensal caiu **92%** entre nov/2025 (264 mil) e set/2026 (21 mil). O pico mensal seguiu o mesmo caminho: de 465 mil (jan/2026) para 37 mil."""),
    img("02a_jogadores_mes_arc"),
    md("""No mesmo calendário, o ARC Raiders saiu do patamar de PUBG e Apex para o de Tarkov e Hunt. Os FPS consolidados (CS2, PUBG, Apex, Rainbow Six) ficaram praticamente estáveis no período, então a queda não é do mercado: é do jogo."""),
    img("02b_jogadores_mes_concorrentes"),
    md("""Alinhando todos pelo mês de estreia, o ARC Raiders tem a curva típica de um grande lançamento que não segurou a base: acima dos pares nos 4 primeiros meses, entre os mais baixos a partir do 8º."""),
    img("02c_ciclo_de_vida"),

    md("""## 3. A queda vertiginosa

A queda não foi uniforme. Houve **uma única alta** (jan/2026, com Headwinds e o recorde de 960 mil em todas as plataformas) e **três quedas acima de 30%** (mar, abr e jun/2026). Jun/2026 (−41%) é o primeiro mês inteiro sem atualização de conteúdo depois do anúncio da nova cadência."""),
    img("03a_queda_mes_a_mes"),
    md("""O paradoxo da retenção: o ARC Raiders foi o jogo que **mais demorou para perder metade da base** (4 meses), mas chegou ao 10º mês com **9% do melhor mês**, à frente só de Gray Zone Warfare. Hunt, Rainbow Six e Delta Force mostram que um jogo de tiro pode se estabilizar; o ARC Raiders ainda não encontrou esse piso."""),
    img("03b_retencao"),

    md("""## 4. Lista de desejos → vendas

O número de desejos no lançamento não é público, então tratamos como cenário. Estimamos **3,7 mi de unidades na Steam nos primeiros 30 dias** [E], com um método validado contra os números oficiais (erro de 1% até dez/2025).

Mesmo no cenário mais conservador (5 mi de desejos), a conversão foi de **75%**, quase 3x a mediana da Steam (27%). Com os 2,5 mi relatados em ago/2025, passaria de 149%, acima dos 10% melhores. **A demanda veio muito além de quem já tinha o jogo na lista**: streamers e boca a boca trouxeram compradores novos."""),
    img("04_lista_de_desejos_conversao"),

    md("""## 5. Efeito das atualizações e dos patches

Estudo de evento: para cada atualização, comparamos o pico diário médio da semana seguinte com a tendência de queda dos 28 dias anteriores.

- **Atualizações de conteúdo** (mapas, eventos, inimigos): efeito médio de **+20%** sobre a tendência (mediana +17%). Flashpoint (+43%) e Riven Tides (+51%) foram as maiores.
- **Patches com balanceamento**: efeito médio de **−12%** (mediana −17%). Os cinco ficaram abaixo da tendência, três deles em −17% ou mais.

Depois de Riven Tides (28/04) não houve mais atualização de conteúdo, e o jogo perdeu o único mecanismo que vinha interrompendo a queda.

**Cuidado na leitura:** são 11 eventos e o estudo mede associação, não causa. Um patch pode coincidir com outros fatores (fim de evento, lançamento de concorrente). A análise de reclamações (Etapa 5) vai testar se os temas de balanceamento aparecem nas análises negativas dessas semanas."""),
    img("05a_atualizacoes_linha_do_tempo"),
    img("05b_efeito_atualizacoes"),

    md("""## 6. Hype x base de jogadores

A audiência na Twitch caiu **antes e mais rápido** que o número de jogadores: em dez/2025 já estava em 66% de nov/2025, contra 87% dos jogadores. Hoje está em 5% do lançamento, contra 8% dos jogadores. O hype é um indicador antecedente: quando os streamers saem, os jogadores seguem."""),
    img("06_twitch_x_jogadores"),

    md("""## 7. Quem joga ARC Raiders

- **Região** (idioma das análises): 60% em inglês, 11% em russo, depois alemão, português (4,2%), francês e espanhol. Público majoritariamente ocidental, com Rússia/CEI forte e Ásia pequena (chinês 1,4%, coreano 1%).
- **Plataforma**: a Steam é cerca de **49%** do público; consoles e outras lojas, 51%.
- **Estilo de jogo** (Embark): **37% cooperativos**, 27% mistos, 34% só PvP. O grupo cooperativo cresce desde o lançamento, e **51% querem um modo PvE**.
- **Engajamento**: mediana de **138 horas** jogadas por quem avaliou, mas só **14%** jogaram nas duas semanas antes da coleta.
- **Idade e gênero** não são públicos. Referências do gênero [G]: jogadores de FPS são ~93% homens e ~7% mulheres (Quantic Foundry, 2017); nos EUA, jogos de tiro concentram o público jovem, com preferência abaixo de 10% após os 62 anos (ESA, 2026)."""),
    img("07_perfil_jogadores"),

    md("""## Síntese do diagnóstico

1. **O lançamento foi excepcional**: top 2 em pico, audiência e conversão de desejos, com 82% de análises positivas.
2. **A retenção é o problema**: −92% em 11 meses, 9% do melhor mês no 10º mês, entre os piores do grupo.
3. **Conteúdo novo funciona, balanceamento não**: atualizações de conteúdo seguraram a curva (+20% em média); patches de balanceamento coincidiram com quedas (−12%).
4. **A pausa de conteúdo desde maio acelerou a queda**, e no mesmo período as análises positivas foram de 66% (abr) para 51% (set).
5. **O público quer outra coisa**: 37% cooperativos e 51% interessados em PvE, o que dá peso ao teste de PvE de outubro.

Próximas etapas: reclamações (Etapa 5) para explicar *por que* os jogadores saíram, e RFE + agrupamento (Etapa 6) para saber *quem* saiu."""),
]
nb["cells"] = cells
nb["metadata"]["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, r"C:\dev\arc-raiders-analysis\notebooks\01_diagnostico.ipynb")
print("ok")
