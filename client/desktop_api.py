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

    def _monitor_game_process(self, process, game_id, save_path):
        print(f"Jeu lancé (PID: {process.pid}). Surveillance active...")
        
        process.wait()
        
        print("Jeu fermé. Lancement de la synchronisation...")
        time.sleep(1)
        
        self._sync_up(game_id, save_path)
        
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

            return {"success": True, "message": "Jeu lancé ! Synchro active."}

        except Exception as e:
            return {"success": False, "message": str(e)}
        
    def toggle_fullscreen(self):
        if len(webview.windows) > 0:
            window = webview.windows[0]
            window.toggle_fullscreen()

    def _get_save_path(self, rom_path):
        """Helper: Get .sav path from .nes/.sfc path"""
        base_name, _ = os.path.splitext(rom_path)
        return f"{base_name}.sav"

    def _sync_down(self, game_id, save_path):
        """
        Télécharge la dernière sauvegarde si elle est plus récente que la locale.
        """
        print(f"[Sync] Checking Cloud for Game {game_id}...")
        
        try:
            # 1. Demander les infos de la dernière save au serveur
            # Note: On utilise le nouveau endpoint /latest/info
            info_resp = requests.get(f"{config.API_BASE_URL}/games/{game_id}/save/latest/info")
            
            if info_resp.status_code == 200:
                server_data = info_resp.json()
                
                # Parsing de la date serveur (ISO format string -> float timestamp)
                # Attention : le serveur renvoie du temps UTC
                from datetime import datetime
                server_date_str = server_data['created_at']
                # Python < 3.7 : strptime. Python 3.7+ : fromisoformat
                server_dt = datetime.fromisoformat(server_date_str)
                server_timestamp = server_dt.timestamp()

                # Vérifier la date locale
                should_download = False
                if not os.path.exists(save_path):
                    print("[Sync] Pas de sauvegarde locale. Téléchargement...")
                    should_download = True
                else:
                    local_timestamp = os.path.getmtime(save_path)
                    # Si le serveur est plus récent (avec une marge de sécurité de quelques secondes)
                    if server_timestamp > local_timestamp:
                        print(f"[Sync] Serveur plus récent ({server_date_str}). Mise à jour...")
                        should_download = True
                    else:
                        print("[Sync] La sauvegarde locale est à jour.")

                if should_download:
                    # Téléchargement du fichier binaire
                    file_resp = requests.get(f"{config.API_BASE_URL}/games/{game_id}/save/latest")
                    if file_resp.status_code == 200:
                        with open(save_path, 'wb') as f:
                            f.write(file_resp.content)
                        print("[Sync] Succès : Fichier .sav mis à jour !")
                        
                        # IMPORTANT : Mettre à jour la date de modification locale pour éviter
                        # de re-uploader immédiatement après le jeu.
                        os.utime(save_path, (time.time(), time.time()))
                        return True
            else:
                print("[Sync] Aucune sauvegarde sur le cloud.")

        except Exception as e:
            print(f"[Sync Error Down] {e}")
        return False

    def _sync_up(self, game_id, save_path):
        """
        Crée une NOUVELLE version sur le serveur.
        """
        print(f"[Sync] Préparation de l'upload vers le cloud...")
        if not os.path.exists(save_path):
            print("[Sync] Fichier introuvable, abandon.")
            return

        try:
            # On envoie le fichier. Le serveur créera une nouvelle ligne dans la table 'saves'
            files = {'file': open(save_path, 'rb')}
            resp = requests.post(f"{config.API_BASE_URL}/games/{game_id}/save", files=files)
            
            if resp.status_code == 200:
                data = resp.json()
                print(f"[Sync] Upload réussi ! Nouvelle version ID: {data.get('save_id')}")
            else:
                print(f"[Sync] Erreur upload: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"[Sync Error Up] {e}")
            