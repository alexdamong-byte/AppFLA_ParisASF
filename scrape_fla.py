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

def paris_offset(dt):
    """Retourne '+02:00' (été) ou '+01:00' (hiver) pour une date Europe/Paris,
    selon la règle UE (dernier dimanche de mars à dernier dimanche d'octobre)."""
    import datetime as _dt
    def dernier_dimanche(annee, mois):
        d = _dt.date(annee, mois, 1)
        d = (d.replace(month=mois % 12 + 1, day=1) if mois < 12 else _dt.date(annee + 1, 1, 1)) - _dt.timedelta(days=1)
        while d.weekday() != 6: d -= _dt.timedelta(days=1)
        return d
    debut_ete = dernier_dimanche(dt.year, 3)
    fin_ete = dernier_dimanche(dt.year, 10)
    return "+02:00" if debut_ete <= dt.date() < fin_ete else "+01:00"
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

def source_id(m):
    # Même formule que côté front (index.html) pour pouvoir relier les deux.
    return f"{m['competition']}|{m['domicile']}|{m['exterieur']}|{m['date']}"

def sync_to_supabase(matches):
    import os
    url = (os.environ.get("SUPABASE_URL") or "").strip().strip('"').strip("'").rstrip("/")
    key = (os.environ.get("SUPABASE_SERVICE_KEY") or "").strip().strip('"').strip("'")
    if not url or not key:
        print("⚠️  SUPABASE_URL / SUPABASE_SERVICE_KEY absents — synchro Supabase ignorée.")
        return
    if not url.startswith("http"):
        print(f"❌ SUPABASE_URL invalide (doit commencer par https://) — valeur actuelle : {len(url)} caractère(s), ne commence pas par http.")
        return
    headers = {
        "apikey": key, "Authorization": f"Bearer {key}",
        "Content-Type": "application/json", "Prefer": "resolution=merge-duplicates",
    }
    # Saison active (optionnel, laissé vide si introuvable)
    saison_id = None
    try:
        r = requests.get(f"{url}/rest/v1/saisons?active=eq.true&select=id", headers=headers, timeout=15)
        rows = r.json()
        if rows: saison_id = rows[0]["id"]
    except Exception as e:
        print("⚠️  Récupération de la saison active impossible :", e)

    payload = []
    for m in matches:
        if not m["date"]:
            continue
        payload.append({
            "source_id": source_id(m),
            "saison_id": saison_id,
            "competition": "coupe" if m["competition"] == "Coupe" else "championnat",
            "date_heure": m["date"] + paris_offset(__import__("datetime").datetime.fromisoformat(m["date"])),
            "equipe_domicile": m["domicile"],
            "equipe_exterieur": m["exterieur"],
            "adresse_stade": m["venue"],
            "score_domicile": m["score"][0] if m["score"] else None,
            "score_exterieur": m["score"][1] if m["score"] else None,
            "statut": "termine" if m["statut"] == "past" else "a_venir",
        })
    if not payload:
        print("⚠️  Aucun match avec date valide à synchroniser."); return
    r = requests.post(f"{url}/rest/v1/matchs?on_conflict=source_id", headers=headers, json=payload, timeout=30)
    if r.status_code in (200, 201):
        print(f"✅ {len(payload)} matchs synchronisés dans Supabase")
    else:
        print(f"❌ Erreur synchro Supabase ({r.status_code}) : {r.text[:500]}")

def _ics_escape(s):
    return (s or "").replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

def _ics_fold(line):
    """Replie les lignes de plus de 75 octets (RFC 5545)."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    parts, cur = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        if len(cur) + len(b) > (75 if not parts else 74):
            parts.append(cur); cur = b
        else:
            cur += b
    parts.append(cur)
    return "\r\n ".join(p.decode("utf-8") for p in parts)

def generate_ics(matches, path="calendrier.ics"):
    import hashlib
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    lines = [
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Paris ASF//Calendrier FLA//FR",
        "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:Paris ASF",
        "X-WR-TIMEZONE:Europe/Paris", "REFRESH-INTERVAL;VALUE=DURATION:PT6H", "X-PUBLISHED-TTL:PT6H",
    ]
    n = 0
    for m in matches:
        if not m.get("date"):
            continue
        local = datetime.fromisoformat(m["date"])
        off_h = int(paris_offset(local)[1:3])
        debut = (local - timedelta(hours=off_h)).strftime("%Y%m%dT%H%M%SZ")
        fin = (local - timedelta(hours=off_h) + timedelta(hours=1)).strftime("%Y%m%dT%H%M%SZ")
        titre = f"{m['domicile']} - {m['exterieur']}"
        if m.get("score"):
            titre += f" ({m['score'][0]}-{m['score'][1]})"
        if m["competition"] == "Coupe":
            titre = "🏆 " + titre
        uid = hashlib.sha1(source_id(m).encode("utf-8")).hexdigest() + "@paris-asf"
        lines += [
            "BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{now}", f"DTSTART:{debut}", f"DTEND:{fin}",
            f"SUMMARY:{_ics_escape(titre)}", f"LOCATION:{_ics_escape(m.get('venue'))}",
            f"DESCRIPTION:{_ics_escape(m.get('competition_nom') or m['competition'])}",
            "END:VEVENT",
        ]
        n += 1
    lines.append("END:VCALENDAR")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("\r\n".join(_ics_fold(l) for l in lines) + "\r\n")
    print(f"✅ {n} événements écrits dans {path}")

if __name__ == "__main__":
    matches = parse_matches()
    with open("matches.json", "w", encoding="utf-8") as f:
        json.dump(matches, f, ensure_ascii=False, indent=2)
    print(f"✅ {len(matches)} matchs écrits dans matches.json")
    generate_ics(matches)
    sync_to_supabase(matches)

    classement = parse_classement()
    with open("classement.json", "w", encoding="utf-8") as f:
        json.dump(classement, f, ensure_ascii=False, indent=2)
    print(f"✅ {len(classement)} équipes écrites dans classement.json")
