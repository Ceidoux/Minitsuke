from sqlalchemy import CheckConstraint, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Word(Base):
    __tablename__ = "words"

    id: Mapped[int] = mapped_column(primary_key=True)
    written_form: Mapped[str] = mapped_column(Text)
    reading: Mapped[str] = mapped_column(Text)


class Meaning(Base):
    __tablename__ = "meanings"

    id: Mapped[int] = mapped_column(primary_key=True)
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id", ondelete="CASCADE"))
    meaning: Mapped[str] = mapped_column(Text)


class JmdictEntryRecord(Base):
    __tablename__ = "jmdict_entries"
    __table_args__ = (
        UniqueConstraint("source_id", name="uq_jmdict_entries_source_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column()


class JmdictWrittenFormRecord(Base):
    __tablename__ = "jmdict_written_forms"
    __table_args__ = (
        UniqueConstraint(
            "entry_id",
            "text",
            name="uq_jmdict_written_forms_entry_text",
        ),
        UniqueConstraint(
            "entry_id",
            "position",
            name="uq_jmdict_written_forms_entry_position",
        ),
        CheckConstraint(
            "position > 0",
            name="ck_jmdict_written_forms_positive_position",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("jmdict_entries.id", ondelete="CASCADE"),
    )
    text: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column()


class JmdictReadingRecord(Base):
    __tablename__ = "jmdict_readings"
    __table_args__ = (
        UniqueConstraint(
            "entry_id",
            "text",
            name="uq_jmdict_readings_entry_text",
        ),
        UniqueConstraint(
            "entry_id",
            "position",
            name="uq_jmdict_readings_entry_position",
        ),
        CheckConstraint(
            "position > 0",
            name="ck_jmdict_readings_positive_position",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("jmdict_entries.id", ondelete="CASCADE"),
    )
    text: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column()
    no_kanji: Mapped[bool] = mapped_column()
