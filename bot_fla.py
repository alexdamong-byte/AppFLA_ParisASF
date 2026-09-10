import requests
import json

def generer_api_classement():
    # On retire les chiffres de l'URL, le serveur les veut dans le "payload"
    url = "https://www.football-loisir-amateur.com/Home/GetClassement"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }

    # Voici la valise de données exigée par le serveur (tes identifiants)
    payload = {
        "championnatId": 1358,
        "saisonId": 15
    }

    print("Téléchargement des données brutes en cours...")
    
    # On ajoute json=payload pour l'envoyer correctement au serveur
    reponse = requests.post(url, json=payload, headers=headers)
    
    try:
        donnees = reponse.json()
        
        with open('classement.json', 'w', encoding='utf-8') as f:
            json.dump(donnees, f, ensure_ascii=False, indent=4)
            
        print(f"✅ Fichier JSON généré avec succès ! ({len(donnees)} équipes traitées)")
        
    except requests.exceptions.JSONDecodeError:
        print("❌ ÉCHEC : Le serveur n'a pas renvoyé de JSON valide.")
        print(f"Code HTTP reçu : {reponse.status_code}")
        print("Voici les 500 premiers caractères :")
        print(reponse.text[:500])

if __name__ == "__main__":
    generer_api_classement()
