"""Compare committed completion implementations using read-only local HTTP APIs.

From the repository root, with the API environment and DATABASE_URL available:
    apps/api/.venv/bin/python scripts/benchmark_conjugation_completions.py \
        --output /tmp/completion-comparison.json

Temporary API processes and source snapshots keep application code and database
contents read-only during comparison. The two source revisions remain explicit
so rerunning this diagnostic after later commits compares the same implementations.
"""

import argparse
import hashlib
import http.client
import io
import itertools
import json
import os
import platform
import random
import socket
import statistics
import subprocess
import sys
import tarfile
import tempfile
import time
from contextlib import ExitStack
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ("original", "normalization", "indexed")
QUERIES = ("食べま", "tabemas", "takakun")
BASELINE_REF = "e10c00cbc97cb80550edbc57a5375621a3134855"
INDEXED_REF = "2813b475b8b04bbf484f920ce082dc5fcf631365"


def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args], cwd=ROOT)


def prepare_sources(directory: Path, baseline_ref: str, indexed_ref: str):
    with tarfile.open(
        fileobj=io.BytesIO(git("archive", indexed_ref, "apps/api"))
    ) as archive:
        archive.extractall(directory / "shared", filter="data")
    api = directory / "shared/apps/api"
    lookup = (api / "conjugation_lookup.py").read_text()
    lazy = (
        "    for candidate, possible_prefixes in candidate_prefixes.items():\n"
        "        base = None\n"
    )
    deferred = (
        "                if base is None:\n"
        "                    base = normalize_written_form(candidate.dictionary_form)\n\n"
    )
    if lookup.count(lazy) != 1 or lookup.count(deferred) != 1:
        raise RuntimeError(
            "Indexed revision does not contain the expected deferred normalization"
        )
    eager_lookup = lookup.replace(
        lazy,
        "    for candidate, possible_prefixes in candidate_prefixes.items():\n"
        "        base = normalize_written_form(candidate.dictionary_form)\n",
    ).replace(deferred, "")
    scanned_reverse = git("show", f"{baseline_ref}:apps/api/reverse_conjugation.py")
    indexed_reverse = (api / "reverse_conjugation.py").read_bytes()
    variants = {}
    for name in VARIANTS:
        variant = directory / name
        variant.mkdir()
        (variant / "conjugation_lookup.py").write_text(
            eager_lookup if name == "original" else lookup
        )
        (variant / "reverse_conjugation.py").write_bytes(
            indexed_reverse if name == "indexed" else scanned_reverse
        )
        variants[name] = variant
        for path in variant.glob("*.py"):
            compile(path.read_bytes(), str(path), "exec")
    # All variants retain the merged search-only lookup fixes and share every
    # other module from indexed_ref, rather than using uncommitted local files.
    return api, variants


def load_variant(api: Path, variant: Path):
    sys.path[:0] = [str(variant), str(api)]


def serve(api: Path, variant: Path, fd: int):
    load_variant(api, variant)
    import uvicorn
    from sqlalchemy import text
    from sqlalchemy.orm import Session

    # isort: split
    from database import engine, get_session
    from main import app

    def read_only_session():
        with Session(engine) as session:
            session.execute(text("SET TRANSACTION READ ONLY"))
            yield session

    app.dependency_overrides[get_session] = read_only_session

    class CpuTiming:
        async def __call__(self, scope, receive, send):
            started = time.process_time_ns()

            async def timed_send(message):
                if message["type"] == "http.response.start":
                    elapsed = (time.process_time_ns() - started) / 1_000_000
                    message["headers"] = [
                        *message.get("headers", []),
                        (b"x-benchmark-cpu-ms", str(elapsed).encode("ascii")),
                    ]
                await send(message)

            await app(scope, receive, timed_send)

    uvicorn.run(
        CpuTiming(),
        fd=fd,
        log_level="warning",
        access_log=False,
        timeout_keep_alive=300,
    )


def measure_index_memory(api: Path, variant: Path):
    load_variant(api, variant)
    import tracemalloc

    import reverse_conjugation as reverse

    reverse._reverse_rules()
    reverse._adjective_reverse_rules()
    if not hasattr(reverse, "_reverse_prefix_index"):
        return {
            "retained_bytes": 0,
            "peak_bytes": 0,
            "prefixes": 0,
            "rule_references": 0,
        }
    tracemalloc.start()
    index = reverse._reverse_prefix_index()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "retained_bytes": current,
        "peak_bytes": peak,
        "prefixes": len(index),
        "rule_references": sum(len(rules) for rules in index.values()),
    }


