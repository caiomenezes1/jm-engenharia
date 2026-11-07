
from io import BytesIO

from docx import Document
from docx.shared import Cm, Pt
from flask import send_file

from datetime import date

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy import select, delete
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



@bp.route("/diarios/<int:id_diario>/excluir", methods=["POST"])
def excluir_diario(id_diario):
    with SessionLocal() as session:
        try:
            diario = session.get(DiarioObra, id_diario)

            if diario is None:
                flash("Diário não encontrado.", "warning")
                return redirect(url_for("main.index"))

            session.execute(
                delete(DiarioProfissional).where(
                    DiarioProfissional.id_diario == id_diario
                )
            )

            session.execute(
                delete(DiarioAtividade).where(
                    DiarioAtividade.id_diario == id_diario
                )
            )

            session.delete(diario)
            session.commit()

            flash("Diário excluído com sucesso!", "success")

        except Exception:
            session.rollback()
            flash("Não foi possível excluir o diário.", "danger")

    return redirect(url_for("main.index"))


@bp.route("/diarios/<int:id_diario>")
def detalhes_diario(id_diario):
    with SessionLocal() as session:
        diario = session.scalar(
            select(DiarioObra)
            .where(DiarioObra.id == id_diario)
            .options(
                selectinload(DiarioObra.profissionais)
                .selectinload(DiarioProfissional.funcao),

                selectinload(DiarioObra.atividades)
                .selectinload(DiarioAtividade.atividade)
                .selectinload(Atividade.grupo)
            )
        )

        if diario is None:
            flash("Diário não encontrado.", "warning")
            return redirect(url_for("main.index"))

        return render_template(
            "detalhes_diario.html",
            diario=diario
        )


@bp.route("/diarios/<int:id_diario>/imprimir")
def imprimir_diario(id_diario):
    with SessionLocal() as session:
        diario = session.scalar(
            select(DiarioObra)
            .where(DiarioObra.id == id_diario)
            .options(
                selectinload(DiarioObra.profissionais)
                .selectinload(DiarioProfissional.funcao),

                selectinload(DiarioObra.atividades)
                .selectinload(DiarioAtividade.atividade)
                .selectinload(Atividade.grupo)
            )
        )

        if diario is None:
            flash("Diário não encontrado.", "warning")
            return redirect(url_for("main.index"))

        documento = Document()

        # Configuração da página
        secao = documento.sections[0]
        secao.top_margin = Cm(2)
        secao.bottom_margin = Cm(2)
        secao.left_margin = Cm(2)
        secao.right_margin = Cm(2)

        # Título
        titulo = documento.add_heading("JM ENGENHARIA", level=0)
        titulo.alignment = 1

        subtitulo = documento.add_paragraph("DIÁRIO DE OBRAS")
        subtitulo.alignment = 1

        # Dados da obra
        documento.add_heading("Dados da obra", level=1)

        documento.add_paragraph(
            f"Identificação: {diario.identificacao_obra}"
        )

        documento.add_paragraph(
            f"Data: {diario.data_diario.strftime('%d/%m/%Y')}"
        )

        # Profissionais
        documento.add_heading("Profissionais", level=1)

        tabela = documento.add_table(rows=1, cols=2)
        tabela.style = "Table Grid"

        tabela.rows[0].cells[0].text = "Função"
        tabela.rows[0].cells[1].text = "Quantidade"

        for profissional in diario.profissionais:
            celulas = tabela.add_row().cells
            celulas[0].text = profissional.funcao.nome_funcao
            celulas[1].text = str(profissional.quantidade)

        # Atividades
        documento.add_heading("Atividades realizadas", level=1)

        tabela = documento.add_table(rows=1, cols=2)
        tabela.style = "Table Grid"

        tabela.rows[0].cells[0].text = "Grupo"
        tabela.rows[0].cells[1].text = "Atividade"

        for item in diario.atividades:
            celulas = tabela.add_row().cells
            celulas[0].text = item.atividade.grupo.nome_grupo
            celulas[1].text = item.atividade.descricao_atividade

        # Observações gerais
        if diario.observacoes_gerais:
            documento.add_heading("Observações gerais", level=1)
            documento.add_paragraph(diario.observacoes_gerais)

        # Geração do arquivo em memória
        arquivo = BytesIO()
        documento.save(arquivo)
        arquivo.seek(0)

        nome_arquivo = f"diario_obra_{diario.id}.docx"

        return send_file(
            arquivo,
            as_attachment=True,
            download_name=nome_arquivo,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )    