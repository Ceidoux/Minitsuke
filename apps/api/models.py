from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Text,
    UniqueConstraint,
    false,
)
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
        CheckConstraint(
            "frequency_band > 0",
            name="ck_jmdict_entries_positive_frequency_band",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column()
    is_common: Mapped[bool] = mapped_column(
        nullable=False,
        server_default=false(),
    )
    frequency_band: Mapped[int | None] = mapped_column(nullable=True)


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
        UniqueConstraint(
            "entry_id",
            "id",
            name="uq_jmdict_written_forms_entry_id",
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
    search_text: Mapped[str] = mapped_column(Text, nullable=False)
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
        UniqueConstraint(
            "entry_id",
            "id",
            name="uq_jmdict_readings_entry_id",
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
    search_text: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column()
    no_kanji: Mapped[bool] = mapped_column()


class JmdictReadingRestrictionRecord(Base):
    __tablename__ = "jmdict_reading_restrictions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["entry_id", "reading_id"],
            ["jmdict_readings.entry_id", "jmdict_readings.id"],
            name="fk_jmdict_reading_restrictions_reading",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["entry_id", "written_form_id"],
            ["jmdict_written_forms.entry_id", "jmdict_written_forms.id"],
            name="fk_jmdict_reading_restrictions_written_form",
            ondelete="CASCADE",
        ),
    )

    entry_id: Mapped[int] = mapped_column()
    reading_id: Mapped[int] = mapped_column(primary_key=True)
    written_form_id: Mapped[int] = mapped_column(primary_key=True)


class JmdictSenseRecord(Base):
    __tablename__ = "jmdict_senses"
    __table_args__ = (
        UniqueConstraint(
            "entry_id",
            "position",
            name="uq_jmdict_senses_entry_position",
        ),
        UniqueConstraint(
            "entry_id",
            "id",
            name="uq_jmdict_senses_entry_id",
        ),
        CheckConstraint(
            "position > 0",
            name="ck_jmdict_senses_positive_position",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("jmdict_entries.id", ondelete="CASCADE"),
    )
    position: Mapped[int] = mapped_column()


class JmdictGlossRecord(Base):
    __tablename__ = "jmdict_glosses"
    __table_args__ = (
        UniqueConstraint(
            "sense_id",
            "position",
            name="uq_jmdict_glosses_sense_position",
        ),
        CheckConstraint(
            "position > 0",
            name="ck_jmdict_glosses_positive_position",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sense_id: Mapped[int] = mapped_column(
        ForeignKey("jmdict_senses.id", ondelete="CASCADE"),
    )
    text: Mapped[str] = mapped_column(Text)
    language: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column()


class JmdictPartOfSpeechRecord(Base):
    __tablename__ = "jmdict_parts_of_speech"
    __table_args__ = (
        UniqueConstraint(
            "sense_id",
            "position",
            name="uq_jmdict_parts_of_speech_sense_position",
        ),
        CheckConstraint(
            "position > 0",
            name="ck_jmdict_parts_of_speech_positive_position",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sense_id: Mapped[int] = mapped_column(
        ForeignKey("jmdict_senses.id", ondelete="CASCADE"),
    )
    label: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column()


class JmdictSenseWrittenFormRestrictionRecord(Base):
    __tablename__ = "jmdict_sense_written_form_restrictions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["entry_id", "sense_id"],
            ["jmdict_senses.entry_id", "jmdict_senses.id"],
            name="fk_jmdict_sense_written_form_restrictions_sense",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["entry_id", "written_form_id"],
            ["jmdict_written_forms.entry_id", "jmdict_written_forms.id"],
            name="fk_jmdict_sense_written_form_restrictions_target",
            ondelete="CASCADE",
        ),
    )

    entry_id: Mapped[int] = mapped_column()
    sense_id: Mapped[int] = mapped_column(primary_key=True)
    written_form_id: Mapped[int] = mapped_column(primary_key=True)


class JmdictSenseReadingRestrictionRecord(Base):
    __tablename__ = "jmdict_sense_reading_restrictions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["entry_id", "sense_id"],
            ["jmdict_senses.entry_id", "jmdict_senses.id"],
            name="fk_jmdict_sense_reading_restrictions_sense",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["entry_id", "reading_id"],
            ["jmdict_readings.entry_id", "jmdict_readings.id"],
            name="fk_jmdict_sense_reading_restrictions_target",
            ondelete="CASCADE",
        ),
    )

    entry_id: Mapped[int] = mapped_column()
    sense_id: Mapped[int] = mapped_column(primary_key=True)
    reading_id: Mapped[int] = mapped_column(primary_key=True)
