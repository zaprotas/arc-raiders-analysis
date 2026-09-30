"""Gera notebooks/06_decisao.ipynb (executar depois com nbconvert --execute)."""
import nbformat as nbf

nb = nbf.v4.new_notebook()
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
img = lambda name: code(f'Image("../reports/figures/{name}.png")')

nb["cells"] = [
    md("""# 06 · Decisão: investir no ARC Raiders em 2027?

Etapa 9 do projeto. A pergunta de negócio: **a Embark deve manter o desenvolvimento e o investimento no ARC Raiders em 2027?** A análise foi fechada em 30/09/2026, antes do Frozen Trail (08/10/2026).

A decisão real não é "manter ou abandonar": mesmo sem conteúdo novo, uma equipe mínima (servidores, anti-cheat, loja) continua recebendo a receita da base atual. Então comparamos **duas estratégias para 2027**:

| Estratégia | O que inclui | Equipe [P] |
|---|---|---|
| **Investir** | grandes atualizações semestrais + modo PvE + skins de armas (cenário S3) | 150–250 pessoas |
| **Mínimo** | manutenção, sem conteúdo novo (cenário S0) | 30–60 pessoas |

**Custo** (não é público; faixa [P]): US$ 95–135 mil por pessoa ao ano (salário bruto de SEK 650–850 mil com ~50% de encargos e benefícios suecos) × 1,3–1,6 de outros custos (servidores, anti-cheat, marketing, terceiros). A Embark tinha ~350 pessoas em 2025, divididas entre ARC Raiders e The Finals.

**Receita:** as projeções da Etapa 8, nas variantes base e pessimista."""),
    code("""import json, sys
from pathlib import Path
from IPython.display import Image

sys.path.insert(0, str(Path.cwd().parent / "src"))
from analysis import decision

decision.main()
metrics = json.loads(Path("../reports/metrics_decisao.json").read_text(encoding="utf-8"))
metrics["resumo"]"""),

    md("""## 1. Resultado de 2027 por estratégia

| 2027 (US$ mi) | Base: investir | Base: mínimo | Pessimista: investir | Pessimista: mínimo |
|---|---|---|---|---|
| Receita | 127 (87–183) | 34 | 49 (32–74) | 19 |
| Custo | 33 (26–42) | ~8 | 33 (26–42) | ~8 |
| **Resultado** | **94** (53–151) | 26 (18–36) | **16** (−3 a 42) | 11 (5–20) |

**Ganho de investir sobre o mínimo:**
- **Cenário base: +US$ 67 mi** (30 a 120), positivo em 100% das simulações; cada US$ 1 a mais de custo gera ~US$ 2,70 de ganho líquido.
- **Cenário pessimista: +US$ 5 mi** (−10 a +25), positivo em 64% das simulações: praticamente empata.

Investir nunca perde muito (pior caso realista: −US$ 10 mi no pessimista) e pode ganhar muito (até +US$ 120 mi no base). A assimetria favorece investir, **desde que haja um ponto de saída** caso o mundo pessimista se confirme."""),
    img("12a_resultado_2027_estrategias"),

    md("""## 2. O limite de decisão

Base e pessimista começam iguais: o Frozen Trail deve levar a média de outubro a ~42 mil jogadores na Steam nos dois casos. **A diferença aparece três meses depois**, quando se vê quanto da alta ficou: em jan/2027, a mediana é de **28,7 mil** no base e **18,7 mil** no pessimista.

Cruzando todas as simulações, **investir dá ganho positivo em 70%+ dos casos quando jan/2027 fecha com 19 mil jogadores ou mais** na média da Steam. Esse é o número a acompanhar."""),
    img("12b_limite_de_decisao"),

    md("""## 3. Quadro de indicadores (limites definidos antes do Frozen Trail)

Definir os limites **antes** de ver os resultados evita ajustar a régua ao que acontecer.

| # | Indicador | Hoje | Limite para manter o plano | Quando medir | Fonte |
|---|---|---|---|---|---|
| 1 | Média de jogadores na Steam em out/2026 | 21 mil (set) | **≥ 35 mil** (10º percentil das simulações) | início de nov/2026 | SteamCharts |
| 2 | **Média de jogadores na Steam em jan/2027** | — | **≥ 19 mil** (limite de decisão) | início de fev/2027 | SteamCharts |
| 3 | Retenção da alta: jan/2027 ÷ out/2026 | — | ≥ 55% (base: 68%; pessimista: 44%) | início de fev/2027 | SteamCharts |
| 4 | Análises positivas na Steam (out–dez/2026) | 51% (set) | ≥ 65% | jan/2027 | Steam (Etapa 5) |
| 5 | Reclamações de cheaters por 100 análises | 25 (set) | ≤ 15 | mensal | Steam (Etapa 5) |
| 6 | Adoção do PvE no teste de 13–20/10 | — | ≥ 25% dos jogadores | quando a Embark divulgar | Embark |

**Regra:** os indicadores 2 e 3 decidem; 1, 4, 5 e 6 são sinais antecipados e orientam prioridades."""),

    md("""## 4. Recomendação: MANTER O INVESTIMENTO EM 2027, COM UM PONTO DE REVISÃO EM FEV/2027

**Por que manter**
1. **O ativo é valioso:** ~US$ 660 mi de receita em 11 meses, 16,6 mi de unidades, segunda maior estreia de tiro da Steam no período e 82% de análises positivas no total.
2. **O público que saiu gosta do jogo:** os veteranos que abandonaram (30% dos autores) recomendam o jogo (84%). É um público recuperável com conteúdo, não um público perdido.
3. **Conteúdo novo funciona:** as atualizações seguraram a curva (+20% sobre a tendência, Etapa 4), e os comparáveis mostram que 2/3 da alta de uma grande atualização costumam ficar.
4. **A aposta é assimétrica:** ganho esperado de +US$ 67 mi no base contra perda máxima realista de ~US$ 10 mi no pessimista.

**Condições (o que precisa ser feito junto)**
1. **Anti-cheat como prioridade nº 1 até o fim de 2026:** cheaters são a reclamação que mais derruba a nota (−28 p.p. na chance de recomendar) e 34% das queixas dos veteranos ativos, o núcleo que ficou.
2. **Congelar nerfs em armas populares:** patches de balanceamento antecederam as quedas (−12% sobre a tendência; reclamações +60% nas semanas seguintes). Preferir buffs e ajustes em armas pouco usadas.
3. **Reduzir o vale entre as grandes atualizações:** eventos e projetos menores a cada 4–6 semanas, como no Tarkov e no Helldivers 2. A queda entre atualizações é o que separa o cenário base do pessimista.
4. **Transformar o teste de PvE em modo permanente em abr/2027 se a adoção passar de 25%:** fala com os casuais persistentes (27%) e com os 37% de jogadores cooperativos.
5. **Skins de armas como complemento:** ~8% da receita projetada; monitorar se a perda de skins ao morrer derruba a conversão.

**Ponto de revisão em fev/2027 (com os dados de jan/2027)**
- **Jan ≥ 19 mil e retenção ≥ 55%:** seguir o plano completo de 2027 (atualização de abr/2027 + PvE + atualização de out/2027).
- **Jan < 19 mil:** entregar a atualização de abril, que já estará em produção, e reduzir a equipe para manutenção depois dela, realocando pessoas para outros projetos da Embark.

**Fora do modelo (potencial de alta):** um possível lançamento na China (noticiado pela imprensa especializada, sem confirmação), versões em novas plataformas, valor da marca para uma sequência e sinergias técnicas com The Finals. Nenhum desses entrou nos números."""),
]
nb["metadata"]["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, "06_decisao.ipynb")
print("ok")
