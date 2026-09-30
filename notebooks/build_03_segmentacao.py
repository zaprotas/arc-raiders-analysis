"""Gera notebooks/03_segmentacao.ipynb (executar depois com nbconvert --execute)."""
import nbformat as nbf

nb = nbf.v4.new_notebook()
md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
img = lambda name: code(f'Image("../reports/figures/{name}.png")')

nb["cells"] = [
    md("""# 03 · Modelo RFE e agrupamento: quem ficou e quem saiu

Etapa 6 do projeto. O projeto de referência usa **RFM** (Recência, Frequência, Valor monetário) para segmentar clientes de varejo. Não temos compras por jogador, mas cada análise da Steam traz o perfil de jogo do autor. Adaptamos para **RFE**:

| Letra | Indicador | Como é calculado |
|---|---|---|
| **R** | Recência | dias entre a última sessão e a coleta (25/09/2026) |
| **F** | Frequência | horas por semana entre o lançamento e a última sessão |
| **E** | Engajamento | horas jogadas no total (substitui o valor monetário) |

Como no projeto de referência, trabalhamos em duas camadas: **notas RFE de 1 a 5** (quintis) para leitura de negócio e **K-Means** sobre R, log(F) e log(E) padronizados para encontrar os grupos. Depois cruzamos os grupos com o voto e com as reclamações da Etapa 5.

**Viés conhecido:** os 416,8 mil autores de análises são ~5% das unidades vendidas na Steam e mais engajados que a média. Os grupos descrevem esse público, não todos os compradores."""),
    code("""import json, sys
from pathlib import Path
from IPython.display import Image

sys.path.insert(0, str(Path.cwd().parent / "src"))
from analysis import segmentation

segmentation.main()
metrics = json.loads(Path("../reports/metrics_segmentacao.json").read_text(encoding="utf-8"))"""),

    md("""## 1. Quantos grupos

Testamos k de 2 a 8. A silhueta é máxima em **k = 4** (0,369), no mesmo ponto em que a curva de inércia começa a achatar. Com k = 5, o grupo extra só dividia os veteranos ativos em dois, sem diferença de comportamento útil para o negócio."""),
    img("09a_escolha_k"),

    md("""## 2. Os quatro grupos

| Grupo | % dos autores | Nota RFE média (3–15) | Perfil |
|---|---|---|---|
| **Veteranos ativos** | 27% | 13,1 | Última sessão há 38 dias (mediana), 11,5 h/semana, 435 h no total; 35% jogaram nas últimas 2 semanas |
| **Veteranos que abandonaram** | 30% | 8,4 | Jogaram 9,7 h/semana e pararam há ~7 meses (228 dias); 126 h no total |
| **Casuais persistentes** | 27% | 8,5 | 3,3 h/semana por meses seguidos, última sessão há 65 dias, 114 h no total |
| **Desistiram cedo** | 16% | 4,3 | 22 h no total, pararam há ~7 meses |

O dado mais importante está na última coluna do gráfico: **os veteranos que abandonaram recomendam o jogo (84%)**. Eles não saíram por raiva: jogaram intensamente, esgotaram o conteúdo e pararam."""),
    img("09b_perfil_grupos"),

    md("""## 3. Quando cada grupo chegou e saiu

- **Veteranos que abandonaram**: 63% escreveram a análise ainda em nov/2025 (os entusiastas do lançamento). A última sessão se concentra entre dez/2025 e abr/2026, com pico em **mar/2026**, justamente o mês de −34% na média de jogadores.
- **Desistiram cedo**: saíram ao longo de nov/2025 a mar/2026, sem pico.
- **Veteranos ativos** e **casuais persistentes** são quem sustentou o jogo depois de abril.

A queda de fev–abr/2026 não foi de jogadores insatisfeitos, mas da maior fatia do núcleo engajado ficando sem motivo para voltar, enquanto ainda havia uma atualização por mês."""),
    img("09d_grupos_no_tempo"),

    md("""## 4. Do que cada grupo reclama

- **Veteranos ativos**: **cheaters (34%)**, três vezes mais que qualquer outro grupo, além de exploits (7%) e pareamento (16%). É o núcleo que ficou e o que mais sofre com trapaça.
- **Veteranos que abandonaram**: ratos e campers (25%) e falta de PvE (23%). Cheaters pesam pouco (11%): saíram antes da explosão de trapaça de jun/2026.
- **Casuais persistentes**: falta de PvE (23%) e ratos (22%), o perfil do jogador cooperativo que a Embark descreveu (37% da base).
- **Desistiram cedo**: queixas em geral mais baixas; falta de PvE (17%) e ratos (14%) na frente.

Idioma: os veteranos que abandonaram são mais anglófonos (66% em inglês, 8% em russo); os casuais persistentes têm mais russo (15%)."""),
    img("09c_reclamacoes_por_grupo"),

    md("""## Síntese: o que cada grupo pede

| Grupo | Situação | O que traria de volta ou manteria |
|---|---|---|
| Veteranos ativos (27%) | Ficaram, mas a nota caiu | **Anti-cheat** e punição a exploits; é o grupo com risco imediato de saída |
| Veteranos que abandonaram (30%) | Saíram satisfeitos | **Conteúdo novo de peso** e progressão de longo prazo: o alvo natural do Frozen Trail |
| Casuais persistentes (27%) | Ficam, jogando pouco | **Modo PvE / menos PvP forçado**: o alvo do teste de PvE de 13–20/10 |
| Desistiram cedo (16%) | Saíram cedo | Onboarding e proteção ao iniciante; menor prioridade |

Esses grupos alimentam as projeções da Etapa 8: cada frente (atualização semestral, PvE, skins) fala com um grupo diferente."""),
]
nb["metadata"]["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, "03_segmentacao.ipynb")
print("ok")
