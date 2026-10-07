"""
Génère les notifications quotidiennes pour l'app Paris ASF :
- relance tous les 3 jours si un joueur n'a pas répondu (jusqu'à 20 jours avant le match)
- mise en "absent" automatique à J-4 si toujours sans réponse
- notification "vote disponible" 2h après le match, une fois la feuille + les stats validées
Lancé quotidiennement par GitHub Actions avec la clé service_role (contourne les RLS).
"""
import os, requests
from datetime import datetime, timedelta, timezone

URL = (os.environ.get("SUPABASE_URL") or "").strip().strip('"').rstrip("/")
KEY = (os.environ.get("SUPABASE_SERVICE_KEY") or "").strip().strip('"')
HEADERS = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

def get(path, params=""):
    r = requests.get(f"{URL}/rest/v1/{path}{params}", headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.json()

def post(path, payload, prefer="return=minimal"):
    h = dict(HEADERS); h["Prefer"] = prefer
    r = requests.post(f"{URL}/rest/v1/{path}", headers=h, json=payload, timeout=20)
    if r.status_code >= 300:
        print(f"⚠️  Erreur POST {path} : {r.status_code} {r.text[:300]}")

def patch(path, payload):
    h = dict(HEADERS); h["Prefer"] = "return=minimal"
    r = requests.patch(f"{URL}/rest/v1/{path}", headers=h, json=payload, timeout=20)
    if r.status_code >= 300:
        print(f"⚠️  Erreur PATCH {path} : {r.status_code} {r.text[:300]}")

def notifier(joueur_id, match_id, type_, message):
    existe = get("notifications", f"?joueur_id=eq.{joueur_id}&match_id=eq.{match_id}&type=eq.{type_}&select=id&limit=1")
    if existe:
        return False
    post("notifications", {"joueur_id": joueur_id, "match_id": match_id, "type": type_, "message": message, "lu": False})
    return True

def deja_relance_recemment(joueur_id, match_id):
    rows = get("notifications", f"?joueur_id=eq.{joueur_id}&match_id=eq.{match_id}&type=eq.relance_presence&select=created_at&order=created_at.desc&limit=1")
    if not rows:
        return False
    dernier = datetime.fromisoformat(rows[0]["created_at"].replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - dernier) < timedelta(days=3)

def gerer_presence_a_venir():
    if not URL or not KEY:
        print("⚠️  Secrets Supabase absents — notifications ignorées."); return
    now = datetime.now(timezone.utc)
    matchs = get("matchs", f"?statut=eq.a_venir&date_heure=gte.{now.isoformat()}&date_heure=lte.{(now+timedelta(days=20)).isoformat()}&select=id,date_heure")
    joueurs = get("joueurs", "?actif=eq.true&select=id,nom")
    for m in matchs:
        date_match = datetime.fromisoformat(m["date_heure"].replace("Z", "+00:00"))
        jours_restants = (date_match - now).days
        presences = {p["joueur_id"]: p["statut"] for p in get("presences", f"?match_id=eq.{m['id']}&select=joueur_id,statut")}
        for j in joueurs:
            statut = presences.get(j["id"])
            if statut in ("oui", "non"):
                continue  # a déjà répondu
            if jours_restants <= 4:
                post("presences", {"match_id": m["id"], "joueur_id": j["id"], "statut": "non"}, prefer="resolution=merge-duplicates")
                notifier(j["id"], m["id"], "absence_auto",
                         f"Sans réponse de ta part, tu as été mis automatiquement absent pour le match du {date_match.strftime('%d/%m à %Hh%M')}.")
            elif not deja_relance_recemment(j["id"], m["id"]):
                notifier(j["id"], m["id"], "relance_presence",
                         f"Dispo pour le match du {date_match.strftime('%d/%m à %Hh%M')} ? Réponds dans l'app.")

def gerer_vote_disponible():
    now = datetime.now(timezone.utc)
    matchs = get("matchs", "?statut=eq.termine&feuille_validee=eq.true&stats_remplies=eq.true&select=id,date_heure")
    for m in matchs:
        date_match = datetime.fromisoformat(m["date_heure"].replace("Z", "+00:00"))
        if (now - date_match) < timedelta(hours=2):
            continue
        presents = get("presences", f"?match_id=eq.{m['id']}&a_reellement_joue=eq.true&select=joueur_id")
        for p in presents:
            notifier(p["joueur_id"], m["id"], "vote_disponible",
                     "Le vote pour l'homme du match est ouvert — à toi de voter !")

if __name__ == "__main__":
    gerer_presence_a_venir()
    gerer_vote_disponible()
    print("✅ Notifications traitées")
