"""
yt-dlp Ultimate Web Downloader — Flask Entry Point (Linux)
"""

from flask import Flask, render_template
from routes.download_routes import download_bp
from routes.tools_routes    import tools_bp
from routes.format_routes   import format_bp
from routes.control_routes  import control_bp
import webbrowser
import threading
import os

app = Flask(__name__, template_folder="templates", static_folder="static")

app.register_blueprint(download_bp)
app.register_blueprint(tools_bp)
app.register_blueprint(format_bp)
app.register_blueprint(control_bp)

@app.route("/")
def home():
    return render_template("index.html")

def _open_browser():
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == "__main__":
    threading.Timer(1.5, _open_browser).start()
    app.run(debug=False, host="127.0.0.1", port=5000, use_reloader=False)
