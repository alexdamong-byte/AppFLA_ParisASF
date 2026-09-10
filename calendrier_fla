import requests
from bs4 import BeautifulSoup
import json

def generer_api_calendrier_club():
    url = "https://www.football-loisir-amateur.com/Home/Club?Id=6463"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    print("Téléchargement de la page du club...")
    reponse = requests.get(url, headers=headers)
    soup = BeautifulSoup(reponse.text, 'html.parser')
    
    # La page Club contient plusieurs tableaux (Classement, Résultats...).
    # On cible spécifiquement toutes les lignes.
    lignes = soup.find_all('tr')
    calendrier_club = []
    
    for ligne in lignes:
        colonnes = ligne.find_all('td')
        
        # S'il y a le lieu en première colonne, on a besoin d'au moins 5 colonnes
        # Cela permet aussi d'éviter de lire les lignes du tableau de classement par erreur
        if len(colonnes) >= 5:
            try:
                # Si le lieu est dans la 1ère colonne (index 0), tout le reste se décale de +1
                match_data = {
                    "lieu": colonnes[0].text.strip(),
                    "date": colonnes[1].text.strip(),
                    "equipe_domicile": colonnes[2].text.strip(),
                    "score_ou_statut": colonnes[3].text.strip(),
                    "equipe_exterieur": colonnes[4].text.strip()
                }
                
                # On filtre les lignes vides ou les en-têtes qui se seraient glissés
                if match_data["equipe_domicile"] != "" and "Equipe" not in match_data["equipe_domicile"]:
                    calendrier_club.append(match_data)
                    
            except Exception as e:
                pass
                
    with open('calendrier.json', 'w', encoding='utf-8') as f:
        json.dump(calendrier_club, f, ensure_ascii=False, indent=4)
        
    print(f"✅ Fichier calendrier.json généré avec succès ! ({len(calendrier_club)} matchs trouvés)")

if __name__ == "__main__":
    generer_api_calendrier_club()
