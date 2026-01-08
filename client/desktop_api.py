import threading
import requests
import webview
import subprocess
import os
import storage
import config
import time

class JSApi:
    def pick_file(self):
        if len(webview.windows) > 0:
            window = webview.windows[0]
            print("Ouverture du file dialog...")
            
            file_types = ('Executables (*.exe;*.app;*.sh)', 'All files (*.*)')
            result = window.create_file_dialog(webview.OPEN_DIALOG, file_types=file_types)
            
            if result and len(result) > 0:
                clean_path = result[0].replace('\\', '/')
                return clean_path
        return ""

    def toggle_fullscreen(self):
        if len(webview.windows) > 0:
            window = webview.windows[0]
            window.toggle_fullscreen()

    def _get_auth_headers(self):
        try:
            auth_data = storage.load_auth_token()
            token = auth_data.get('access_token')
            if token:
                return {"Authorization": f"Bearer {token}"}
        except Exception as e:
            print(f"[Auth Warning] {e}")
        return {}

    def _get_save_path(self, rom_path):
        base_name, _ = os.path.splitext(rom_path)
        save_path = f"{base_name}.sav"
        
        print(f"[Debug Path] ROM: {rom_path}")
        print(f"[Debug Path] SAVE ATTENDUE: {save_path}")
        return save_path

    def _monitor_game_process(self, process, game_id, save_path):
        print(f"Jeu lancé (PID: {process.pid}). Surveillance active...")
        
        start_time = time.time()
        
        process.wait()

        end_time = time.time()
        
        print("Jeu fermé. Lancement des tâches de fond...")
        time.sleep(1)
        
        session_duration = int(end_time - start_time)
        print(f"[Session] Durée de la partie : {session_duration} secondes")

        try:
            self._sync_up(game_id, save_path)
        except Exception as e:
            print(f"[Erreur Sync] {e}")

        try:
            self._update_playtime(game_id, session_duration)
        except Exception as e:
            print(f"[Erreur Playtime] {e}")
        
        print("Cycle de jeu terminé.")

    def launch_game(self, game_id, platform_id):
        print(f"Préparation lancement Jeu ID: {game_id}")

        library = storage.load_local_library()
        local_config = storage.load_local_config()
        
        game_id_str = str(game_id)
        platform_id_str = str(platform_id)

        rom_path = library.get(game_id_str)
        emu_path = local_config.get(platform_id_str)

        if not rom_path or not os.path.exists(rom_path):
            return {"success": False, "message": "ROM manquante."}
        if not emu_path or not os.path.exists(emu_path):
            return {"success": False, "message": "Émulateur non configuré."}

        save_path = self._get_save_path(rom_path)

        self._sync_down(game_id, save_path)

        try:
            process = subprocess.Popen([emu_path, rom_path])
            
            monitor_thread = threading.Thread(
                target=self._monitor_game_process, 
                args=(process, game_id, save_path)
            )
            monitor_thread.daemon = True
            monitor_thread.start()

            return {"success": True, "message": "Jeu lancé ! Bon jeu."}

        except Exception as e:
            return {"success": False, "message": str(e)}

    def _update_playtime(self, game_id, duration_seconds):
        if duration_seconds < 5:
            print("[Playtime] Session trop courte (<5s), ignorée.")
            return

        print(f"[Playtime] Envoi de {duration_seconds}s au serveur...")
        url = f"{config.API_BASE_URL}/games/{game_id}/playtime"
        headers = self._get_auth_headers()
        
        if not headers:
            print("[Playtime] Échec : Pas de token d'authentification.")
            return

        resp = requests.post(url, json={"seconds": duration_seconds}, headers=headers)
        if resp.status_code == 200:
            print(f"[Playtime] Succès ! Nouveau total reçu du serveur.")
        else:
            print(f"[Playtime] Erreur serveur : {resp.status_code}")

    def _sync_down(self, game_id, save_path):
        print(f"[Sync] Checking Cloud for Game {game_id}...")
        try:
            headers = self._get_auth_headers()
            info_resp = requests.get(f"{config.API_BASE_URL}/games/{game_id}/save/latest/info", headers=headers)
            
            if info_resp.status_code == 200:
                server_data = info_resp.json()
                from datetime import datetime
                server_dt = datetime.fromisoformat(server_data['created_at'])
                server_timestamp = server_dt.timestamp()

                should_download = False
                if not os.path.exists(save_path):
                    print("[Sync] Pas de sauvegarde locale. Téléchargement...")
                    should_download = True
                else:
                    local_timestamp = os.path.getmtime(save_path)
                    if server_timestamp > local_timestamp:
                        print(f"[Sync] Serveur plus récent. Mise à jour...")
                        should_download = True
                    else:
                        print("[Sync] La sauvegarde locale est à jour.")

                if should_download:
                    file_resp = requests.get(f"{config.API_BASE_URL}/games/{game_id}/save/latest", headers=headers)
                    if file_resp.status_code == 200:
                        with open(save_path, 'wb') as f:
                            f.write(file_resp.content)
                        print("[Sync] Succès : Fichier .sav mis à jour !")
                        os.utime(save_path, (time.time(), time.time()))
                        return True
            else:
                print("[Sync] Aucune sauvegarde sur le cloud ou User inconnu.")

        except Exception as e:
            print(f"[Sync Error Down] {e}")
        return False

    def _sync_up(self, game_id, save_path):
        print(f"[Sync] Préparation de l'upload vers le cloud...")
        if not os.path.exists(save_path):
            print(f"[Sync] Fichier introuvable à : {save_path}")
            print("[Sync] Abandon (Le jeu n'a pas sauvegardé ou le chemin est incorrect).")
            return

        try:
            files = {'file': open(save_path, 'rb')}
            headers = self._get_auth_headers()
            resp = requests.post(f"{config.API_BASE_URL}/games/{game_id}/save", files=files, headers=headers)
            
            if resp.status_code == 200:
                data = resp.json()
                print(f"[Sync] Upload réussi ! Save ID: {data.get('save_id')}")
            else:
                print(f"[Sync] Erreur upload: {resp.status_code}")
        except Exception as e:
            print(f"[Sync Error Up] {e}")