def database_inventory(api: Path):
    sys.path.insert(0, str(api))
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url
    from sqlalchemy.orm import Session

    url = make_url(os.environ["DATABASE_URL"])
    if url.database != "smartjisho":
        raise ValueError(
            "Benchmark requires the populated smartjisho development database"
        )
    engine = create_engine(url, connect_args={"connect_timeout": 3})
    try:
        with Session(engine) as session:
            session.execute(text("SET TRANSACTION READ ONLY"))
            count = session.scalar(text("SELECT count(*) FROM jmdict_entries"))
            if not count:
                raise RuntimeError(
                    "Development dictionary is empty; benchmark cannot run"
                )
            return {
                "database": url.database,
                "entries": count,
                "migration": session.execute(
                    text("SELECT version_num FROM alembic_version")
                )
                .scalars()
                .all(),
                "postgres_version": session.scalar(text("SHOW server_version")),
            }
    finally:
        engine.dispose()


def request(connection: http.client.HTTPConnection, path: str):
    started = time.perf_counter_ns()
    connection.request("GET", path)
    response = connection.getresponse()
    data = response.read()
    elapsed = (time.perf_counter_ns() - started) / 1_000_000
    if response.status != 200:
        raise RuntimeError(f"HTTP {response.status} for {path}: {data[:300]!r}")
    canonical = json.dumps(
        json.loads(data), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return {
        "http_ms": elapsed,
        "server_cpu_ms": float(response.getheader("x-benchmark-cpu-ms")),
        "sha256": hashlib.sha256(canonical.encode()).hexdigest(),
    }


def start_server(stack: ExitStack, api: Path, variant: Path, directory: Path):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(128)
        port = listener.getsockname()[1]
        log = stack.enter_context((directory / f"{variant.name}.log").open("w"))
        process = subprocess.Popen(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--mode",
                "serve",
                "--api",
                str(api),
                "--variant",
                str(variant),
                "--fd",
                str(listener.fileno()),
            ],
            pass_fds=(listener.fileno(),),
            stdout=log,
            stderr=log,
        )

    def stop():
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

    stack.callback(stop)
    for attempt in range(200):
        if process.poll() is not None:
            raise RuntimeError(
                f"{variant.name} server failed: {(directory / f'{variant.name}.log').read_text()}"
            )
        connection = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
        try:
            request(connection, "/openapi.json")
            stack.callback(connection.close)
            return connection
        except OSError:
            connection.close()
            time.sleep(0.05)
    raise RuntimeError(f"{variant.name} server did not become ready")


def paired_savings(before, after, metric: str):
    deltas = [old[metric] - new[metric] for old, new in zip(before, after, strict=True)]
    rng = random.Random(42)
    bootstraps = sorted(
        statistics.median(rng.choices(deltas, k=len(deltas))) for _ in range(2000)
    )
    return {
        "median_saved_ms": statistics.median(deltas),
        "mean_saved_ms": statistics.mean(deltas),
        "faster_rounds": sum(delta > 0 for delta in deltas),
        "rounds": len(deltas),
        "median_saved_bootstrap_95_interval_ms": [bootstraps[49], bootstraps[1949]],
    }


