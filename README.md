# CourseGrab

**Local web UI for downloading Coursera course materials.**

CourseGrab wraps [coursera-helper](https://github.com/coursera-helper/coursera-helper) with a browser-based interface — configure downloads, pick content types, and watch real-time progress in an embedded terminal.

![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

---

## Features

- **Video lectures** — download at 720p, 540p, 360p, or 240p
- **Subtitles & transcripts** — any language via ISO codes
- **Slides** — PDF and PPTX separately
- **Notebooks & quizzes** — Jupyter notebooks and quiz content
- **Parallel downloads** — 1 to 8 concurrent jobs
- **Real-time terminal** — color-coded log streaming via SSE
- **Persistent settings** — CAUTH, output dir, and language prefs saved in browser
- **Dark premium UI** — Stitch-designed interface with Manrope/Inter typography

## Requirements

- Python 3.9+
- [coursera-helper](https://github.com/coursera-helper/coursera-helper) (`pip install coursera-helper`)
- A valid Coursera account with active enrollment

## Installation

### From source

```bash
git clone https://github.com/jkrasuski/coursegrab.git
cd coursegrab
pip install -e .
```

### With pip (from GitHub)

```bash
pip install git+https://github.com/jkrasuski/coursegrab.git
```

## Quick Start

1. **Get your CAUTH cookie** — open browser DevTools on coursera.org, go to Application > Cookies, and copy the `CAUTH` value.

2. **Launch CourseGrab:**

   ```bash
   coursegrab
   ```

   This starts a local server at `http://127.0.0.1:8000` and opens your browser automatically.

3. **Paste the course URL**, enter your CAUTH, select content types, and click **Download Course**.

## Configuration

| Option             | Description                               | Default                |
| ------------------ | ----------------------------------------- | ---------------------- |
| Course URL         | Full Coursera course/lecture URL          | —                      |
| CAUTH Cookie       | Authentication token from browser cookies | —                      |
| Output Directory   | Where to save downloaded files            | `~/Downloads/coursera` |
| Video Quality      | Resolution: 720p, 540p, 360p, 240p        | 720p                   |
| Subtitle Languages | Comma-separated ISO codes (e.g. `en,pl`)  | `en,pl`                |
| Parallel Downloads | Concurrent download jobs (1-8)            | 4                      |

## Development

```bash
# Clone and install with dev dependencies
git clone https://github.com/jkrasuski/coursegrab.git
cd coursegrab
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run quality checks
black src/ tests/
ruff check --fix src/ tests/
mypy src/
pytest --cov=src --cov-report=term-missing
```

## Tech Stack

- **Backend:** FastAPI + Uvicorn
- **Frontend:** Tailwind CSS, Vanilla JS, Material Symbols
- **Download engine:** coursera-helper (subprocess)
- **Streaming:** Server-Sent Events (SSE)

## Legal Disclaimer

This tool is provided for **personal and educational use only**.

- **Not affiliated with or endorsed by Coursera, Inc.**
- Users are solely responsible for complying with [Coursera's Terms of Service](https://www.coursera.org/about/terms).
- Only download materials from courses you are actively enrolled in.
- Coursera is a registered trademark of Coursera, Inc.

## License

[MIT](LICENSE)
