
from types import SimpleNamespace
from unittest.mock import MagicMock
from datetime import date
from io import BytesIO
from docx import Document

import pytest
from flask import Flask

import app.routes as routes


def criar_cliente(monkeypatch):
    session = MagicMock()
    session.__enter__.return_value = session
    session.__exit__.return_value = False

    monkeypatch.setattr(
        routes,
        "SessionLocal",
        lambda: session
    )

    flask_app = Flask(__name__)
    flask_app.config["SECRET_KEY"] = "chave-teste"
    flask_app.register_blueprint(routes.bp)

    return flask_app.test_client(), session


def resultado_consulta(dados):
    resultado = MagicMock()
    resultado.all.return_value = dados
    return resultado


def test_index_lista_diarios(monkeypatch):
    client, session = criar_cliente(monkeypatch)

    monkeypatch.setattr(
        routes,
        "render_template",
        lambda template, **context: template
    )

    session.scalars.return_value = resultado_consulta([])

    response = client.get("/")

    assert response.status_code == 200
    assert response.data == b"index.html"
    session.scalars.assert_called_once()


def test_novo_diario_abre_formulario(monkeypatch):
    client, session = criar_cliente(monkeypatch)

    monkeypatch.setattr(
        routes,
        "render_template",
        lambda template, **context: template
    )

    session.scalars.side_effect = [
        resultado_consulta([]),
        resultado_consulta([]),
    ]

    response = client.get("/diarios/novo")

    assert response.status_code == 200
    assert response.data == b"novo_diario.html"
    assert session.scalars.call_count == 2


def test_novo_diario_rejeita_dados_invalidos(monkeypatch):
    client, session = criar_cliente(monkeypatch)

    monkeypatch.setattr(
        routes,
        "render_template",
        lambda template, **context: str(context["erros"])
    )

    session.scalars.side_effect = [
        resultado_consulta([]),
        resultado_consulta([]),
    ]

    response = client.post(
        "/diarios/novo",
        data={
            "identificacao_obra": "",
            "data_diario": "data-invalida",
        },
    )

    assert response.status_code == 200
    assert "Informe a identificação da obra.".encode() in response.data
    assert "Informe uma data válida.".encode() in response.data
    session.commit.assert_not_called()


def test_novo_diario_cadastra_com_sucesso(monkeypatch):
    client, session = criar_cliente(monkeypatch)

    funcao = SimpleNamespace(
        id=1,
        nome_funcao="Eletricista"
    )

    atividade = SimpleNamespace(
        id=10,
        ativo=True
    )

    grupo = SimpleNamespace(
        atividades=[atividade]
    )

    session.scalars.side_effect = [
        resultado_consulta([funcao]),
        resultado_consulta([grupo]),
    ]

    response = client.post(
        "/diarios/novo",
        data={
            "identificacao_obra": "Obra de teste",
            "data_diario": "2026-11-10",
            "observacoes_gerais": "Observação de teste",
            "quantidade_1": "2",
            "atividade_ids": ["10"],
        },
    )

    assert response.status_code == 302
    assert response.location.endswith("/")
    assert session.add.call_count == 3
    session.flush.assert_called_once()
    session.commit.assert_called_once()


def test_excluir_diario_inexistente(monkeypatch):
    client, session = criar_cliente(monkeypatch)
    session.get.return_value = None

    response = client.post("/diarios/999/excluir")

    assert response.status_code == 302
    assert response.location.endswith("/")
    session.commit.assert_not_called()
    session.delete.assert_not_called()


def test_excluir_diario_com_sucesso(monkeypatch):
    client, session = criar_cliente(monkeypatch)
    diario = MagicMock()
    session.get.return_value = diario

    response = client.post("/diarios/1/excluir")

    assert response.status_code == 302
    assert response.location.endswith("/")
    assert session.execute.call_count == 2
    session.delete.assert_called_once_with(diario)
    session.commit.assert_called_once()


