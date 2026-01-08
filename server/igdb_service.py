import os
import requests
import time

CLIENT_ID = os.getenv("IGDB_CLIENT_ID")
CLIENT_SECRET = os.getenv("IGDB_CLIENT_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    print("⚠️  ATTENTION : Les clés IGDB ne sont pas configurées dans le fichier .env")

class IGDBService:
    def __init__(self):
        self.access_token = None
        self.token_expiry = 0

    def _authenticate(self):
        if not CLIENT_ID or not CLIENT_SECRET:
            return

        if self.access_token and time.time() < self.token_expiry:
            return

        print("[IGDB] Authenticating...")
        url = "https://id.twitch.tv/oauth2/token"
        params = {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "client_credentials"
        }
        
        try:
            response = requests.post(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            self.access_token = data["access_token"]
            self.token_expiry = time.time() + data["expires_in"] - 60
            print("[IGDB] Authentication successful.")
        except Exception as e:
            print(f"[IGDB] Auth failed: {e}")
            self.access_token = None

    def search_game(self, query):
        if not CLIENT_ID or not CLIENT_SECRET:
            print("[IGDB] Skipping search (Missing API Keys)")
            return None

        self._authenticate()
        if not self.access_token:
            return None

        print(f"[IGDB] Searching for: {query}")
        url = "https://api.igdb.com/v4/games"
        
        body = f'fields name, cover.url; search "{query}"; limit 1;'
        
        headers = {
            "Client-ID": CLIENT_ID,
            "Authorization": f"Bearer {self.access_token}"
        }

        try:
            response = requests.post(url, data=body, headers=headers)
            response.raise_for_status()
            results = response.json()

            if results and len(results) > 0:
                game = results[0]
                if "cover" in game and "url" in game["cover"]:
                    raw_url = game["cover"]["url"]
                    
                    if raw_url.startswith("//"):
                        raw_url = "https:" + raw_url
                    
                    hd_url = raw_url.replace("t_thumb", "t_cover_big")
                    
                    print(f"[IGDB] Found cover: {hd_url}")
                    return hd_url
            
            print("[IGDB] No results found.")
            return None

        except Exception as e:
            print(f"[IGDB] Search failed: {e}")
            return None

igdb = IGDBService()
