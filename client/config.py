import os

API_BASE_URL = "http://127.0.0.1:8000"

DOCUMENTS_DIR = os.path.join(os.path.expanduser('~'), 'Documents', 'NeutronGames')
LIBRARY_FILE = 'local_library.json'
CONFIG_FILE = 'local_config.json'

if not os.path.exists(DOCUMENTS_DIR):
    os.makedirs(DOCUMENTS_DIR)
    