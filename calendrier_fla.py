import requests
import json
import time

def generer_api_calendriers_complets():
    try:
        with open('classement.json', 'r', encoding='utf-8') as f:
            classement = json.load(f)
    except FileNotFoundError:
        print("❌ Fichier classement.json introuvable.")
        return

    url = "https://www.football-loisir-amateur.com/Home/GetRencontreDuneTeam/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest"
    }

    tous_les_calendriers = {}
    print(f"Téléchargement des calendriers pour {len(classement)} équipes...")

    for equipe in classement:
        id_equipe = str(equipe.get("IdEquipe"))
        nom_equipe = equipe.get("Nom")
        
        # Le nom de la clé attendue par la FLA est "idEquipe"
        payload = {"idEquipe": int(id_equipe)}
        
        try:
            reponse = requests.post(url, json=payload, headers=headers)
            tous_les_calendriers[id_equipe] = reponse.json()
            print(f"✅ Calendrier récupéré pour : {nom_equipe}")
        except Exception as e:
            print(f"❌ Erreur pour {nom_equipe} : {e}")
        
        time.sleep(1)
        
    with open('calendrier.json', 'w', encoding='utf-8') as f:
        json.dump(tous_les_calendriers, f, ensure_ascii=False, indent=4)
        
    print("✅ Méga-fichier calendrier.json généré avec succès !")

if __name__ == "__main__":
    generer_api_calendriers_complets()
