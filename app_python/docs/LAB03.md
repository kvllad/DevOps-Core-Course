# Lab 3 — CI/CD (Python + Bonus Go)

## 1. Overview
- **Testing framework**: `pytest` + `pytest-cov`.
  - Why: concise syntax, good fixtures, simple coverage integration, strong ecosystem.
- **Tests covered**:
  - `GET /` checks response structure and required fields.
  - `GET /health` checks status + timestamp + uptime.
  - `GET /does-not-exist` verifies 404 error handler.
- **CI trigger strategy**:
  - Python workflow runs only when `app_python/**` or `.github/workflows/python-ci.yml` changes.
  - Go workflow runs only when `app_go/**` or `.github/workflows/go-ci.yml` changes.
- **Versioning strategy**: **CalVer** (`YYYY.MM.DD`).
  - Why: this is a service, releases are time-based, and CalVer is simple for CI automation.
  - Docker tags: `YYYY.MM.DD` + `latest`.

## 2. Workflow Evidence
**Local test run**
```
vladkuznetsov@MacBook-Air-5 DevOps-Core-Course % PYTHONPATH=app_python pytest -c app_python/pytest.ini
=================================================================================================================== test session starts ===================================================================================================================
platform darwin -- Python 3.11.9, pytest-8.3.3, pluggy-1.6.0
rootdir: /Users/vladkuznetsov/inno/DevOps-Core-Course/app_python
configfile: pytest.ini
plugins: anyio-4.12.1, cov-5.0.0
collected 3 items                                                                                                                                                                                                                                         

app_python/tests/test_app.py ...                                                                                                                                                                                                                    [100%]

---------- coverage: platform darwin, python 3.11.9-final-0 ----------
Name                Stmts   Miss  Cover   Missing
-------------------------------------------------
app_python/app.py      49      4    92%   124, 134-137
-------------------------------------------------
TOTAL                  49      4    92%
Coverage XML written to file coverage.xml

Required test coverage of 70% reached. Total coverage: 91.84%

==================================================================================================================== 3 passed in 0.26s ====================================================================================================================
```

**Workflow run link**
- https://github.com/kvllad/DevOps-Core-Course/actions/runs/21797773596

**Docker Hub image (Python)**
- `https://hub.docker.com/r/vladk6813050/devops-info-service-py`

**CI test evidence**
- Python 3.12: `3 passed in 1.26s`, coverage `91.84%`
- Python 3.13: `3 passed in 0.60s`, coverage `91.84%`

**Status badge**
- Python CI badge added to `app_python/README.md`.
- Coverage badge added to `app_python/README.md` (Codecov).

## 3. Best Practices Implemented
- **Dependency caching**: `actions/setup-python` with pip cache keyed by requirements files to speed installs.
- **Job dependencies**: Docker build job runs only after tests pass (`needs: test`).
- **Conditional deploy**: Docker push only on `master` branch pushes (not on PRs).
- **Matrix testing**: Python 3.12 and 3.13 to catch version-specific issues early.
- **Concurrency control**: cancel in-progress runs for same branch to save CI time.
- **Least privilege**: workflow permissions limited to `contents: read`.

**Caching speed improvement**
- First run (cache miss): `pip cache is not found`
- Cache saved: `Cache saved with the key: setup-python-Linux-x64-24.04-Ubuntu-python-3.12.12-pip-5e39d1e1ee6ff5df7fe2edacb44905b46ff4830f6fb663e88586ce2c46fce07d`
- Next run should show cache hit and faster install.

**Snyk scan**
- Integrated via `snyk/actions/python`.
- Result: `✔ Tested /github/workspace for known issues, no vulnerable paths found.`

## 4. Key Decisions
- **Versioning**: CalVer because the service is released continuously and doesn’t need SemVer semantics.
- **Docker tags**: `YYYY.MM.DD` for traceability + `latest` for convenience.
- **Workflow triggers**: path-based filters to avoid unnecessary CI for unrelated changes.
- **Coverage**: `pytest-cov` with a 70% minimum threshold (`pytest.ini`). Current coverage: **91.84%**.

## 5. Bonus — Multi-App CI + Coverage
- **Second workflow**: `.github/workflows/go-ci.yml` for the Go app.
  - Steps: lint (`golangci-lint`), `go test`, Docker build & push.
  - Uses the same CalVer tags and `latest`.
- **Path filters**: Python and Go workflows only run when their respective folders change.
- **Coverage tracking**: `pytest-cov` generates `coverage.xml`, uploaded to Codecov in CI.
- Coverage badge added to README.
- Current coverage (local): **91.84%**.
- Codecov upload (CI): https://app.codecov.io/github/kvllad/devops-core-course/commit/f6009e758c6aec3273e7401b9de02af028613340

## 6. Challenges
- **No internet in this environment**: pip could not download dependencies here, so tests were run on the host machine and output is recorded above.

## Secrets Required (GitHub)
Add these repository secrets before the workflow can publish images and run scans:
- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`
- `SNYK_TOKEN` (optional but required to run Snyk scan)
- `CODECOV_TOKEN` (optional; required if Codecov needs token for your repo)
