# Dicionário de dados

Tabelas tratadas na Etapa 3, geradas pelos scripts em `src/clean/`. As etiquetas de confiança ([O], [E], [G], [P]) estão explicadas em [SOURCES.md](SOURCES.md).

Para regenerar tudo a partir dos dados brutos:

```bash
python src/clean/players.py
python src/clean/twitch.py
python src/clean/events.py
python src/clean/reviews.py
```

## `interim/players_monthly.csv` [O]

Jogadores simultâneos na Steam por mês, 15 jogos. Fonte: SteamCharts. Gerado por `players.py`.

| Coluna | Tipo | Descrição |
|---|---|---|
| `appid` | int | ID do jogo na Steam |
| `game` | texto | Nome do jogo |
| `group` | texto | `arc_raiders`, `extraction`, `extraction_hybrid`, `fps`, `reference_pve`, `reference_updates` |
| `month` | data | Primeiro dia do mês |
| `avg_players` | float | Média de jogadores simultâneos no mês |
| `peak_players` | int | Maior número de jogadores simultâneos no mês |
| `partial_month` | bool | `True` para setembro/2026 (últimos 30 dias até a coleta) |
| `months_since_launch` | int | Meses desde o primeiro mês com dados no SteamCharts (0 = mês de estreia na Steam) |
| `peak_index` | float | `avg_players` como % da maior média mensal do próprio jogo (100 = melhor mês) |

Validação: pico mensal do SteamCharts bate com o do SteamDB em todos os meses (diferença máxima de 4,9%, em nov/2025).

## `interim/arc_players_daily.csv` [O]

ARC Raiders por dia na Steam, de 30/10/2025 a 25/09/2026. Fonte: SteamDB (exportado pelo usuário). Gerado por `players.py`.

| Coluna | Tipo | Descrição |
|---|---|---|
| `date` | data | Dia |
| `peak_players` | int | Maior número de jogadores simultâneos no dia |
| `mean_players` | float | Média dos registros do dia; vazio quando o SteamDB exporta só um ponto diário |
| `points` | int | Quantos registros o dia teve (1 = só o pico; ~144 = a cada 10 minutos) |

## `interim/twitch_monthly.csv` [O]

Audiência mensal na Twitch: ARC Raiders, Escape from Tarkov, Hunt: Showdown 1896, Battlefield 6 e Marathon. Fonte: TwitchTracker (prints transcritos). Gerado por `twitch.py`.

| Coluna | Tipo | Descrição |
|---|---|---|
| `game` | texto | `arc_raiders`, `escape_from_tarkov`, `hunt_showdown`, `battlefield_6`, `marathon` |
| `month` | data | Mês real, já corrigido |
| `label_month` | data | Mês como aparece na tabela do site (um mês antes do real) |
| `avg_viewers` | int | Média de espectadores simultâneos |
| `peak_viewers` | int | Pico de espectadores simultâneos |
| `avg_streams` | int | Média de canais transmitindo ao mesmo tempo |
| `peak_streams` | int | Pico de canais transmitindo |
| `hours_watched` | float | Horas assistidas no mês |
| `partial_month` | bool | `True` para setembro/2026 (até ~24/09) |

## `interim/arc_events.csv` [O]

Linha do tempo de anúncios oficiais do ARC Raiders na Steam (77 eventos, dez/2021 a set/2026). Gerado por `events.py`.

| Coluna | Tipo | Descrição |
|---|---|---|
| `date` | data | Data do anúncio |
| `kind` | texto | `launch`, `major_update`, `major_update_announcement`, `live_update`, `hotfix`, `store_update`, `expedition`, `survey`, `communication`, `pre_launch` |
| `title` | texto | Título do anúncio |
| `text_len` | int | Tamanho do texto integral (indicador do volume de mudanças) |
| `n_balance` | int | Menções a balanceamento (balance, nerf, buff, ajustes de dano) |
| `n_anticheat` | int | Menções a cheat, anti-cheat e banimentos |
| `n_exploit` | int | Menções a exploits |
| `n_bugfix` | int | Menções a correções ("fix", "fixed", "fixes") |
| `n_matchmaking` | int | Menções a pareamento |
| `n_new_content` | int | Menções a conteúdo novo (mapa, arma, inimigo, trader, missão, evento…) |
| `url` | texto | Link do anúncio |

`major_update` = atualização de conteúdo com nome (North Line, Cold Snap, Headwinds, Shared Watch, Shrouded Sky, Flashpoint, Riven Tides). A partir de maio/2026 só há `live_update` e `store_update`, até o Frozen Trail (08/10/2026).

## `interim/arc_reviews.parquet` [O] (fora do git, ~100 MB)

Todas as análises do ARC Raiders na Steam: 416.780 de 416.929 (99,96%). Gerado por `reviews.py`. **Sem dados pessoais:** steamid, apelido, perfil e avatar do autor foram removidos.

| Coluna | Tipo | Descrição |
|---|---|---|
| `review_id` | int | ID da análise |
| `created`, `updated` | datetime | Criação e última edição (UTC) |
| `month` | data | Mês de criação |
| `language` | texto | Idioma da análise (indicador de região) |
| `voted_up` | bool | Recomenda o jogo |
| `text` | texto | Texto da análise |
| `text_len` | int | Número de caracteres (34% têm menos de 20) |
| `votes_up`, `votes_funny` | int | Votos de "útil" e "engraçado" recebidos |
| `weighted_vote_score` | float | Pontuação de utilidade calculada pela Steam |
| `steam_purchase` | bool | Comprado na Steam (`False` = key de outra loja) |
| `received_for_free` | bool | Recebeu o jogo de graça |
| `primarily_steam_deck` | bool | Jogou principalmente no Steam Deck |
| `playtime_forever_min` | int | Minutos jogados no total, na data da coleta |
| `playtime_at_review_min` | int | Minutos jogados quando escreveu a análise |
| `playtime_2weeks_min` | int | Minutos jogados nas duas semanas antes da coleta (85,8% = 0) |
| `last_played` | datetime | Última vez que jogou |
| `days_since_last_played` | int | Dias entre `last_played` e a coleta (25/09/2026) |
| `author_games_owned` | int | Jogos na biblioteca do autor |
| `author_num_reviews` | int | Análises que o autor já escreveu na Steam |

Valores extremos: 18 análises (0,004%) somam mais de 5.000 horas em 11 meses, provavelmente jogo aberto sem uso. O modelo RFE limita esses valores no percentil 99,9.

## `external/official_milestones.csv` [O]

Marcos oficiais: unidades vendidas, receita, pico em todas as plataformas (Nexon), divisão de estilos de jogo e datas (Embark), audiência de lançamento (Streams Charts). A coluna `source_type` indica se veio do release primário ou da imprensa.

Derivado usado na análise: no mês de pico (jan/2026), a Steam teve 466.372 jogadores simultâneos (SteamDB) contra 960.000 em todas as plataformas (Nexon). **A Steam representa cerca de 49% do público**, e consoles e outras lojas os outros 51%.

## `external/genre_demographics.csv` [G]

Referências demográficas do gênero de tiro e do mercado (Quantic Foundry, ESA, Newzoo), com ano e fonte em cada linha.

## `raw/sensortower_vgi_quickstats_2026-09-25.csv` [E]

Estimativas do Sensor Tower (conta gratuita) para 13 jogos: unidades, receita de venda na Steam, tempo de jogo médio e mediano, % de análises positivas. Valores só da Steam.
