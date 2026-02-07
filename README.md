# DeveloperDoc.ai Backend

This is the enterprise backend for the DeveloperDoc.ai Agentic Project, built with FastAPI and designed for scalable, maintainable AI-driven applications.

## Features
- FastAPI with enterprise folder structure
- Environment-based configuration (.env)
- Dockerized for production
- GitHub Actions for CI (lint, test)
- Ready for AI agentic logic and extension

## Folder Structure
```
backend/
  app/
    agents/         # AI agent orchestration
    api/            # API route definitions
    core/           # Core settings, config, startup
    models/         # Pydantic and DB models
    repositories/   # Data access layer
    schemas/        # Request/response schemas
    services/       # Business logic
    utils/          # Utility functions
    main.py         # FastAPI entrypoint
  configs/          # Configuration files
  scripts/          # Utility scripts
  tests/            # Unit/integration tests
  requirements.txt  # Python dependencies
  Dockerfile        # Multi-stage Docker build
  .env.example      # Example environment variables
```

## Quick Start

1. Copy `.env.example` to `.env` and fill in your secrets/configs.
2. Build and run with Docker:
   ```sh
   docker build -t developerdoc-backend ./backend
   docker run --env-file ./backend/.env -p 8000:8000 developerdoc-backend
   ```
3. Or run locally:
   ```sh
   cd backend
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

## Pre-commit Hooks (Pythonic)

This project uses [pre-commit](https://pre-commit.com/) for code quality and commit message checks.

### Setup (after cloning)

1. Install pre-commit:
   ```sh
   pip install pre-commit
   ```
2. Install hooks:
   ```sh
   pre-commit install --install-hooks
   pre-commit install --hook-type commit-msg
   ```

### Commit Workflow
- On commit, black and isort will check Python code formatting.
- On commit message, gitlint will validate the message format (supports Conventional Commits).

## CI/CD
- Automated linting and testing via GitHub Actions on every push/PR.

## License
MIT
