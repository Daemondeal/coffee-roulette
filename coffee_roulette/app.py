import os
from pathlib import Path
from flask import Flask
from coffee_roulette.db import init_db
from coffee_roulette.routes import bp
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")  # Load environment variables early

def create_app():
    template_path = Path(__file__).parent.parent / "templates"

    app = Flask(__name__, template_folder=template_path)
    app.register_blueprint(bp)
    app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key")  # fallback for dev
    return app

# Initialize DB separately (so WSGI can call it without running app)
init_db()

def main():
    app = create_app()
    app.run(debug=True)

