import requests
from bs4 import BeautifulSoup
import json

def generer_api_classement():
    url = "https://www.football-loisir-amateur.com/Home/GetClassement/135815"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    print("Téléchargement des données de la FLA...")
    reponse = requests.get(url, headers=headers)
    soup = BeautifulSoup(reponse.text, 'html.parser')
    
    lignes = soup.find_all('tr')
    classement_complet = []
    
    for ligne in lignes:
        colonnes = ligne.find_all('td')
        
        # D'après ta capture, il y a au moins 12 colonnes de données
        if len(colonnes) >= 12:
            try:
                # On extrait proprement chaque donnée
                equipe_data = {
                    "rank": colonnes[0].text.strip(),
                    "team": colonnes[1].text.strip(),
                    "points": colonnes[2].text.strip(),
                    "joues": colonnes[3].text.strip(),
                    "gagnes": colonnes[4].text.strip(),
                    "nuls": colonnes[5].text.strip(),
                    "perdus": colonnes[6].text.strip(),
                    "buts_pour": colonnes[7].text.strip(),
                    "buts_contre": colonnes[8].text.strip(),
                    "diff": colonnes[9].text.strip(),
                    "bonus": colonnes[10].text.strip(),
                    "forfait": colonnes[11].text.strip()
                }
                classement_complet.append(equipe_data)
            except Exception as e:
                print(f"Erreur sur une ligne : {e}")
                continue
                
    # On sauvegarde le tout dans un fichier JSON
    with open('classement.json', 'w', encoding='utf-8') as f:
        json.dump(classement_complet, f, ensure_ascii=False, indent=4)
        
    print(f"✅ Fichier JSON généré avec succès ! ({len(classement_complet)} équipes traitées)")

if __name__ == "__main__":
    generer_api_classement()
