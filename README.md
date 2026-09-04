<div align="center">

# 🧹 env-lint

**Catch broken .env files before they break production.**

[![CI](https://github.com/v01dst/env-lint/actions/workflows/ci.yml/badge.svg)](https://github.com/v01dst/env-lint/actions/workflows/ci.yml)
![License](https://img.shields.io/badge/license-MIT-8A2BE2)
![Python](https://img.shields.io/badge/python-3.14-3776AB?logo=python&logoColor=white)
![Deps](https://img.shields.io/badge/dependencies-stdlib%20only-00c853)
![Tests](https://img.shields.io/badge/tests-15%20passing-brightgreen)

`duplicate keys` · `bad syntax` · `weak secrets` · `.env.example diff` · `--strict`

</div>

---

## ✨ Features

- **🔍 Syntax checks** — missing `=`, invalid key chars, unterminated quotes, `export` prefix handled
- **🔁 Duplicate keys** — error with a pointer to the original line
- **🔐 Secrets hygiene** — flags short secrets and unquoted secrets with spaces
- **📎 Example diff** — `-e .env.example` finds vars missing from your env (and extras)
- **🚦 Cron/CI friendly** — exit 1 on errors, `--strict` also fails on warnings
- **🪶 Pure stdlib** — zero pip dependencies

## 🚀 Quick Start

```bash
git clone https://github.com/v01dst/env-lint
cd env-lint
python3 -m env_lint .env
```

Or with Docker:

```bash
docker build -t env-lint .
docker run --rm -v "$PWD:/work" env-lint -f /work/.env
```

## 📖 Usage

```
env-lint [-f FILE] [-e EXAMPLE] [--strict]
```

### Sample output

```
.env:2: warning: [weak-secret] 'API_KEY' looks like a secret but is shorter than 8 chars
.env:4: warning: [unquoted-secret] 'PASSWORD' contains spaces and is unquoted
.env:6: error: [duplicate-key] 'PORT' already defined on line 5
.env:7: error: [syntax] expected KEY=VALUE, got: OOPS
```

### CI usage

```bash
python3 -m env_lint -f .env -e .env.example --strict || exit 1
```

| Exit code | Meaning                     |
|-----------|------------------------------|
| `0`       | Clean (or warnings, no `--strict`) |
| `1`       | Errors (or warnings with `--strict`) |

## 🧱 Tech Stack

| Layer     | Tech                        |
|-----------|-----------------------------|
| Runtime   | Python ≥ 3.10 (stdlib only) |
| Testing   | unittest                    |
| Packaging | Docker                      |
| CI        | GitHub Actions              |

---

<div align="center">

Built with ⚡ by **v01dst**

[![GitHub](https://img.shields.io/badge/github-v01dst-181717?logo=github)](https://github.com/v01dst)
[![Discord](https://img.shields.io/badge/discord-9p.1-5865F2?logo=discord&logoColor=white)](https://discord.com/users/9p.1)

</div>
