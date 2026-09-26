"""Grava os rótulos da leitura manual da amostra de teste (seed=2026, só análises negativas).

Critério: 1 = a análise trata o tema como problema/queixa; 0 = menção sem queixa
(elogio, outro sentido da palavra, tema diferente). Para as análises sem tema, lista os
temas que a leitura identificou e o dicionário não pegou.
"""
import pandas as pd

s = pd.read_csv(r"C:\dev\arc-raiders-analysis\data\interim\validation_sample.csv")
wrong = {  # índices (ordem da amostra) julgados incorretos em cada tema
    "cheaters": {}, "rats": {}, "bugs": {7: "turco 'hata' = erro do jogador", 8: "'багоюзери' = abusadores de bug (exploit)", 13: "'lag switching' é técnica de trapaça"},
    "exploits": {15: "'angle exploiting' é tática de posicionamento"},
    "pve": {3: "queixa é de cheater em lobby PvE", 8: "diz que jogador PvE pode gostar", 12: "contra modo PvE", 19: "PvE chato, não pede PvE"},
    "content": {1: "deseja que o jogo morra", 12: "'nothing to do with'", 17: "sugestão sobre rotas repetitivas"},
    "balance": {},
    "matchmaking": {8: "lobby cheio de ratos/cheaters", 9: "lobby com bug", 10: "lobby com cheaters", 14: "narrativa, sem queixa", 19: "'volta ao lobby'"},
}
missed = {  # análises sem tema: temas que deveriam ter sido marcados
    4: "bugs", 5: "rats", 7: "bugs", 14: "rats", 20: "content", 22: "rats", 24: "pve", 26: "pve", 27: "rats",
    30: "bugs", 35: "content", 36: "rats", 37: "content", 39: "content", 43: "rats;content", 46: "content",
    47: "rats", 49: "pve", 51: "pve", 54: "content;matchmaking", 57: "bugs",
}
rows = []
for group, g in s.groupby("sample_group", sort=False):
    g = g.reset_index(drop=True)
    for i, r in g.iterrows():
        if group.startswith("flagged:"):
            topic = group.split(":")[1]
            rows.append({"review_id": r.review_id, "sample_group": group, "correct": int(i not in wrong[topic]),
                         "missed_topics": "", "note": wrong[topic].get(i, "")})
        else:
            rows.append({"review_id": r.review_id, "sample_group": group, "correct": "",
                         "missed_topics": missed.get(i, ""), "note": ""})
out = pd.DataFrame(rows)
out.to_csv(r"C:\dev\arc-raiders-analysis\data\external\complaint_validation_labels.csv", index=False, encoding="utf-8")
print(out.groupby("sample_group")["correct"].apply(lambda c: pd.to_numeric(c, errors="coerce").mean()).round(2))
print("sem tema com tema perdido:", (out.missed_topics != "").sum())
