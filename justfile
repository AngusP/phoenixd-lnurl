_default:
  @just --list --unsorted --justfile {{justfile()}}

# Install development dependencies
install:
    @echo "📦 Installing requirements..."
    pip install pip-tools
    pip-sync requirements-dev.txt
    @echo "✅ Done"

# Run a dev server
serve:
    #!/usr/bin/env bash
    _=$(lsof -i:8000 -P -n -t)
    if [ "$?" == "1" ]; then
        uvicorn app.main:app_factory --factory --reload --reload-include '*.env';
    else
        echo "💡 Port 8000 is in use, the server is probably already running"
    fi

# Update package dependencies (can change requirements)
update:
    pip-compile -Uq --strip-extras
    pip-compile -Uq --strip-extras requirements-dev.in
    @git diff requirements*
    @echo "🤔 Rememeber to run 'just install' to apply package updates!"

# Run python linters and tests (just checks code)
test: lint pytest mypy

# Run python formatters (can change code)
format:
    ruff check --select I --fix
    ruff format
    ruff check --fix

alias fmt := format

# Run python linters (just checks code)
lint:
    ruff check

# Run python tests
pytest *pytest_args="-vx":
    IS_TEST=1 pytest --cov=app --cov-report html {{pytest_args}}

# Run python type checking
mypy *files=".":
    mypy {{files}}

open_cmd := if os() == "macos" { "open" } else if os() == "windows" { "wslview" } else { "xdg-open" }

# Open auto-generated API docs
docs:
    #!/usr/bin/env bash
    _=$(lsof -i:8000 -P -n -t)
    if [ "$?" == "1" ]; then
        echo "😱 You need to run 'just serve' first to view the docs"
    else
        {{open_cmd}} 'http://127.0.0.1:8000/docs'
    fi
