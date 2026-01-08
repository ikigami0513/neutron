import json
import os
import re
from config import LIBRARY_FILE, CONFIG_FILE

def load_json(filename):
    if not os.path.exists(filename):
        return {}
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Erreur chargement {filename}: {e}")
        return {}

def save_json(filename, data):
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Erreur sauvegarde {filename}: {e}")

def load_local_library():
    return load_json(LIBRARY_FILE)

def save_local_library(data):
    save_json(LIBRARY_FILE, data)

def load_local_config():
    return load_json(CONFIG_FILE)

def save_local_config(data):
    save_json(CONFIG_FILE, data)

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)
