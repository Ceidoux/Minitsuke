import argparse
import os
import sys
from pathlib import Path
from time import perf_counter
from xml.etree import ElementTree as ET

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from jmdict import read_jmdict
from jmdict_importer import save_jmdict_entry


def import_jmdict_file(
    session_factory: sessionmaker[Session],
    path: Path,
    progress_every: int = 1_000,
) -> int:
    if progress_every < 1:
        raise ValueError("Progress interval must be positive")

    count = 0

    with session_factory() as session, session.begin():
        for entry in read_jmdict(path):
            try:
                save_jmdict_entry(session, entry)
            except ValueError as error:
                raise ValueError(f"Entry {entry.source_id}: {error}") from error

            count += 1

            if count % progress_every == 0:
                print(
                    f"Processed {count:,} entries (not yet committed)...",
                    flush=True,
                )

    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Import an uncompressed JMdict XML file in one transaction.",
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Path to the uncompressed JMdict XML file",
    )
    parser.add_argument(
        "--progress-every",
        type=int,
        default=1_000,
        help="Report progress every N entries (default: 1000)",
    )
    args = parser.parse_args(argv)

    if args.progress_every < 1:
        parser.error("--progress-every must be positive")

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        parser.error("DATABASE_URL must be set")

    engine = create_engine(database_url)
    session_factory = sessionmaker(bind=engine)
    started = perf_counter()

    try:
        count = import_jmdict_file(
            session_factory,
            args.path.expanduser(),
            progress_every=args.progress_every,
        )
    except (OSError, ValueError, ET.ParseError, SQLAlchemyError) as error:
        print(f"Import failed: {error}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()

    elapsed = perf_counter() - started
    print(f"Imported {count:,} entries in {elapsed:.1f} seconds. Committed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
