import requests
from bs4 import BeautifulSoup

def recuperer_classement():
    # L'URL magique que tu as dénichée
    url = "https://www.football-loisir-amateur.com/Home/GetClassement/135815"
    
    # On se déguise en navigateur classique pour que le serveur nous réponde gentiment
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36"
    }

    print("Récupération du classement de Paris ASF en cours...\n")
    
    # On interroge directement l'URL
    reponse = requests.get(url, headers=headers)
    
    # On fouille dans le code HTML reçu
    soup = BeautifulSoup(reponse.text, 'html.parser')
    
    # On isole toutes les lignes du tableau
    lignes = soup.find_all('tr')
    trouve = False
    
    for ligne in lignes:
        if 'Paris ASF' in ligne.text:
            colonnes = ligne.find_all('td')
            if len(colonnes) >= 3:
                position = colonnes[0].text.strip()
                
                # La colonne 2 (index 2) correspond généralement aux points sur leur site, 
                # mais si ça affiche le nombre de matchs joués, change le [2] par [3] ou [4] !
                points = colonnes[2].text.strip() 
                
                print(f"🏆 Paris ASF est actuellement à la place n°{position} avec {points} points !")
                trouve = True
                break
                
    if not trouve:
         print("Je n'ai pas trouvé l'équipe. Soit le nom est écrit un peu différemment sur le site, soit le tableau est vide en début de saison.")

if __name__ == "__main__":
    recuperer_classement()
