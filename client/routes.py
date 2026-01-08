import os
import shutil
import requests
from flask import Flask, render_template, request, redirect, url_for, flash
import config
import storage

app = Flask(__name__)
app.secret_key = "super_secret_key_change_me"


@app.route('/')
def list_games():
    filter_platform_id = request.args.get('platform_id')
    search_query = request.args.get('q')

    games = []
    platforms = []
    
    try:
        platforms_resp = requests.get(f"{config.API_BASE_URL}/platforms/")
        if platforms_resp.status_code == 200:
            platforms = platforms_resp.json()

        api_params = {}
        
        if filter_platform_id:
            api_params['platform_id'] = filter_platform_id
            
        if search_query:
            api_params['search'] = search_query

        games_resp = requests.get(f"{config.API_BASE_URL}/games/", params=api_params)
        
        if games_resp.status_code == 200:
            games = games_resp.json()
            
    except requests.exceptions.ConnectionError:
        flash("API offline.", "error")

    local_library = storage.load_local_library()
    for game in games:
        game_id_str = str(game['id'])
        if game_id_str in local_library and os.path.exists(local_library[game_id_str]):
            game['is_installed'] = True
            game['local_path'] = local_library[game_id_str]
        else:
            game['is_installed'] = False

    return render_template(
        'games_list.html', 
        games=games, 
        platforms=platforms, 
        active_filter=filter_platform_id,
        active_search=search_query,
        api_base_url=config.API_BASE_URL
    )

@app.route('/platforms/new', methods=['GET'])
def new_platform_form():
    return render_template('create_platform.html')

@app.route('/platforms/create', methods=['POST'])
def create_platform_logic():
    name = request.form.get('name')
    icon_file = request.files.get('icon')

    payload = {'name': name}
    files = {}
    if icon_file and icon_file.filename != '':
        files['icon'] = (icon_file.filename, icon_file.read(), icon_file.content_type)

    try:
        response = requests.post(f"{config.API_BASE_URL}/platforms/", data=payload, files=files)
        if response.status_code == 200:
            flash(f"Plateforme '{name}' créée !", "success")
            return redirect(url_for('new_platform_form'))
        else:
            flash(f"Erreur: {response.json().get('detail')}", "error")
    except requests.exceptions.ConnectionError:
        flash("Erreur connexion API.", "error")
    
    return redirect(url_for('new_platform_form'))

@app.route('/games/new', methods=['GET'])
def new_game_form():
    platforms = []
    try:
        response = requests.get(f"{config.API_BASE_URL}/platforms/")
        if response.status_code == 200:
            platforms = response.json()
    except:
        flash("Erreur chargement plateformes.", "error")
    return render_template('create_game.html', platforms=platforms)

@app.route('/games/create', methods=['POST'])
def create_game_logic():
    title = request.form.get('title')
    platform_id = request.form.get('platform_id')
    rom_file = request.files.get('rom')
    cover_file = request.files.get('cover')

    if not rom_file or rom_file.filename == '':
        flash("Fichier ROM obligatoire.", "error")
        return redirect(url_for('new_game_form'))

    payload = {'title': title, 'platform_id': platform_id}
    files = {'rom': (rom_file.filename, rom_file.read(), rom_file.content_type)}
    
    if cover_file and cover_file.filename != '':
        files['cover'] = (cover_file.filename, cover_file.read(), cover_file.content_type)

    try:
        response = requests.post(f"{config.API_BASE_URL}/games/", data=payload, files=files)
        if response.status_code == 200:
            flash("Jeu ajouté avec succès !", "success")
        else:
            flash("Erreur lors de l'ajout.", "error")
    except:
        flash("Erreur connexion API.", "error")

    return redirect(url_for('new_game_form'))

@app.route('/games/install/<int:game_id>', methods=['POST'])
def install_game(game_id):
    try:
        all_games = requests.get(f"{config.API_BASE_URL}/games/").json()
        game_info = next((g for g in all_games if g['id'] == game_id), None)

        if not game_info:
            flash("Jeu introuvable.", "error")
            return redirect(url_for('list_games'))

        rom_url = f"{config.API_BASE_URL}/media/{game_info['rom_path']}"
        _, ext = os.path.splitext(game_info['rom_path'])
        safe_title = storage.sanitize_filename(game_info['title'])
        local_filename = f"{safe_title}{ext}"
        local_path = os.path.join(config.DOCUMENTS_DIR, local_filename)

        with requests.get(rom_url, stream=True) as r:
            r.raise_for_status()
            with open(local_path, 'wb') as f:
                shutil.copyfileobj(r.raw, f)

        library = storage.load_local_library()
        library[str(game_id)] = local_path
        storage.save_local_library(library)

        flash(f"{game_info['title']} installé !", "success")
    except Exception as e:
        flash(f"Erreur installation: {e}", "error")

    return redirect(url_for('list_games'))

@app.route('/settings', methods=['GET'])
def settings_page():
    platforms = []
    try:
        response = requests.get(f"{config.API_BASE_URL}/platforms/")
        if response.status_code == 200:
            platforms = response.json()
    except:
        flash("API Offline.", "error")

    local_config = storage.load_local_config()

    is_fullscreen = local_config.get('fullscreen', False)

    for p in platforms:
        p_id_str = str(p['id'])
        p['emulator_path'] = local_config.get(p_id_str, "")

    return render_template('settings.html', platforms=platforms, fullscreen=is_fullscreen)

@app.route('/settings/save', methods=['POST'])
def save_settings():
    local_config = storage.load_local_config()

    local_config['fullscreen'] = True if request.form.get('fullscreen') else False

    for key, value in request.form.items():
        if key.startswith("emulator_path_"):
            platform_id = key.replace("emulator_path_", "")
            local_config[platform_id] = value.strip()
    
    storage.save_local_config(local_config)
    flash("Configuration sauvegardée.", "success")
    return redirect(url_for('settings_page'))
