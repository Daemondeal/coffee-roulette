from socket import gethostname 
import os
from flask import Flask
from coffee_roulette.db import init_db
from coffee_roulette.routes import bp
from dotenv import load_dotenv

def create_app():
    app = Flask(__name__, template_folder="../templates")
    app.register_blueprint(bp)
    app.secret_key = os.getenv("SECRET_KEY")
    return app

def main(run_app):
    init_db()
    load_dotenv()
    app = create_app()
    if run_app:
        app.run()


if __name__ == "__main__":
    run_app = 'liveconsole' not in gethostname()
    main(run_app)

