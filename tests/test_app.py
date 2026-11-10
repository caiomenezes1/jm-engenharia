
from unittest.mock import MagicMock

import app
import app.routes as routes


def test_create_app_loads_environment(monkeypatch):
    # Simula o carregamento das variáveis de ambiente
    load_dotenv_mock = MagicMock()
    monkeypatch.setattr(app, "load_dotenv", load_dotenv_mock)

    # Define uma chave secreta para o teste
    monkeypatch.setenv("SECRET_KEY", "chave-teste")

    # Simula a conexão com o banco de dados
    engine_mock = MagicMock()
    monkeypatch.setattr("app.database.engine", engine_mock)

    flask_app = app.create_app()

    # Verifica o carregamento do .env
    load_dotenv_mock.assert_called_once()

    # Verifica a configuração da chave secreta
    assert flask_app.config["SECRET_KEY"] == "chave-teste"


def test_create_app_checks_database_connection(monkeypatch):
    engine_mock = MagicMock()
    monkeypatch.setattr("app.database.engine", engine_mock)

    app.create_app()

    # Verifica se a conexão foi aberta
    engine_mock.connect.assert_called_once()

    # Verifica se a consulta SELECT 1 foi executada
    connection_mock = engine_mock.connect.return_value.__enter__.return_value

    connection_mock.execute.assert_called_once()

    statement = connection_mock.execute.call_args[0][0]
    assert str(statement) == "SELECT 1"


def test_create_app_registers_blueprint(monkeypatch):
    engine_mock = MagicMock()
    monkeypatch.setattr("app.database.engine", engine_mock)

    flask_app = app.create_app()

    # Verifica se o Blueprint principal foi registrado
    assert "main" in flask_app.blueprints

    assert flask_app.blueprints["main"] is routes.bp
