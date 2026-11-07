
import os

from flask import Flask
from dotenv import load_dotenv


def create_app():
    load_dotenv()

    app = Flask(__name__)

    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

    from app.database import engine
    from sqlalchemy import text

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    from app import routes

    app.register_blueprint(routes.bp)

    return app
