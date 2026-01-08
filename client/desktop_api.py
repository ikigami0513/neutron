import webview
import subprocess
import os
import storage

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

    def launch_game(self, game_id, platform_id):
        print(f"Lancement Jeu ID: {game_id} sur Plateforme ID: {platform_id}")

        library = storage.load_local_library()
        config = storage.load_local_config()

        game_id_str = str(game_id)
        platform_id_str = str(platform_id)

        rom_path = library.get(game_id_str)
        emu_path = config.get(platform_id_str)

        if not rom_path or not os.path.exists(rom_path):
            return {"success": False, "message": "ROM introuvable localement. Veuillez télécharger le jeu."}
        
        if not emu_path or not os.path.exists(emu_path):
            return {"success": False, "message": "Émulateur non configuré. Allez dans les paramètres."}

        try:
            subprocess.Popen([emu_path, rom_path])
            return {"success": True, "message": "Jeu lancé !"}
        except Exception as e:
            print(f"Erreur lancement: {e}")
            return {"success": False, "message": str(e)}
        
    def toggle_fullscreen(self):
        if len(webview.windows) > 0:
            window = webview.windows[0]
            window.toggle_fullscreen()
            