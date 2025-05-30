from datetime import datetime
import os
from pathlib import Path
from typing import Any, Optional, Tuple

from invoke import Context, task

BASE_DIR = "ehp"


@task
def black(ctx: Context) -> Any:
    """Runs black to auto-format the Python code."""
    result = ctx.run('black --exclude=".venv" .', echo=True, pty=True)  # noqa
    return result.stdout, result.stderr, result.exited


@task
def flake8(ctx: Context) -> Any:
    """Run a style check using .flake8."""
    result = ctx.run("flake8 . ", echo=True, pty=True)
    return result.stdout, result.stderr, result.exited


@task
def mypy(ctx: Context) -> Any:
    cmd = f"mypy --namespace-packages {BASE_DIR}"
    result = ctx.run(cmd, echo=True, pty=True)
    return result.stdout, result.stderr, result.exited


@task
def vulture_whitelist(ctx: Context) -> Any:
    """Runs vulture to find abandoned Python code."""
    result = ctx.run(
        f"vulture {BASE_DIR} --min-confidence 100 --make-whitelist > tasks/whitelist.py",
        echo=True,
        pty=True,
    )
    return result.stdout, result.stderr, result.exited


@task
def vulture(ctx: Context) -> Any:
    """Runs vulture to find abandoned Python code."""
    cmd = [f"vulture {BASE_DIR}", "--min-confidence 100"]
    site_root = os.path.realpath(os.path.dirname(__file__))
    if os.path.isfile(f"{site_root}/whitelist.py"):
        cmd.insert(1, "tasks/whitelist.py")
    result = ctx.run(" ".join(cmd), echo=True, pty=True)
    return result.stdout, result.stderr, result.exited


@task
def lint(ctx: Context) -> None:
    """Runs all linting checks in the following order: black, .flake8, and mypy."""
    print("1. Running black.")
    black(ctx)
    print("\n2. Running .flake8.")
    flake8(ctx)
    print("\n3. Running vulture.")
    vulture(ctx)
    print("\n4. Running mypy.")
    mypy(ctx)
    print("\nAll linting checks passed!")


@task
def build(ctx: Context) -> None:
    """Build the cluster."""
    # ensure_docker_network_exists(ctx)
    ctx.run("docker compose build", pty=True)


@task
def kill(ctx: Context) -> None:
    """Stop the application."""
    ctx.run("docker-compose kill", pty=True)


def build_pytest_cmd(
    cwd: Optional[str],
    exitfirst: bool,
    keyword: Optional[str],
    no_coverage: bool,
    verbose: bool,
    pdb: bool,
    no_capture: bool,
    ignore_collection_errors: bool,
    term_missing: bool,
) -> str:
    cmd_parts = ["pytest"]
    if cwd:
        cmd_parts.append(cwd)
    if exitfirst:
        cmd_parts.append("--exitfirst")
    if verbose:
        cmd_parts.append("-v")
    if keyword:
        cmd_parts.append(f"-k '{keyword}'")
    if no_coverage:
        cmd_parts.append("--no-cov")
    else:
        cmd_parts.append("--cov")
        if term_missing:
            cmd_parts.append("--cov-report term-missing")

    if pdb:
        cmd_parts.append("--pdb")
    if no_capture:
        cmd_parts.append("-s")
    if ignore_collection_errors:
        cmd_parts.append("--continue-on-collection-errors")

    cmd = " ".join(cmd_parts)
    return cmd


@task(
    help={
        "keyword": "If specified, select tests by keyword expression.",
        "exitfirst": "Should testing stop at the first failure?",
        "no-coverage": "If specified, test coverage will not be calculated.",
        "verbose": "If specified, run the tests with additional logging info.",
        "term-missing": "If specified, show missing lines in coverage report.",
    }
)
def pytest(
    ctx: Context,
    exitfirst: bool = False,
    keyword: Optional[str] = None,
    no_coverage: bool = False,
    verbose: bool = False,
    pdb: bool = False,
    no_capture: bool = True,
    run_in_docker: bool = True,
    ignore_collection_errors: bool = True,
    term_missing: bool = False,
) -> None:
    """Run unit tests using pytest."""
    cmd = build_pytest_cmd(
        f"{BASE_DIR}/",
        exitfirst,
        keyword,
        no_coverage,
        verbose,
        pdb,
        no_capture,
        ignore_collection_errors,
        term_missing,
    )
    run_command(ctx, cmd, run_in_docker)


