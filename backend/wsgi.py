"""Entry point for `flask` CLI commands and `flask run` (FLASK_APP=wsgi.py).

FLASK_APP in .env tells the `flask` command to load this file and use the `app`
object below. "WSGI" is the standard way Python web servers talk to web apps;
production servers (e.g. gunicorn/waitress) also start the app from here.
"""
from app import create_app

app = create_app()   # build the app with the default DevelopmentConfig

# Only runs if you start this file directly with `python wsgi.py` (not with `flask run`).
if __name__ == "__main__":
    app.run(port=5000)
