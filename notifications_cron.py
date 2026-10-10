"""
Génère les notifications quotidiennes pour l'app Paris ASF :
- relance tous les 3 jours si un joueur n'a pas répondu (jusqu'à 20 jours avant le match)
- mise en "absent" automatique à J-4 si toujours sans réponse
- notification "vote disponible" 2h après le match, une fois la feuille + les stats validées
Lancé quotidiennement par GitHub Actions avec la clé service_role (contourne les RLS).
"""
import os, re, json, requests
from datetime import datetime, timedelta, timezone

URL = (os.environ.get("SUPABASE_URL") or "").strip().strip('"').rstrip("/")
KEY = (os.environ.get("SUPABASE_SERVICE_KEY") or "").strip().strip('"')
HEADERS = {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}

def parse_ts(valeur):
    """Lit un horodatage Supabase. Python 3.10 n'accepte que 3 ou 6 chiffres de fraction de seconde,
    alors que Supabase en renvoie parfois 5 (ex. 19.80524) : on normalise à 6."""
    v = valeur.replace("Z", "+00:00")
    v = re.sub(r"\.(\d+)", lambda m: "." + m.group(1)[:6].ljust(6, "0"), v, count=1)
    return datetime.fromisoformat(v)

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

def envoyer_push(joueur_id, message, match_id=None):
    """Envoie un push à tous les appareils abonnés du joueur. Silencieux si non configuré."""
    priv = (os.environ.get("VAPID_PRIVATE_KEY") or "").strip()
    sujet = (os.environ.get("VAPID_SUBJECT") or "").strip()
    if not priv:
        return
    if not sujet.lower().startswith("mailto:"):
        print("⚠️  VAPID_SUBJECT absent ou invalide (doit être mailto:ton@email) — push ignoré.")
        return
    from pywebpush import webpush, WebPushException
    subs = get("push_subscriptions", f"?joueur_id=eq.{joueur_id}&select=id,endpoint,p256dh,auth_key")
    for s in subs:
        try:
            webpush(
                subscription_info={"endpoint": s["endpoint"], "keys": {"p256dh": s["p256dh"], "auth": s["auth_key"]}},
                data=json.dumps({"title": "Paris ASF", "body": message, "url": f"./?match={match_id}" if match_id else "./"}),
                vapid_private_key=priv, vapid_claims={"sub": sujet}, ttl=86400,
            )
        except WebPushException as e:
            code = getattr(e.response, "status_code", None)
            if code in (404, 410):  # abonnement expiré ou désinstallé : on le supprime
                requests.delete(f"{URL}/rest/v1/push_subscriptions?id=eq.{s['id']}", headers=HEADERS, timeout=20)
            else:
                print(f"⚠️  Push échoué ({code}) : {str(e)[:200]}")
        except Exception as e:
            print(f"⚠️  Push échoué : {str(e)[:200]}")

def notifier(joueur_id, match_id, type_, message):
    existe = get("notifications", f"?joueur_id=eq.{joueur_id}&match_id=eq.{match_id}&type=eq.{type_}&select=id&limit=1")
    if existe:
        return False
    post("notifications", {"joueur_id": joueur_id, "match_id": match_id, "type": type_, "message": message, "lu": False})
    envoyer_push(joueur_id, message, match_id)
    return True

def test_push():
    ids = {s["joueur_id"] for s in get("push_subscriptions", "?select=joueur_id")}
    print(f"Test push : {len(ids)} joueur(s) abonné(s)")
    for jid in ids:
        envoyer_push(jid, "Notification de test ✅ — tout fonctionne !")

def deja_relance_recemment(joueur_id, match_id):
    rows = get("notifications", f"?joueur_id=eq.{joueur_id}&match_id=eq.{match_id}&type=eq.relance_presence&select=created_at&order=created_at.desc&limit=1")
    if not rows:
        return False
    dernier = parse_ts(rows[0]["created_at"])
    return (datetime.now(timezone.utc) - dernier) < timedelta(days=3)

def gerer_presence_a_venir():
    if not URL or not KEY:
        print("⚠️  Secrets Supabase absents — notifications ignorées."); return
    now = datetime.now(timezone.utc)
    iso_z = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")  # pas de "+" : il serait lu comme un espace dans l'URL
    matchs = get("matchs", f"?statut=eq.a_venir&date_heure=gte.{iso_z(now)}&date_heure=lte.{iso_z(now+timedelta(days=20))}&select=id,date_heure")
    joueurs = get("joueurs", "?actif=eq.true&select=id,nom")
    for m in matchs:
        date_match = parse_ts(m["date_heure"])
        jours_restants = (date_match - now).days
        presences = {p["joueur_id"]: p["statut"] for p in get("presences", f"?match_id=eq.{m['id']}&select=joueur_id,statut")}
        for j in joueurs:
            statut = presences.get(j["id"])
            if statut in ("oui", "non"):
                continue  # a déjà répondu
            if jours_restants <= 4:
                post("presences?on_conflict=match_id,joueur_id", {"match_id": m["id"], "joueur_id": j["id"], "statut": "non"}, prefer="resolution=merge-duplicates")
                notifier(j["id"], m["id"], "absence_auto",
                         f"Sans réponse de ta part, tu as été mis automatiquement absent pour le match du {date_match.strftime('%d/%m à %Hh%M')}.")
            elif not deja_relance_recemment(j["id"], m["id"]):
                notifier(j["id"], m["id"], "relance_presence",
                         f"Dispo pour le match du {date_match.strftime('%d/%m à %Hh%M')} ? Réponds dans l'app.")

def gerer_vote_disponible():
    now = datetime.now(timezone.utc)
    matchs = get("matchs", "?statut=eq.termine&feuille_validee=eq.true&stats_remplies=eq.true&select=id,date_heure")
    for m in matchs:
        date_match = parse_ts(m["date_heure"])
        if (now - date_match) < timedelta(hours=2):
            continue
        presents = get("presences", f"?match_id=eq.{m['id']}&a_reellement_joue=eq.true&select=joueur_id")
        for p in presents:
            notifier(p["joueur_id"], m["id"], "vote_disponible",
                     "Le vote pour l'homme du match est ouvert — à toi de voter !")

if __name__ == "__main__":
    if (os.environ.get("PUSH_TEST") or "").lower() == "true":
        test_push()
    else:
        gerer_presence_a_venir()
        gerer_vote_disponible()
    print("✅ Notifications traitées")
