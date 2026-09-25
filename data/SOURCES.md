# Fontes de dados

Etiquetas de confiança usadas em todo o projeto:

- **[O] Observado:** dado medido diretamente na fonte (ex.: jogadores simultâneos na Steam).
- **[E] Estimado por terceiros:** estimativa publicada por outra empresa (ex.: vendas no Sensor Tower VGI).
- **[G] Referência do gênero:** dado do gênero FPS/extraction shooter ou de jogos comparáveis, usado no lugar do dado do Arc Raiders.
- **[P] Premissa:** hipótese do projeto, sempre justificada.

## Coletadas (Etapa 2)

| Fonte | Dados | Etiqueta | Coleta | Arquivo | Limitações |
|---|---|---|---|---|---|
| [SteamCharts](https://steamcharts.com) | Média e pico mensais de jogadores simultâneos, 15 jogos | [O] | 2026-09-25 | `raw/steamcharts_monthly_2026-09-25.csv` | Só Steam (sem consoles). Set/2026 = últimos 30 dias (`partial_month`). Out/2025 ausente (lançamento em 30/10). |
| [API de análises da Steam](https://partner.steamgames.com/doc/store/getreviews) | Resumo de análises (positivas/negativas) por jogo | [O] | 2026-09-25 | `raw/steam_reviews_summary_2026-09-25.csv` | Só Steam. |
| API de análises da Steam | Texto, voto, idioma e horas jogadas de cada análise do ARC Raiders | [O] | 2026-09-25 | `raw/steam_reviews_1808500_recent_all.jsonl` (435 MB, fora do git) | 416.780 de 416.929 análises (99,96%), de 30/10/2025 a 25/09/2026, sem duplicatas. A paginação da API devolve páginas vazias intermitentes; o coletor retoma do cursor salvo. Só Steam. |
| [API de notícias da Steam](https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/) | Anúncios oficiais (patches, hotfixes, grandes atualizações) de 15 jogos | [O] | 2026-09-25 | `raw/steam_news_2026-09-25.csv` | Classificação por título é automática e será revisada à mão. |
| [arcraiders.com/news](https://arcraiders.com/news) e anúncios da Steam | Texto integral de publicações estratégicas da Embark | [O] | 2026-09-25 | `external/official_posts/*.txt` | — |
| [Sensor Tower VGI](https://app.sensortower.com/vgi/) (conta gratuita) | Estimativas Steam: unidades, receita de venda, tempo de jogo, % positivas, 13 jogos | [E] | 2026-09-25 | `raw/sensortower_vgi_quickstats_2026-09-25.csv` | Só Steam. Séries históricas, demografia e sobreposição de público exigem plano Enterprise. A tabela de sobreposição exibida na conta gratuita é **ilustrativa** (links "undefined") e não deve ser usada. |
| Releases trimestrais da Nexon (texto integral do Business Wire republicado pela [FinancialContent](https://markets.financialcontent.com)) | Unidades, receita, pico de jogadores em todas as plataformas | [O] | 2026-09-25 | `external/official_milestones.csv` | Receita do ARC Raiders por trimestre só é divulgada para Q2/2026 e no acumulado. Conflito entre veículos resolvido com o release primário (15,5M ao fim de Q1; 16,3M ao fim de Q2). |
| [Streams Charts](https://streamscharts.com/news/arc-raiders-becomes-most-watched-game-2025) (notícias) | Audiência na Twitch na semana de lançamento | [O] | 2026-09-25 | `external/official_milestones.csv` | Só a semana de lançamento; séries mensais dependem de TwitchTracker/SullyGnome. |
| [SteamDB](https://steamdb.info/app/1808500/charts/) (exportado pelo usuário) | Jogadores simultâneos na Steam: diário desde 30/10/2025, a cada 10 min nas semanas recentes | [O] | 2026-09-25 | `external/steamdb_chart_1808500.csv` | Só Steam. Resolução mista; agregar por dia na limpeza. Separador `;`. |
| [TwitchTracker](https://twitchtracker.com/games) (prints do usuário, transcritos) | Audiência mensal na Twitch: média, pico, canais, horas assistidas. ARC Raiders, Escape from Tarkov (desde 2016), Hunt: Showdown (desde 2017), Battlefield 6, Marathon | [O] | 2026-09-25 | `external/twitchtracker_monthly.csv` (+ prints originais) → `interim/twitch_monthly.csv` | Só Twitch. **A tabela do site rotula cada mês com o mês anterior**: corrigido (+1 mês), com três evidências (datas de pico no resumo das páginas do BF6 e do Marathon; horas assistidas batem em ±1% em 88% das linhas com a correção contra 14% sem ela; o último mês fecha em 24/30 dias). Set/2026 parcial (até ~24/09). Transcrição validada: 292/292 linhas batem com a coluna "Gain". |
| Embark (publicação sobre o teste PvE) | Divisão dos jogadores por estilo de jogo; interesse em PvE | [O] | 2026-09-25 | `external/official_milestones.csv` | Dados da própria desenvolvedora, sem metodologia detalhada. |

## Perfil demográfico

Não há demografia pública do ARC Raiders. O perfil combina dados próprios do jogo com referências do gênero:

| Dimensão | Fonte | Etiqueta |
|---|---|---|
| Região | Idioma das 416,8 mil análises da Steam | [O] |
| Plataforma | Pico em todas as plataformas (Nexon, 960 mil) × pico na Steam (465 mil) no mesmo mês | [O] derivado |
| Estilo de jogo | Divulgação da Embark (37% cooperativos, 27% mistos, 34% PvP) | [O] |
| Engajamento | Horas jogadas pelos autores das análises | [O] |
| Idade e gênero | Quantic Foundry 2017 (gênero por tipo de jogo), ESA 2026 (EUA) | [G] |
| Mercado | Newzoo 2025 (jogadores por plataforma; perfil de quem paga) | [G] |

Arquivo: `external/genre_demographics.csv`. Os sites agregadores (SQ Magazine, inStreamly, Icon Era, ShaneTheGamer, Virtwave) foram avaliados em 2026-09-25: nenhum traz dados de jogos de tiro, e divergem entre si (ex.: Oriente Médio e África com 300 ou 600 milhões de jogadores). Citamos a fonte original que eles indicam, marcando quando o número só foi visto no agregador.

## Bloqueadas ou pendentes

| Fonte | Motivo | Alternativa |
|---|---|---|
| SteamDB, TwitchTracker, SullyGnome, Streams Charts (páginas de dados), raijin.gg, IR da Nexon | Bloqueiam acesso automatizado (Cloudflare/403) e a extensão do Chrome recusa a navegação ("domínio não permitido"), mesmo após liberação pelo usuário. Não contornamos. | Exportação manual pelo usuário, ou notícias e relatórios mensais publicados por essas fontes. |
| Gamalytic API | Exige chave paga. | — |
| SteamSpy | Dados do ARC Raiders desatualizados (0 análises, 0–20 mil donos). | Descartado para este jogo. |

## Descartadas (dados locais)

- `top games dataset.zip`: dados aparentemente sintéticos (ex.: Sekiro como "Sports", no Switch, em 2014).
- `Multimodal Player Engagement (MultiPENG).zip`: EEG/rastreamento ocular de pesquisa; sem relação com o ARC Raiders.
