import requests
import json

def generer_api_classement():
    url = "https://www.football-loisir-amateur.com/Home/GetClassement/135815"
    
    # On met un User-Agent ultra complet de vrai navigateur pour contourner les blocages
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }

    print("Téléchargement des données brutes en cours...")
    
    # On utilise POST (très souvent obligatoire sur les API ASP.NET pour le JSON)
    reponse = requests.post(url, headers=headers)
    
    try:
        # On tente de décoder le JSON
        donnees = reponse.json()
        
        with open('classement.json', 'w', encoding='utf-8') as f:
            json.dump(donnees, f, ensure_ascii=False, indent=4)
            
        print(f"✅ Fichier JSON généré avec succès ! ({len(donnees)} équipes traitées)")
        
    except requests.exceptions.JSONDecodeError:
        # Si ça plante, on ne crash plus, on affiche ce que le serveur a osé nous répondre
        print("❌ ÉCHEC : Le serveur n'a pas renvoyé de JSON valide.")
        print(f"Code HTTP reçu : {reponse.status_code}")
        print("Voici les 500 premiers caractères de ce qu'il a renvoyé :")
        print(reponse.text[:500])

if __name__ == "__main__":
    generer_api_classement()
