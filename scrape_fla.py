"""
Scraper pour la nouvelle plateforme FLA (football-loisir-amateur.fr).
Remplace bot_fla.py + calendrier_fla.py, qui ciblaient l'ancien site
(football-loisir-amateur.com), désormais hors service pour cette saison.

Produit deux fichiers, au même format que les anciens (compatibles avec
l'app) mais enrichis : matches.json (calendrier Paris ASF, Coupe incluse)
et classement.json (classement complet du championnat).
"""
import requests, re, json
from bs4 import BeautifulSoup

BASE = "https://football-loisir-amateur.fr"
TEAM_ID = 265          # PARIS ASF — à changer si l'ID change d'une saison à l'autre
CHAMPIONSHIP_ID = 25   # 4ème division A — idem
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

MOIS = {"janv":1,"févr":2,"mars":3,"avr":4,"mai":5,"juin":6,"juil":7,"août":8,
        "sept":9,"oct":10,"nov":11,"déc":12}
JOURS = "lun|mar|mer|jeu|ven|sam|dim"
DATE_RE = re.compile(rf"({JOURS})\.\s*(\d{{1,2}})\s+({'|'.join(MOIS)})\.?\s+(\d{{4}})")
TIME_RE = re.compile(r"(\d{1,2})h(\d{2})")
SCORE_RE = re.compile(r"^(\d+)\s*–\s*(\d+)\s*([VDN])$")

def get_text_lines(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text("\n")
    return [l.strip() for l in text.split("\n") if l.strip()], soup

def parse_matches():
    lines, _ = get_text_lines(f"{BASE}/teams/{TEAM_ID}")
    try:
        start = lines.index("Toutes les rencontres de la saison") + 1
    except ValueError:
        raise RuntimeError("Section 'Toutes les rencontres de la saison' introuvable — le site a peut-être changé.")
    try:
        end = lines.index("Matchs à venir", start)
    except ValueError:
        end = len(lines)
    section = lines[start:end]

    matches, i = [], 0
    while i < len(section):
        line = section[i]
        if line.startswith("Coupe") or line.startswith("Championnat"):
            comp_type = "Coupe" if line.startswith("Coupe") else "Championnat"
            comp_name = re.sub(r"\s+(Domicile|Extérieur)$", "", line[len(comp_type):].strip(" —"))
            journee_m = re.search(r"Journée\s*(\d+)", comp_name)
            journee = int(journee_m.group(1)) if journee_m else None
            i += 1
            recoit = None; opponent = None
            while i < len(section) and not (section[i].startswith("Reçoit") or section[i].startswith("Se déplace chez")):
                i += 1
            if i < len(section):
                if section[i].startswith("Reçoit"):
                    recoit = True; opponent = section[i][len("Reçoit"):].strip()
                else:
                    recoit = False; opponent = section[i][len("Se déplace chez"):].strip()
                i += 1
            date_iso = None
            while i < len(section) and not DATE_RE.search(section[i]):
                i += 1
            if i < len(section):
                jr, d, mo, y = DATE_RE.search(section[i]).groups()
                i += 1
                hh = mm = None
                venue_parts = []
                while i < len(section) and not (SCORE_RE.match(section[i]) or section[i] == "À jouer"):
                    tm = TIME_RE.search(section[i])
                    if tm and hh is None:
                        hh, mm = tm.groups()
                    else:
                        v = section[i].lstrip("· ").strip()
                        if v: venue_parts.append(v)
                    i += 1
                venue = " ".join(venue_parts) if venue_parts else "Lieu à confirmer"
                if hh:
                    date_iso = f"{y}-{MOIS[mo]:02d}-{int(d):02d}T{int(hh):02d}:{mm}:00"
                score = None; statut = "upcoming"
                if i < len(section):
                    sm = SCORE_RE.match(section[i])
                    if sm:
                        own, opp = int(sm.group(1)), int(sm.group(2))
                        score = [own, opp] if recoit else [opp, own]
                        statut = "past"
                    i += 1
                matches.append({
                    "competition": comp_type, "competition_nom": comp_name, "journee": journee,
                    "domicile": "PARIS ASF" if recoit else opponent,
                    "exterieur": opponent if recoit else "PARIS ASF",
                    "date": date_iso, "venue": venue, "score": score, "statut": statut,
                })
        else:
            i += 1
    return matches

def parse_classement():
    _, soup = get_text_lines(f"{BASE}/championships/{CHAMPIONSHIP_ID}/rankings?season=2")
    table = soup.find("table")
    if not table:
        raise RuntimeError("Tableau de classement introuvable — le site a peut-être changé.")
    rows = []
    for tr in table.find_all("tr")[1:]:  # skip header
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cells) < 7: continue
        # cells: [Pos, Équipe, Pts, J, G, N, P, Diff]
        equipe = cells[1]
        pts, j, g, n, p = (int(x) if x.lstrip("-").isdigit() else 0 for x in cells[2:7])
        rows.append({"equipe": equipe, "points": pts, "joues": j, "gagnes": g, "nuls": n, "perdus": p})
    return rows

if __name__ == "__main__":
    matches = parse_matches()
    with open("matches.json", "w", encoding="utf-8") as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)
    print(f"✅ {len(matches)} matchs écrits dans matches.json")

    classement = parse_classement()
    with open("classement.json", "w", encoding="utf-8") as f:
        json.dump(classement, f, ensure_ascii=False, indent=2)
    print(f"✅ {len(classement)} équipes écrites dans classement.json")
