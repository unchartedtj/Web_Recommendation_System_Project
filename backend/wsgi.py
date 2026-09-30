"""Entry point for `flask` CLI commands and `flask run` (FLASK_APP=wsgi.py)."""
from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(port=5000)
