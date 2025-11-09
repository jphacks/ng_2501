# Repository Guidelines

## Project Structure & Module Organization
- `front/` — Next.js 15 / React 19 app. `src/app` hosts routes + server actions, `src/features` holds domain logic, `public/` keeps static assets.
- `back/` — FastAPI + LangGraph agents. `app/main.py` entry, `service/` (agent orchestration), `tools/` (linter, diff patcher, security), `model/` (Pydantic schemas), artifacts in `media/`.
- `docker-compose.yml` runs the API, frontend, Postgres, nginx, certbot; nginx configs live in `nginx/`, TLS steps are described in `HTTPS_SETUP.md`.

## Build, Test, and Development Commands
- Frontend: `cd front && pnpm install`, `pnpm dev` for Turbopack dev server, `pnpm build && pnpm start` for production check, `pnpm lint` / `pnpm lint:fix` for Biome.
- Backend: `cd back && uv sync`, `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000`. Quality gates: `uv run ruff check app`, `uv run pyright app`, `uv run mypy app`.
- Full stack: `docker compose up --build` (requires `.env` and certs under `certbot/`).

## Coding Style & Naming Conventions
- TypeScript: Biome enforces 4-space indent, 100-char lines, single quotes for JS and double quotes for JSX. Use `PascalCase` components, `camelCase` hooks/utilities, colocate Tailwind helpers with their component.
- Python: keep modules/functions `snake_case`, classes `PascalCase`, annotate everything with types, and log via `loguru` without exposing secrets. Keep agent state machines pure to make diff-based updates easier.

## Testing Guidelines
- Backend tests use `unittest` (see `back/app/tools/video_data/video_db_test.py`). Mirror that shape, name files `*_test.py`, run `uv run python -m unittest discover app`, and remove temporary SQLite or media artifacts in `tearDown`.
- Frontend automated tests are not wired yet; when touching UI logic add Vitest/Jest specs under `front/src/__tests__` and record manual verification steps (screenshots or clips) in the PR until CI lands.
- Always add regression coverage for new agent tools, RAG utilities, and database helpers.

## Commit & Pull Request Guidelines
- Commits are short, imperative, and descriptive (`ビルド時に環境変数を渡す`, `タイムアウト設定を長時間にした`); prefix `front:` or `back:` when a change spans both.
- PRs should explain scope and intent, link tracking issues, and list validation commands (`pnpm lint`, `uv run python -m unittest ...`, manual QA). Include screenshots for UI-visible work.

## Security & Configuration Tips
- Keep secrets out of git; load them from `.env`, Docker `environment`, or your deployment secret manager, and rotate Gemini/Google keys shared in `back/prompts/**`.
- Only run `init-letsencrypt.sh` on hosts that can solve ACME challenges; nginx mounts the resulting certs from `certbot/`.
