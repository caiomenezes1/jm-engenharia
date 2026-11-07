
from datetime import date

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import SessionLocal
from app.models import (
    Atividade,
    DiarioAtividade,
    DiarioObra,
    DiarioProfissional,
    FuncaoProfissional,
    GrupoAtividade,
)

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    with SessionLocal() as session:
        diarios = session.scalars(
            select(DiarioObra).order_by(
                DiarioObra.data_diario.desc(),
                DiarioObra.id.desc()
            )
        ).all()

    return render_template("index.html", diarios=diarios)


@bp.route("/diarios/novo", methods=["GET", "POST"])
def novo_diario():
    with SessionLocal() as session:

        funcoes = session.scalars(
            select(FuncaoProfissional)
            .where(FuncaoProfissional.ativo.is_(True))
            .order_by(FuncaoProfissional.nome_funcao)
        ).all()

        grupos = session.scalars(
            select(GrupoAtividade)
            .where(GrupoAtividade.ativo.is_(True))
            .options(selectinload(GrupoAtividade.atividades))
            .order_by(GrupoAtividade.nome_grupo)
        ).all()

        if request.method == "POST":

            obra = request.form.get("identificacao_obra", "").strip()
            data_texto = request.form.get("data_diario", "")
            observacoes = request.form.get(
                "observacoes_gerais", ""
            ).strip()

            erros = []

            if not obra:
                erros.append("Informe a identificação da obra.")
            elif len(obra) > 150:
                erros.append("A identificação da obra deve ter até 150 caracteres.")

            try:
                data_diario = date.fromisoformat(data_texto)
            except ValueError:
                data_diario = None
                erros.append("Informe uma data válida.")

            profissionais = []

            for funcao in funcoes:
                quantidade_texto = request.form.get(
                    f"quantidade_{funcao.id}", ""
                ).strip()

                if not quantidade_texto:
                    continue

                try:
                    quantidade = int(quantidade_texto)
                except ValueError:
                    erros.append(
                        f"Quantidade inválida para {funcao.nome_funcao}."
                    )
                    continue

                if quantidade < 0:
                    erros.append(
                        f"A quantidade de {funcao.nome_funcao} não pode ser negativa."
                    )
                elif quantidade > 0:
                    profissionais.append((funcao.id, quantidade))

            if not profissionais:
                erros.append("Informe pelo menos uma função profissional.")

            atividades_ids = request.form.getlist("atividade_ids")

            atividades_disponiveis = {
                atividade.id
                for grupo in grupos
                for atividade in grupo.atividades
                if atividade.ativo
            }

            try:
                atividades_ids = list(dict.fromkeys(
                    int(id_atividade) for id_atividade in atividades_ids
                ))
            except ValueError:
                atividades_ids = []
                erros.append("Seleção de atividades inválida.")

            if not atividades_ids:
                erros.append("Selecione pelo menos uma atividade.")
            elif not set(atividades_ids).issubset(atividades_disponiveis):
                erros.append("Uma ou mais atividades selecionadas são inválidas.")

            if erros:
                return render_template(
                    "novo_diario.html",
                    funcoes=funcoes,
                    grupos=grupos,
                    erros=erros,
                    atividades_selecionadas=[
                        str(id) for id in atividades_ids
                    ]
                )

            diario = DiarioObra(
                identificacao_obra=obra,
                data_diario=data_diario,
                observacoes_gerais=observacoes or None
            )

            session.add(diario)
            session.flush()

            for id_funcao, quantidade in profissionais:
                session.add(
                    DiarioProfissional(
                        id_diario=diario.id,
                        id_funcao=id_funcao,
                        quantidade=quantidade
                    )
                )

            for id_atividade in atividades_ids:
                session.add(
                    DiarioAtividade(
                        id_diario=diario.id,
                        id_atividade=id_atividade
                    )
                )

            try:
                session.commit()
                flash("Diário cadastrado com sucesso!", "success")
                return redirect(url_for("main.index"))

            except Exception:
                import traceback

                traceback.print_exc()
                session.rollback()
                erros.append(
                    "Não foi possível salvar o diário. Verifique os dados e tente novamente."
                )

            return render_template(
                "novo_diario.html",
                funcoes=funcoes,
                grupos=grupos,
                erros=erros,
                atividades_selecionadas=[
                    str(id) for id in atividades_ids
                ]
            )

        return render_template(
            "novo_diario.html",
            funcoes=funcoes,
            grupos=grupos,
            erros=[],
            atividades_selecionadas=[]
        )
