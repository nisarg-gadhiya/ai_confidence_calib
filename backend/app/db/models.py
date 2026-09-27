from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    dataset: Mapped[str] = mapped_column(
        String(100),
        default="gsm8k",
    )

    dataset_question_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    question_text: Mapped[str] = mapped_column(
        Text,
    )

    reference_answer: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    runs: Mapped[list["ReasoningRun"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
    )


class ReasoningRun(Base):
    __tablename__ = "reasoning_runs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id"),
    )

    model_name: Mapped[str] = mapped_column(
        String(200),
    )

    temperature: Mapped[float] = mapped_column(
        Float,
        default=0.0,
    )

    prompt_version: Mapped[str] = mapped_column(
        String(100),
        default="v1",
    )

    final_answer: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    question: Mapped["Question"] = relationship(
        back_populates="runs",
    )

    steps: Mapped[list["ReasoningStep"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
    )


class ReasoningStep(Base):
    __tablename__ = "reasoning_steps"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    run_id: Mapped[int] = mapped_column(
        ForeignKey("reasoning_runs.id"),
    )

    step_number: Mapped[int] = mapped_column(
        Integer,
    )

    step_text: Mapped[str] = mapped_column(
        Text,
    )

    step_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    ground_truth_correct: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )

    run: Mapped["ReasoningRun"] = relationship(
        back_populates="steps",
    )

    signal: Mapped["StepSignal | None"] = relationship(
        back_populates="step",
        uselist=False,
        cascade="all, delete-orphan",
    )


class StepSignal(Base):
    __tablename__ = "step_signals"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    step_id: Mapped[int] = mapped_column(
        ForeignKey("reasoning_steps.id"),
        unique=True,
    )

    verification_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    consistency_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    token_probability: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    entropy: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    fused_confidence: Mapped[float] = mapped_column(
        Float,
    )

    step: Mapped["ReasoningStep"] = relationship(
        back_populates="signal",
    )


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    experiment_id: Mapped[str] = mapped_column(
        String(100),
    )

    top1_accuracy: Mapped[float] = mapped_column(
        Float,
    )

    top2_accuracy: Mapped[float] = mapped_column(
        Float,
    )

    ece: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    brier_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    nll: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )