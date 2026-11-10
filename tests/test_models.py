
from sqlalchemy import inspect

from app.database import Base
from app.models import (
    DiarioObra,
    FuncaoProfissional,
    DiarioProfissional,
    GrupoAtividade,
    Atividade,
    DiarioAtividade,
)


def test_all_models_are_registered():
    expected_tables = {
        "diario_obra",
        "funcao_profissional",
        "diario_profissional",
        "grupo_atividade",
        "atividade",
        "diario_atividade",
    }

    assert expected_tables.issubset(Base.metadata.tables.keys())


def test_models_have_identity_primary_keys():
    models = [
        DiarioObra,
        FuncaoProfissional,
        DiarioProfissional,
        GrupoAtividade,
        Atividade,
        DiarioAtividade,
    ]

    for model in models:
        primary_key = model.__table__.c.id

        assert primary_key.primary_key
        assert primary_key.identity is not None


def test_active_fields_have_true_default():
    models = [
        FuncaoProfissional,
        GrupoAtividade,
        Atividade,
    ]

    for model in models:
        assert model.__table__.c.ativo.default.arg is True


def test_unique_constraints_are_configured():
    assert FuncaoProfissional.__table__.c.nome_funcao.unique is True
    assert GrupoAtividade.__table__.c.nome_grupo.unique is True

    expected_constraints = {
        "diario_profissional": "uq_diario_profissional",
        "atividade": "uq_grupo_atividade",
        "diario_atividade": "uq_diario_atividade",
    }

    for table_name, constraint_name in expected_constraints.items():
        table = Base.metadata.tables[table_name]
        constraint_names = {
            constraint.name
            for constraint in table.constraints
        }

        assert constraint_name in constraint_names


def test_professional_quantity_must_be_positive():
    constraints = DiarioProfissional.__table__.constraints

    check_constraints = [
        constraint
        for constraint in constraints
        if constraint.name == "ck_quantidade_positiva"
    ]

    assert len(check_constraints) == 1
    assert str(check_constraints[0].sqltext) == "quantidade > 0"


def test_foreign_keys_are_configured():
    expected_foreign_keys = {
        DiarioProfissional: {
            "id_diario": "diario_obra.id",
            "id_funcao": "funcao_profissional.id",
        },
        Atividade: {
            "id_grupo": "grupo_atividade.id",
        },
        DiarioAtividade: {
            "id_diario": "diario_obra.id",
            "id_atividade": "atividade.id",
        },
    }

    for model, expected in expected_foreign_keys.items():
        for column_name, target in expected.items():
            foreign_key = next(
                iter(model.__table__.c[column_name].foreign_keys)
            )

            assert foreign_key.target_fullname == target


def test_relationships_are_configured():
    expected_relationships = [
        (DiarioObra, "profissionais", "diario"),
        (DiarioObra, "atividades", "diario"),
        (FuncaoProfissional, "profissionais", "funcao"),
        (GrupoAtividade, "atividades", "grupo"),
        (DiarioProfissional, "diario", "profissionais"),
        (DiarioProfissional, "funcao", "profissionais"),
        (Atividade, "grupo", "atividades"),
        (Atividade, "diarios", "atividade"),
        (DiarioAtividade, "diario", "atividades"),
        (DiarioAtividade, "atividade", "diarios"),
    ]

    for model, relationship_name, back_populates in expected_relationships:
        relationship = inspect(model).relationships[relationship_name]

        assert relationship.back_populates == back_populates
