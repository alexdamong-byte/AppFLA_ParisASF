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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest"
    }

    tous_les_calendriers = {}

    print(f"Téléchargement des calendriers pour {len(classement)} équipes...")

    for equipe in classement:
        id_equipe = str(equipe.get("IdEquipe"))
        nom_equipe = equipe.get("Nom")
        
        # Le paramètre est peut-être différent (ex: IdEquipe au lieu de equipeId)
        payload = {"equipeId": int(id_equipe)}
        
        reponse = requests.post(url, json=payload, headers=headers)
        
        try:
            donnees = reponse.json()
            tous_les_calendriers[id_equipe] = donnees
            print(f"✅ OK : {nom_equipe}")
        except requests.exceptions.JSONDecodeError:
            print(f"❌ ERREUR pour {nom_equipe}")
            print(f"Code HTTP : {reponse.status_code}")
            print("Message du serveur :")
            print(reponse.text[:500])
            print("\n⚠️ ARRÊT DU SCRIPT : Regarde le message ci-dessus pour comprendre ce que veut le serveur.")
            break # On arrête tout à la première erreur
            
        time.sleep(2) # On attend 2 secondes pour ne pas se faire bloquer
        
    if tous_les_calendriers:
        with open('calendrier.json', 'w', encoding='utf-8') as f:
            json.dump(tous_les_calendriers, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    generer_api_calendriers_complets()
