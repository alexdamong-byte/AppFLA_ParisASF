import requests
import json
import time

def generer_api_calendriers_complets():
    # 1. On charge la liste des équipes depuis le classement fraîchement généré
    try:
        with open('classement.json', 'r', encoding='utf-8') as f:
            classement = json.load(f)
    except FileNotFoundError:
        print("❌ Fichier classement.json introuvable. Lance bot_fla.py en premier.")
        return

    url = "https://www.football-loisir-amateur.com/Home/GetRencontreDuneTeam/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest"
    }

    # Ce dictionnaire stockera l'ID de l'équipe comme clé, et sa liste de matchs comme valeur
    tous_les_calendriers = {}

    print(f"Téléchargement des calendriers pour {len(classement)} équipes...")

    for equipe in classement:
        id_equipe = str(equipe.get("IdEquipe"))
        nom_equipe = equipe.get("Nom")
        
        payload = {"equipeId": int(id_equipe)}
        
        try:
            reponse = requests.post(url, json=payload, headers=headers)
            donnees = reponse.json()
            tous_les_calendriers[id_equipe] = donnees
            print(f"✅ Calendrier récupéré pour : {nom_equipe}")
        except Exception as e:
            print(f"❌ Erreur pour {nom_equipe} : {e}")
        
        # On fait une pause d'une seconde entre chaque requête pour ne pas saturer leur serveur
        time.sleep(1)
        
    # On écrase l'ancien fichier calendrier.json avec cette méga-base de données
    with open('calendrier.json', 'w', encoding='utf-8') as f:
        json.dump(tous_les_calendriers, f, ensure_ascii=False, indent=4)
        
    print("✅ Méga-fichier calendrier.json généré avec succès !")

if __name__ == "__main__":
    generer_api_calendriers_complets()
