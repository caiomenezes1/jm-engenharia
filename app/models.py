
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Identity,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DiarioObra(Base):
    __tablename__ = "diario_obra"

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    identificacao_obra: Mapped[str] = mapped_column(String(150), nullable=False)
    data_diario: Mapped[Date] = mapped_column(Date, nullable=False)
    observacoes_gerais: Mapped[str | None] = mapped_column(Text, nullable=True)

    profissionais: Mapped[list["DiarioProfissional"]] = relationship(
        back_populates="diario"
    )
    atividades: Mapped[list["DiarioAtividade"]] = relationship(
        back_populates="diario"
    )


class FuncaoProfissional(Base):
    __tablename__ = "funcao_profissional"

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    nome_funcao: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True
    )
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    profissionais: Mapped[list["DiarioProfissional"]] = relationship(
        back_populates="funcao"
    )


class DiarioProfissional(Base):
    __tablename__ = "diario_profissional"

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    id_diario: Mapped[int] = mapped_column(
        ForeignKey("diario_obra.id"), nullable=False
    )
    id_funcao: Mapped[int] = mapped_column(
        ForeignKey("funcao_profissional.id"), nullable=False
    )
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "id_diario", "id_funcao",
            name="uq_diario_profissional"
        ),
        CheckConstraint(
            "quantidade > 0",
            name="ck_quantidade_positiva"
        ),
    )

    diario: Mapped["DiarioObra"] = relationship(
        back_populates="profissionais"
    )
    funcao: Mapped["FuncaoProfissional"] = relationship(
        back_populates="profissionais"
    )


class GrupoAtividade(Base):
    __tablename__ = "grupo_atividade"

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    nome_grupo: Mapped[str] = mapped_column(
        String(150), nullable=False, unique=True
    )
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    atividades: Mapped[list["Atividade"]] = relationship(
        back_populates="grupo"
    )


class Atividade(Base):
    __tablename__ = "atividade"

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    id_grupo: Mapped[int] = mapped_column(
        ForeignKey("grupo_atividade.id"), nullable=False
    )
    descricao_atividade: Mapped[str] = mapped_column(
        String(500), nullable=False
    )
    ativo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "id_grupo", "descricao_atividade",
            name="uq_grupo_atividade"
        ),
    )

    grupo: Mapped["GrupoAtividade"] = relationship(
        back_populates="atividades"
    )
    diarios: Mapped[list["DiarioAtividade"]] = relationship(
        back_populates="atividade"
    )


class DiarioAtividade(Base):
    __tablename__ = "diario_atividade"

    id: Mapped[int] = mapped_column(Identity(), primary_key=True)
    id_diario: Mapped[int] = mapped_column(
        ForeignKey("diario_obra.id"), nullable=False
    )
    id_atividade: Mapped[int] = mapped_column(
        ForeignKey("atividade.id"), nullable=False
    )
    observacao: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "id_diario", "id_atividade",
            name="uq_diario_atividade"
        ),
    )

    diario: Mapped["DiarioObra"] = relationship(
        back_populates="atividades"
    )
    atividade: Mapped["Atividade"] = relationship(
        back_populates="diarios"
    )
