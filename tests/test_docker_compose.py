from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
REQUIRED_ENV_VARS = [
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "POSTGRES_PORT",
]


def test_compose_file_uses_postgres_18():
    compose = (REPO_ROOT / "docker-compose.yml").read_text()
    assert "postgres:18" in compose


def test_compose_file_has_no_hardcoded_credentials():
    compose = (REPO_ROOT / "docker-compose.yml").read_text()
    for var in REQUIRED_ENV_VARS:
        assert f"${{{var}}}" in compose, f"{var} should be read from the environment"


def test_compose_file_uses_a_named_volume():
    compose = (REPO_ROOT / "docker-compose.yml").read_text()
    assert "volumes:" in compose
    assert "postgres_data:" in compose


def test_env_example_defines_every_required_var():
    env_example = (REPO_ROOT / ".env.example").read_text()
    for var in REQUIRED_ENV_VARS:
        assert f"{var}=" in env_example


def test_env_is_gitignored_but_env_example_is_not():
    gitignore_lines = (REPO_ROOT / ".gitignore").read_text().splitlines()
    assert ".env" in gitignore_lines
    assert ".env.example" not in gitignore_lines


def test_readme_connectivity_check_does_not_require_local_psql_client():
    readme = (REPO_ROOT / "README.md").read_text()
    # The connectivity check must run psql inside the compose-managed
    # container (requires only Docker Compose), not shell out to a psql
    # binary expected to be installed on the host.
    assert "docker compose exec postgres" in readme
    for var in ("POSTGRES_USER", "POSTGRES_DB"):
        assert var in readme


def test_readme_documents_start_stop_and_connectivity_check():
    readme = (REPO_ROOT / "README.md").read_text()
    assert "docker compose up -d" in readme
    assert "docker compose down" in readme
    assert "psql" in readme
