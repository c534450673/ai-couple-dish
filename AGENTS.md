<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **ai-couple-dish** (10301 symbols, 24400 relationships, 300 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## When Debugging

1. `gitnexus_query({query: "<error or symptom>"})` — find execution flows related to the issue
2. `gitnexus_context({name: "<suspect function>"})` — see all callers, callees, and process participation
3. `READ gitnexus://repo/ai-couple-dish/process/{processName}` — trace the full execution flow step by step
4. For regressions: `gitnexus_detect_changes({scope: "compare", base_ref: "main"})` — see what your branch changed

## When Refactoring

- **Renaming**: MUST use `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` first. Review the preview — graph edits are safe, text_search edits need manual review. Then run with `dry_run: false`.
- **Extracting/Splitting**: MUST run `gitnexus_context({name: "target"})` to see all incoming/outgoing refs, then `gitnexus_impact({target: "target", direction: "upstream"})` to find all external callers before moving code.
- After any refactor: run `gitnexus_detect_changes({scope: "all"})` to verify only expected files changed.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Tools Quick Reference

| Tool | When to use | Command |
|------|-------------|---------|
| `query` | Find code by concept | `gitnexus_query({query: "auth validation"})` |
| `context` | 360-degree view of one symbol | `gitnexus_context({name: "validateUser"})` |
| `impact` | Blast radius before editing | `gitnexus_impact({target: "X", direction: "upstream"})` |
| `detect_changes` | Pre-commit scope check | `gitnexus_detect_changes({scope: "staged"})` |
| `rename` | Safe multi-file rename | `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` |
| `cypher` | Custom graph queries | `gitnexus_cypher({query: "MATCH ..."})` |

## Impact Risk Levels

| Depth | Meaning | Action |
|-------|---------|--------|
| d=1 | WILL BREAK — direct callers/importers | MUST update these |
| d=2 | LIKELY AFFECTED — indirect deps | Should test |
| d=3 | MAY NEED TESTING — transitive | Test if critical path |

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/ai-couple-dish/context` | Codebase overview, check index freshness |
| `gitnexus://repo/ai-couple-dish/clusters` | All functional areas |
| `gitnexus://repo/ai-couple-dish/processes` | All execution flows |
| `gitnexus://repo/ai-couple-dish/process/{name}` | Step-by-step execution trace |

## Self-Check Before Finishing

Before completing any code modification task, verify:
1. `gitnexus_impact` was run for all modified symbols
2. No HIGH/CRITICAL risk warnings were ignored
3. `gitnexus_detect_changes()` confirms changes match expected scope
4. All d=1 (WILL BREAK) dependents were updated

## Keeping the Index Fresh

After committing code changes, the GitNexus index becomes stale. Re-run analyze to update it:

```bash
npx gitnexus analyze
```

If the index previously included embeddings, preserve them by adding `--embeddings`:

```bash
npx gitnexus analyze --embeddings
```

To check whether embeddings exist, inspect `.gitnexus/meta.json` — the `stats.embeddings` field shows the count (0 means no embeddings). **Running analyze without `--embeddings` will delete any previously generated embeddings.**

> Claude Code users: A PostToolUse hook handles this automatically after `git commit` and `git merge`.

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->

## Cursor Cloud specific instructions

Stack: Spring Boot 2.7 backend (`backend/`, Maven) + Vue 3/Vite H5 client (`frontend-h5/`), with MySQL 8 and Redis. Standard commands live in `README.md` and `docs/ENVIRONMENT.md`; the notes below are the non-obvious caveats discovered while setting up the cloud environment.

### Services (must be started each session; not auto-started)
- MySQL 8: `sudo service mysql start` — listens on `127.0.0.1:3306`, root password is `root123` (TCP only; the unix socket is not accessible, so always connect with `-h 127.0.0.1`). Database `ai_couple_dish` is already loaded.
- Redis: `sudo service redis-server start` — `127.0.0.1:6379`, no password.
- Use **Java 17** (already the default `java`/alternatives). Spring Boot 2.7 does not target the also-installed Java 21.

### Run the backend
The app reads config from **environment variables** (not from `.env` files). From `backend/`, the `local` profile points at `127.0.0.1` and auto-creates the DB:
```
JWT_SECRET="dev_local_jwt_secret_key_that_is_at_least_64_characters_long_for_hs512_algorithm_ok_1234567890" \
DB_HOST=127.0.0.1 DB_PORT=3306 DB_NAME=ai_couple_dish DB_USERNAME=root DB_PASSWORD=root123 \
REDIS_HOST=127.0.0.1 REDIS_PORT=6379 SPRING_PROFILES_ACTIVE=local FILE_UPLOAD_PATH=/tmp/uploads \
mvn spring-boot:run
```
`JWT_SECRET` is mandatory (HS512 needs ≥64 chars) or startup fails. API base is `http://localhost:8080/api`; Knife4j docs at `/api/doc.html`.

### Backend tests (`mvn test`)
Most tests use H2 + embedded Redis, but `BugFixVerificationTest` is a plain `@SpringBootTest` that hits the **real MySQL** (default/dev profile). Run with `JWT_SECRET` and the `DB_*`/`REDIS_*` env vars above set, otherwise those 8 tests fail. All 617 tests pass when MySQL/Redis are up and the schema matches the models.

### Database schema caveat
The repo's SQL files have drifted from the entity models. `backend/src/main/resources/schema.sql` and `sql/init.sql` are **incomplete** (e.g. missing `t_anniversary.is_lunar_date`). The schema that matches the models is `backend/src/test/resources/schema-test.sql` (37 tables), but it is H2 syntax. To (re)load MySQL:
```
sed -E 's/CREATE (UNIQUE )?INDEX IF NOT EXISTS/CREATE \1INDEX/g' backend/src/test/resources/schema-test.sql > /tmp/mysql-schema.sql
mysql -uroot -proot123 -h127.0.0.1 -e "DROP DATABASE IF EXISTS ai_couple_dish; CREATE DATABASE ai_couple_dish CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -uroot -proot123 -h127.0.0.1 ai_couple_dish < /tmp/mysql-schema.sql
```

### Frontend H5 (`frontend-h5/`)
Run with `npm run dev` (port 3000). It is configured via the gitignored `frontend-h5/.env.development.local`, which sets `VITE_API_BASE_URL` **empty** so axios uses the relative `/api` and goes through the Vite dev proxy (same-origin → `http://localhost:8080`). Do NOT point the browser client directly at `http://localhost:8080/api`: the backend `AuthInterceptor` does not skip CORS `OPTIONS` preflight requests and returns **HTTP 500**, so all cross-origin browser calls fail. If that `.local` file is missing, recreate it with `VITE_API_BASE_URL=` (one line).

### Auth quirks (pre-existing app bugs, do not "fix" as setup)
- WeChat login `POST /api/user/login` works without any WeChat backend: it treats the request `code` as the openid and auto-registers the user. This is the easiest way to mint a real JWT for testing.
- The H5 phone login UI is broken for new users: it calls `POST /api/user/register`, which is **not** in the interceptor whitelist (`WebConfig`), so it 401s. Phone verify codes (for `/user/sendCode` → `/user/phoneLogin`) are stored in Redis at `user:verify:code:<phone>` (not logged). To get a logged-in browser session, seed `localStorage` `token`/`userInfo` from a `/api/user/login` response.
- Most feature endpoints (menu, etc.) require the user to be in a bound couple (`generateCode` on one account, `bind` from the other) or they return code `2006 未绑定情侣关系`.

### Known non-blocking failures
- `npm run lint` reports 5 pre-existing errors (`no-useless-catch`, `afterEach is not defined`).
- Frontend `vitest` has ~34 pre-existing failing tests (broken test setup/mocks).