def benchmark(args):
    if args.rounds < 6 or args.rounds % 6:
        raise ValueError(
            "Rounds must be a positive multiple of six to balance variant order"
        )
    rng = random.Random(args.seed)
    results = {
        "baseline_ref": git("rev-parse", args.baseline_ref).decode().strip(),
        "indexed_ref": git("rev-parse", args.indexed_ref).decode().strip(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "rounds": args.rounds,
        "warmups_per_query": 3,
        "seed": args.seed,
        "samples": {query: {variant: [] for variant in VARIANTS} for query in QUERIES},
    }
    with (
        tempfile.TemporaryDirectory(prefix="minitsuke-completion-") as temporary,
        ExitStack() as stack,
    ):
        directory = Path(temporary)
        api, variants = prepare_sources(directory, args.baseline_ref, args.indexed_ref)
        results["database"] = database_inventory(api)
        print(json.dumps({"database": results["database"]}), flush=True)
        results["index_memory"] = {}
        for name, variant in variants.items():
            measurement = subprocess.check_output(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--mode",
                    "memory",
                    "--api",
                    str(api),
                    "--variant",
                    str(variant),
                ],
                text=True,
            )
            results["index_memory"][name] = json.loads(measurement)
        connections = {
            name: start_server(stack, api, variant, directory)
            for name, variant in variants.items()
        }
        paths = {
            query: "/api/v1/search?"
            + urlencode({"q": query, "limit": 30, "offset": 0, "languages": "eng"})
            for query in QUERIES
        }
        expected = {}
        for query, path in paths.items():
            for name in VARIANTS:
                for _ in range(3):
                    result = request(connections[name], path)
                    expected.setdefault(path, result["sha256"])
                    assert result["sha256"] == expected[path], (name, query)
        controls = (
            "/api/v1/search?"
            + urlencode({"q": query, "limit": 30, "offset": offset, "languages": "eng"})
            for query, offset in (
                ("学校", 0),
                ("たべ", 30),
                ("school", 0),
                ("食べさせられました", 0),
                ("takakunai", 0),
                ("でかけられる", 0),
            )
        )
        control_paths = [
            *controls,
            "/api/v1/search?"
            + urlencode([("q", "学校"), ("languages", "eng"), ("languages", "fre")]),
            "/api/v1/entries/1000800?languages=eng",
            "/api/v1/entries/1983740?languages=eng",
        ]
        for path in control_paths:
            for name in VARIANTS:
                result = request(connections[name], path)
                expected.setdefault(path, result["sha256"])
                assert result["sha256"] == expected[path], (name, path)
        results["response_sha256"] = expected
        orders = list(itertools.permutations(VARIANTS))
        schedules = {}
        for query in QUERIES:
            schedules[query] = orders * (args.rounds // 6)
            rng.shuffle(schedules[query])
        print(
            "Warmups and 12 response-equality cases passed; starting balanced measurements",
            flush=True,
        )
        for round_number in range(args.rounds):
            queries = list(QUERIES)
            rng.shuffle(queries)
            for query in queries:
                for name in schedules[query][round_number]:
                    result = request(connections[name], paths[query])
                    assert result["sha256"] == expected[paths[query]], (name, query)
                    results["samples"][query][name].append(
                        {
                            "http_ms": result["http_ms"],
                            "server_cpu_ms": result["server_cpu_ms"],
                        }
                    )
            if (round_number + 1) % 6 == 0:
                print(
                    f"Completed {round_number + 1}/{args.rounds} balanced rounds",
                    flush=True,
                )
        results["summary"] = {}
        for query, samples in results["samples"].items():
            summary = {
                name: {
                    metric: {
                        "median_ms": statistics.median(row[metric] for row in rows),
                        "mean_ms": statistics.mean(row[metric] for row in rows),
                    }
                    for metric in ("http_ms", "server_cpu_ms")
                }
                for name, rows in samples.items()
            }
            summary["paired_savings"] = {
                f"{old}_to_{new}": {
                    metric: paired_savings(samples[old], samples[new], metric)
                    for metric in ("http_ms", "server_cpu_ms")
                }
                for old, new in (
                    ("original", "normalization"),
                    ("normalization", "indexed"),
                    ("original", "indexed"),
                )
            }
            results["summary"][query] = summary
            print(json.dumps({query: summary}, ensure_ascii=False), flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
    print(f"Results saved to {args.output}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode", choices=("benchmark", "serve", "memory"), default="benchmark"
    )
    parser.add_argument("--baseline-ref", default=BASELINE_REF)
    parser.add_argument("--indexed-ref", default=INDEXED_REF)
    parser.add_argument("--rounds", type=int, default=48)
    parser.add_argument("--seed", type=int, default=20261008)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--api", type=Path)
    parser.add_argument("--variant", type=Path)
    parser.add_argument("--fd", type=int)
    args = parser.parse_args()
    if args.mode == "serve":
        serve(args.api, args.variant, args.fd)
    elif args.mode == "memory":
        print(json.dumps(measure_index_memory(args.api, args.variant)))
    else:
        if args.output is None:
            parser.error("--output is required for benchmark mode")
        benchmark(args)


if __name__ == "__main__":
    main()
