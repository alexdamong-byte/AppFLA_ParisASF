import requests
import json

def generer_api_calendrier():
    url = "https://www.football-loisir-amateur.com/Home/GetRencontreDuneTeam/"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }

    # On envoie l'identifiant de Paris ASF (6463)
    payload = {
        "idEquipe": 6463 
    }

    print("Téléchargement du calendrier brut en cours...")
    reponse = requests.post(url, json=payload, headers=headers)
    
    try:
        donnees = reponse.json()
        
        with open('calendrier.json', 'w', encoding='utf-8') as f:
            json.dump(donnees, f, ensure_ascii=False, indent=4)
            
        print(f"✅ Fichier calendrier JSON généré avec succès ! ({len(donnees)} matchs trouvés)")
        
    except requests.exceptions.JSONDecodeError:
        print("❌ ÉCHEC : Le serveur n'a pas renvoyé de JSON valide.")
        print(f"Code HTTP reçu : {reponse.status_code}")
        print("Vérifie le nom du paramètre dans l'onglet 'Payload' (ex: id, equipeId...). Voici les 500 premiers caractères :")
        print(reponse.text[:500])

if __name__ == "__main__":
    generer_api_calendrier()
