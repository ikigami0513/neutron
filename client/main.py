import threading
import webview
from routes import app
import storage
from desktop_api import JSApi

def start_server():
    app.run(host='127.0.0.1', port=5000, threaded=True, use_reloader=False)

if __name__ == '__main__':
    t = threading.Thread(target=start_server)
    t.daemon = True
    t.start()

    js_api = JSApi()

    local_config = storage.load_local_config()
    start_fullscreen = local_config.get('fullscreen', False)

    main_window = webview.create_window(
        title='Neutron Game Manager',
        url='http://127.0.0.1:5000',
        width=1200,
        height=800,
        resizable=True,
        js_api=js_api,
        fullscreen=start_fullscreen
    )

    webview.start(debug=False)