def test_detalhes_diario_inexistente(monkeypatch):
    client, session = criar_cliente(monkeypatch)
    session.scalar.return_value = None

    response = client.get("/diarios/999")

    assert response.status_code == 302
    assert response.location.endswith("/")


def test_imprimir_diario_inexistente(monkeypatch):
    client, session = criar_cliente(monkeypatch)
    session.scalar.return_value = None

    response = client.get("/diarios/999/imprimir")

    assert response.status_code == 302
    assert response.location.endswith("/")



def configurar_dados_formulario(session, funcoes=None, grupos=None):
    atividade = SimpleNamespace(id=10, ativo=True)

    if grupos is None:
        grupos = [SimpleNamespace(atividades=[atividade])]

    if funcoes is None:
        funcoes = [
            SimpleNamespace(id=1, nome_funcao="Eletricista")
        ]

    session.scalars.side_effect = [
        resultado_consulta(funcoes),
        resultado_consulta(grupos),
    ]

    return atividade


def preparar_resposta_erros(monkeypatch):
    monkeypatch.setattr(
        routes,
        "render_template",
        lambda template, **context: str(context["erros"])
    )


def test_novo_diario_rejeita_identificacao_muito_longa(monkeypatch):
    client, session = criar_cliente(monkeypatch)
    configurar_dados_formulario(session)
    preparar_resposta_erros(monkeypatch)

    response = client.post(
        "/diarios/novo",
        data={
            "identificacao_obra": "A" * 151,
            "data_diario": "2026-11-10",
        },
    )

    assert response.status_code == 200
    assert "A identificação da obra deve ter até 150 caracteres.".encode() in response.data
    session.commit.assert_not_called()


def test_novo_diario_ignora_quantidade_vazia(monkeypatch):
    client, session = criar_cliente(monkeypatch)

    funcoes = [
        SimpleNamespace(id=1, nome_funcao="Eletricista"),
        SimpleNamespace(id=2, nome_funcao="Encanador"),
    ]

    configurar_dados_formulario(session, funcoes=funcoes)

    response = client.post(
        "/diarios/novo",
        data={
            "identificacao_obra": "Obra de teste",
            "data_diario": "2026-11-10",
            "quantidade_1": "",
            "quantidade_2": "2",
            "atividade_ids": ["10"],
        },
    )

    assert response.status_code == 302
    assert session.commit.call_count == 1
    assert session.add.call_count == 3


def test_novo_diario_rejeita_quantidade_nao_numerica(monkeypatch):
    client, session = criar_cliente(monkeypatch)
    configurar_dados_formulario(session)
    preparar_resposta_erros(monkeypatch)

    response = client.post(
        "/diarios/novo",
        data={
            "identificacao_obra": "Obra de teste",
            "data_diario": "2026-11-10",
            "quantidade_1": "abc",
            "atividade_ids": ["10"],
        },
    )

    assert response.status_code == 200
    assert "Quantidade inválida para Eletricista.".encode() in response.data
    session.commit.assert_not_called()


def test_novo_diario_rejeita_quantidade_negativa(monkeypatch):
    client, session = criar_cliente(monkeypatch)
    configurar_dados_formulario(session)
    preparar_resposta_erros(monkeypatch)

    response = client.post(
        "/diarios/novo",
        data={
            "identificacao_obra": "Obra de teste",
            "data_diario": "2026-11-10",
            "quantidade_1": "-2",
            "atividade_ids": ["10"],
        },
    )

    assert response.status_code == 200
    assert "A quantidade de Eletricista não pode ser negativa.".encode() in response.data
    session.commit.assert_not_called()