########################################################################################
#                                     Shell utils                                      #
########################################################################################
@task
def connect(ctx: Context) -> None:
    """Connect to main container."""
    os.system(f"docker-compose exec {BASE_DIR}-application /bin/bash")


def run_command(
    ctx: Context,
    cmd: str,
    system: bool = False,
    echo: bool = False,
) -> Tuple[str, str, int]:
    if system:
        exit_status = os.system(cmd)
        return "", "", exit_status
    else:
        result = ctx.run(cmd, echo=echo, pty=True)
        return result.stdout, result.stderr, result.exited


@task()
def standalone(ctx: Context, env: Optional[str] = None) -> None:
    """Run the container."""
    cmd_parts = [
        "uvicorn application:app --port=11000 --reload --host=0.0.0.0 --log-level=debug"
    ]
    if env:
        cmd_parts.append(f"--env={env}")
    cmd = " ".join(cmd_parts)
    run_command(ctx, cmd, echo=True)


@task()
def run(
    ctx: Context,
    env: Optional[str] = None,
    detached: bool = False,
) -> None:
    """Run the container."""
    cmd_parts = [f"docker compose up {'-d' if detached else ''}"]
    if env:
        cmd_parts.append(f"--env={env}")
    cmd = " ".join(cmd_parts)
    run_command(ctx, cmd, echo=True)


@task
def restart(ctx: Context) -> None:
    """Restarts the server."""
    print("1. Killing...")
    kill(ctx)
    print("\n2. Building...")
    build(ctx)
    print("\n3. Running...")
    run(ctx)


@task
def db_init(ctx: Context) -> None:
    site_root = os.path.realpath(os.path.dirname(__file__))
    path = Path(site_root)
    migrations_folder = os.path.join(path.parent.absolute(), "migrations")
    if os.path.isdir(migrations_folder):
        print("Database already exists...")
    else:
        print("Initializing database migration files...")
        ctx.run("alembic init migrations", pty=True)


@task
def db_make_migrations(ctx: Context) -> None:
    print("Initializing database migration files...")
    year = datetime.now().year
    month = datetime.now().month
    day = datetime.now().day
    hour = datetime.now().hour
    minute = datetime.now().minute
    second = datetime.now().second
    date_stamp = f"{year}-{month}-{day}-{hour}-{minute}-{second}"
    ctx.run(
        f"alembic revision --autogenerate -m '{BASE_DIR}-db-{date_stamp}'", pty=True
    )


@task
def db_upgrade(ctx: Context) -> None:
    ctx.run("alembic upgrade head", pty=True)


# inv migrate
@task
def migrate(ctx: Context) -> None:
    print("\n1. Making migrations...")
    db_make_migrations(ctx)
    print("\n2. Upgrading database...")
    db_upgrade(ctx)


@task
def db_history(ctx: Context) -> None:
    ctx.run("alembic history", pty=True)


@task
def db_fix_heads(ctx: Context) -> None:
    ctx.run("alembic merge heads -m 'Fixing multiple heads'", pty=True)


@task
def pip_compile(ctx: Context) -> None:
    ctx.run("pip-compile requirements/requirements.in", pty=True)
    print("Requirements compiled.")


@task
def pip_sync(ctx: Context) -> None:
    ctx.run("pip-sync --user requirements/requirements.txt", pty=True)
    print("Requirements synchronized.")


@task
def pip_compile_sync(ctx: Context) -> None:
    """Restarts the server."""
    print("1. Compiling...")
    pip_compile(ctx)
    print("\n2. Synchronizing...")
    pip_sync(ctx)
