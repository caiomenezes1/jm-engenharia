from flask import Flask


def create_app():
    app = Flask(__name__)

    from app.database import engine
    from sqlalchemy import text

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))

    from app import routes

    app.register_blueprint(routes.bp)

    return app