def test_novo_diario_rejeita_id_de_atividade_invalido(monkeypatch):
    client, session = criar_cliente(monkeypatch)
    configurar_dados_formulario(session)
    preparar_resposta_erros(monkeypatch)

    response = client.post(
        "/diarios/novo",
        data={
            "identificacao_obra": "Obra de teste",
            "data_diario": "2026-11-10",
            "quantidade_1": "2",
            "atividade_ids": ["abc"],
        },
    )

    assert response.status_code == 200
    assert "Seleção de atividades inválida.".encode() in response.data
    session.commit.assert_not_called()


def test_novo_diario_rejeita_atividade_indisponivel(monkeypatch):
    client, session = criar_cliente(monkeypatch)
    configurar_dados_formulario(session)
    preparar_resposta_erros(monkeypatch)

    response = client.post(
        "/diarios/novo",
        data={
            "identificacao_obra": "Obra de teste",
            "data_diario": "2026-11-10",
            "quantidade_1": "2",
            "atividade_ids": ["999"],
        },
    )

    assert response.status_code == 200
    assert "Uma ou mais atividades selecionadas são inválidas.".encode() in response.data
    session.commit.assert_not_called()


def test_novo_diario_falha_ao_salvar(monkeypatch):
    client, session = criar_cliente(monkeypatch)
    configurar_dados_formulario(session)
    preparar_resposta_erros(monkeypatch)

    session.commit.side_effect = Exception("Erro de teste")

    response = client.post(
        "/diarios/novo",
        data={
            "identificacao_obra": "Obra de teste",
            "data_diario": "2026-11-10",
            "quantidade_1": "2",
            "atividade_ids": ["10"],
        },
    )

    assert response.status_code == 200
    assert "Não foi possível salvar o diário.".encode() in response.data
    session.rollback.assert_called_once()


def test_excluir_diario_falha(monkeypatch):
    client, session = criar_cliente(monkeypatch)

    session.get.return_value = MagicMock()
    session.commit.side_effect = Exception("Erro de teste")

    response = client.post("/diarios/1/excluir")

    assert response.status_code == 302
    assert response.location.endswith("/")
    session.rollback.assert_called_once()


def test_detalhes_diario_com_sucesso(monkeypatch):
    client, session = criar_cliente(monkeypatch)

    diario = MagicMock()
    session.scalar.return_value = diario

    monkeypatch.setattr(
        routes,
        "render_template",
        lambda template, **context: template
    )

    response = client.get("/diarios/1")

    assert response.status_code == 200
    assert response.data == b"detalhes_diario.html"
    session.scalar.assert_called_once()


def test_imprimir_diario_com_sucesso(monkeypatch):
    client, session = criar_cliente(monkeypatch)

    profissional = SimpleNamespace(
        funcao=SimpleNamespace(nome_funcao="Eletricista"),
        quantidade=3,
    )

    item_atividade = SimpleNamespace(
        atividade=SimpleNamespace(
            grupo=SimpleNamespace(nome_grupo="Instalações"),
            descricao_atividade="Instalação de luminárias",
        )
    )

    diario = SimpleNamespace(
        id=1,
        identificacao_obra="Obra de teste",
        data_diario=date(2026, 11, 10),
        profissionais=[profissional],
        atividades=[item_atividade],
        observacoes_gerais="Observação de teste",
    )

    session.scalar.return_value = diario

    response = client.get("/diarios/1/imprimir")

    assert response.status_code == 200
    assert response.mimetype == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert "diario_obra_1.docx" in response.headers["Content-Disposition"]

    documento = Document(BytesIO(response.data))

    textos = [paragrafo.text for paragrafo in documento.paragraphs]

    assert "JM ENGENHARIA" in textos
    assert "DIÁRIO DE OBRAS" in textos
    assert "Identificação: Obra de teste" in textos
    assert "Observação de teste" in textos

    assert documento.tables[0].rows[1].cells[0].text == "Eletricista"
    assert documento.tables[0].rows[1].cells[1].text == "3"

    assert documento.tables[1].rows[1].cells[0].text == "Instalações"
    assert documento.tables[1].rows[1].cells[1].text == "Instalação de luminárias"
