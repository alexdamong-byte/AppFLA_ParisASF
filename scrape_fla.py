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
    lines, soup = get_text_lines(f"{BASE}/teams/{TEAM_ID}")
    text = re.sub(r"\s+", " ", soup.get_text(" ")).strip()
    try:
        start = text.index("Toutes les rencontres de la saison")
        end = text.index("Matchs à venir", start)
    except ValueError:
        raise RuntimeError("Sections introuvables — le site a peut-être changé.")
    section = text[start:end]

    mois_alt = "|".join(MOIS)
    pat = re.compile(
        r"(Coupe|Championnat)\s+(.*?)\s+(?:Domicile|Extérieur)\s+"
        r"(Reçoit|Se déplace chez)\s+(.*?)\s+"
        rf"(?:{JOURS})\.\s*(\d{{1,2}})\s+({mois_alt})\.?\s+(\d{{4}})[\s·]+"
        r"(\d{1,2})h(\d{2})[\s·]+"
        r"(.*?)\s+"
        r"(?:(\d+)\s*–\s*(\d+)\s*[VDN]|À jouer)"
    )
    matches = []
    for m in pat.finditer(section):
        comp_type, comp_name, sens, opponent, d, mo, y, hh, mm, venue, own, opp = m.groups()
        venue = re.sub(r"\s*\(ouvre l'itinéraire.*?\)\s*$", "", venue).strip()
        recoit = (sens == "Reçoit")
        date_iso = f"{y}-{MOIS[mo]:02d}-{int(d):02d}T{int(hh):02d}:{mm}:00"
        if own is not None:
            own, opp = int(own), int(opp)
            score = [own, opp] if recoit else [opp, own]
            statut = "past"
        else:
            score, statut = None, "upcoming"
        journee_m = re.search(r"Journée\s*(\d+)", comp_name)
        matches.append({
            "competition": comp_type, "competition_nom": comp_name.strip(" —"),
            "journee": int(journee_m.group(1)) if journee_m else None,
            "domicile": "PARIS ASF" if recoit else opponent.strip(),
            "exterieur": opponent.strip() if recoit else "PARIS ASF",
            "date": date_iso, "venue": venue or "Lieu à confirmer", "score": score, "statut": statut,
        })
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
