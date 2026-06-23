# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

Recursively downloads a Confluence Cloud page hierarchy and converts it to local Markdown files, optimized for RAG pipelines. Output mirrors the Confluence hierarchy with YAML front matter and local image attachments.

## Running the Tool

### With Podman (recommended)

```bash
cp .env.template .env   # fill in credentials
./hande_project.sh build
./hande_project.sh start
```

### Directly with uv

```bash
uv run python export_confluence.py
```

Required env vars (set in `.env` or shell):

| Variable | Description |
|---|---|
| `CONFLUENCE_URL` | `https://company.atlassian.net` |
| `CONFLUENCE_USER` | email for auth |
| `CONFLUENCE_TOKEN` | Atlassian API token |
| `PARENT_PAGE_ID` | root page ID (from URL: `?pageId=...`) |

## Architecture

There are three script variants; `export_confluence.py` is the primary one:

| Script | Output format |
|---|---|
| `export_confluence.py` | Markdown + YAML front matter + local attachments (RAG-optimized) |
| `export_confluence-html.py` | Raw HTML with `index.html` wrappers |
| `export_confluence_pdf.py` | Plain Markdown, no attachments |

**Data flow in `export_confluence.py`:**

1. Auth via `atlassian-python-api` (`Confluence` class)
2. Recursive page fetch via `get_page_child_by_type()`
3. HTML cleaning with BeautifulSoup (removes scripts/nav/footer, preserves tables)
4. Image attachments downloaded to `./attachments/` and re-linked
5. HTML → Markdown via `markdownify`; tables kept as raw HTML for RAG fidelity
6. YAML front matter injected (`title`, `page_id`, `source`)
7. Written to `output/<Page Title>/index.md`

**Output structure:**

```
output/
└── Root Page/
    ├── index.md
    ├── attachments/
    └── Child Page/
        ├── index.md
        └── attachments/
```

## Container Management (`hande_project.sh`)

```bash
./hande_project.sh build        # build image
./hande_project.sh start        # run download
./hande_project.sh shell        # interactive shell in container
./hande_project.sh logs         # follow logs
./hande_project.sh clean all    # remove containers, images, volumes
./hande_project.sh status       # show current state
```

## Dependencies

`requirements.txt`: `atlassian-python-api`, `beautifulsoup4`, `markdownify`, `urllib3`

SSL verification is disabled globally in the scripts (`verify=False`). This is intentional for internal Confluence instances.
