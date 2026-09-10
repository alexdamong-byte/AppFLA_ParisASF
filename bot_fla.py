import requests
import json

def generer_api_classement():
    url = "https://www.football-loisir-amateur.com/Home/GetClassement/135815"
    
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest" # Force la réponse en JSON
    }

    print("Téléchargement des données brutes...")
    reponse = requests.get(url, headers=headers)
    donnees = reponse.json()
    
    with open('classement.json', 'w', encoding='utf-8') as f:
        json.dump(donnees, f, ensure_ascii=False, indent=4)
        
    print(f"✅ Fichier JSON généré avec succès ! ({len(donnees)} équipes traitées)")

if __name__ == "__main__":
    generer_api_classement()
