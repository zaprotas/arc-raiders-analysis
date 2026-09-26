"""Dicionário multilíngue de temas de reclamação.

Cobre os 12 idiomas com mais análises (97% do total): inglês, russo, alemão, português,
francês, espanhol, turco, polonês, chinês, italiano, coreano e ucraniano. Os termos
incluem gírias da comunidade ("rat", "крыса", "老六") e foram ajustados numa primeira
amostra de 220 análises lidas uma a uma; a precisão final é medida numa segunda amostra,
independente (ver notebooks/02_reclamacoes.ipynb). Busca sem diferenciar maiúsculas.
Alternativas separadas por " | "; frases com espaços são preservadas por to_regex().

Cuidados de desenho:
- russo "чит" também começa "читать" (ler): só formas de "читер/читы/читак".
- "abuse" sozinho é ambíguo (toxicidade): só "abuse" ligado a bug/glitch/exploit.
- francês "exploit" também significa "façanha": aceito, efeito pequeno (3,9% das análises).
"""

TOPICS = {
    "cheaters": {
        "label": "Cheaters e hackers",
        "pattern": r"""
            \bcheat(?:er|ers|ing|s|ed)?\b | \bhack(?:er|ers|ing|s|ed)?\b | aim-?bot | wall-?hack | speed-?hack | spin-?bot
            | trapac | \bxit(?:er|ers|ado|ados|ando) | tramp(?:os|oso)s? | tricheu | \btriche\b | hileci | \bhile\b | oszust | cziter | betrüger
            | imbroglion
            | читер | читак | \bчиты\b | \bчитов\b | читами | хакер | аимбот | \bвх\b | софтер | софтом
            | 外挂 | 开挂 | 挂哥 | 挂狗 | 作弊
            | 핵 | 치터
        """,
    },
    "rats": {
        "label": "Ratos, campers e traição",
        "pattern": r"""
            \brat(?:s|ting|ted|ty)?\b | \bcamp(?:er|ers|ing|ed)\b | camp kill | third[\s-]?party | \bkos\b | kill[\s-]on[\s-]sight
            | shoot[\s-]on[\s-]sight | betray | backstab | back-stab | (?:shot|shoot|shooting|killed) (?:you |me |us )?in the back
            | behind (?:their |your |our )?backs?
            | \bratos\b | \bratear | campa(?:ndo|r|m)\b | \bcamperos?\b | traíra | traição | trai(?:u|ram|dor) | nas costas
            | \bratas?\b | campe(?:ar|ros) | por la espalda
            | \bratte | hinterhalt | verrat | in den rücken
            | alle spalle | \bratti\b | camper
            | \bcampeur | trahi
            | \bfare\b | kampç
            | szczur | kamper
            | крыс | кемпер | кемпят | засад | в спину | предал | предатель
            | 老鼠 | 老六 | 背刺
            | 쥐 | 캠핑 | 뒤통수
        """,
    },
    "bugs": {
        "label": "Bugs, travamentos e servidores",
        "pattern": r"""
            \bbug(?:s|gy|ged)?\b | \bcrash(?:es|ing|ed)?\b | \bglitch(?:es|y|ed)?\b | \blag(?:s|gy|ging)?\b | desync
            | stutter | disconnect(?:s|ed|ing) | \bfreez(?:e|es|ing)\b | fps drop | server(?:s)? (?:issue|problem|down|error)
            | choppy | frame ?rate | performance (?:issue|problem) | audio cuts | error code | can.?t (?:start|launch) | won.?t (?:start|launch)
            | \bbugad | travand | \btrava\b | desconect | queda de fps | não abre | nao abre
            | se cierra | se crashea | se bloquea | no inicia | pantalla negra
            | \bcrasha | si blocca
            | abstürz | absturz | ruckel
            | plantage
            | \bhata\b | donma | kasma | çök
            | zacina | wywala
            | \bбаг | вылет | \bлаг | фриз | краш | дисконект | тормоз | оптимизац | сбой соединения | не запускается
            | 闪退 | 卡顿 | 掉线 | 崩溃 | bug
            | 버그 | 튕 | 렉 | 최적화
        """,
    },
    "exploits": {
        "label": "Exploits e duplicação de itens",
        "pattern": r"""
            \bexploit(?:s|er|ers|ing|ed)?\b | \bdup(?:e|es|ed|ing|er|ers)\b | duplicat(?:ion|ing)\b | abus(?:e|ing) (?:of )?(?:the )?(?:bug|glitch|exploit)
            | glitch(?:ing)? (?:into|through|under)
            | \bdupar | duplicação | duplicando | abus(?:o|ando) de bug
            | duplicación | duplicando | bug de duplica
            | эксплойт | эксплоит | абуз | дюп
            | 卡bug | 复制
            | 복사 | 버그 악용
        """,
    },
    "pve": {
        "label": "Falta de PvE / excesso de PvP",
        "pattern": r"""
            \bpve\b | pvp[\s-]?free | no pvp | without pvp | less pvp | too much pvp | remove pvp | pvp ruin
            | only pvp | co-?op only | pve only | pve mode | pve server | peaceful mode
            | sem pvp | modo pve | menos pvp
            | sin pvp | modo pve
            | ohne pvp | pve-modus
            | пве | без пвп | режим pve
        """,
    },
    "content": {
        "label": "Falta de conteúdo e jogo abandonado",
        "pattern": r"""
            nothing to do | no content | lack of content | content drought | no new content | not enough content
            | no updates | dead game | game is dead | gets? (?:boring|repetitive|stale) | repetitive | no end ?game
            | abandon(?:ed)? (?:the |this )?game | game (?:is |was |feels |seems )?abandoned | dropped (?:the )?game | late game content
            | sem conteúdo | falta de conteúdo | repetitivo | \benjoa | jogo abandonado | abandonaram | jogo morto | sem atualiza
            | sin contenido | falta de contenido | aburrid | dejaron morir | abandonado
            | ripetitiv | noioso
            | kein content | eintönig | langweilig | repetitiv
            | pas de contenu | répétitif
            | нечего делать | нет контента | мало контента | однообраз | надоед | мертв | заброш
            | 没内容 | 重复 | 无聊
            | 콘텐츠 부족 | 할게 없
        """,
    },
    "balance": {
        "label": "Balanceamento (nerfs e buffs)",
        "pattern": r"""
            \bnerf | \bbuff(?:s|ed|ing)?\b | unbalanc | imbalanc | overpowered | balancing | balance (?:changes?|patch|team|update)
            | (?:weapon|gun) balanc | ballance
            | desbalance | desequilibr | déséquilibr
            | нерф | дисбаланс | имба
            | 削弱 | 不平衡
            | 너프
        """,
    },
    "matchmaking": {
        "label": "Pareamento (matchmaking)",
        "pattern": r"""
            matchmaking | \bsbmm\b | \bmmr\b | skill[\s-]based | lobbies | lobby
            | pareamento | emparejamiento
            | матчмейкинг | подбор игроков | подбор
            | 匹配
            | 매칭
        """,
    },
}

# Termos que colidem com palavras comuns de um idioma específico: não contam nesse idioma.
LANGUAGE_EXCLUDE = {
    "rats": {"spanish": r"\bratos\b", "latam": r"\bratos\b"},  # "un rato" = um tempo
}


def to_regex(pattern: str) -> str:
    """Junta as alternativas do dicionário preservando espaços internos.

    O dicionário é escrito em várias linhas para leitura; o modo VERBOSE do Python
    apagaria os espaços de frases como "nothing to do" (bug encontrado na validação).
    """
    parts = [p.strip() for p in pattern.replace("\n", " ").split(" | ")]
    return "|".join(p for p in parts if p)


REQUESTED =["cheaters", "rats", "bugs", "exploits", "pve"]  # temas pedidos no escopo
CONTEXT = ["content", "balance", "matchmaking"]  # temas adicionados para contexto
