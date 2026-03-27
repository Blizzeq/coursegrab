<div align="center">

# CourseGrab

**Download Coursera course materials through a sleek web interface.**

Grab videos, subtitles, slides, notebooks, and quizzes — all from your browser.

[![Live Demo](https://img.shields.io/badge/Live_Demo-coursera--downloader.vercel.app-316ee9?style=for-the-badge&logo=vercel&logoColor=white)](https://coursera-downloader.vercel.app/)

[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-blue?style=flat-square)](https://python.org)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Deployed on Vercel](https://img.shields.io/badge/deployed_on-Vercel-000?style=flat-square&logo=vercel)](https://coursera-downloader.vercel.app/)

</div>

---

## Hosted vs Local

CourseGrab runs in two modes. The app auto-detects which one it's in.

| | **Hosted (Vercel)** | **Local** |
|---|---|---|
| Video downloads | Not available (512MB disk limit) | Full support, all resolutions |
| Subtitles, slides, notebooks | Yes (ZIP download) | Yes (saved to disk) |
| Parallel downloads | Sequential (1 job) | 8 concurrent jobs |
| Output | ZIP file via browser | Direct to chosen folder |
| Folder picker | N/A | Native OS dialog |

**For full course downloads with videos, use the local version.**

## Quick Start (Hosted)

1. Open **[coursera-downloader.vercel.app](https://coursera-downloader.vercel.app/)**
2. Get your CAUTH cookie:
   - Log in to [coursera.org](https://coursera.org)
   - Open DevTools (`F12` / `Cmd+Opt+I`)
   - Go to **Application** > **Cookies** > `coursera.org`
   - Copy the **CAUTH** value
3. Paste the course URL, enter CAUTH, select content types, and click **Download Course**
4. A ZIP file will download automatically when done

> Best for: subtitles, transcripts, slides (PDF/PPTX), notebooks.

## Local Setup

```bash
pip install git+https://github.com/Blizzeq/coursegrab.git
coursegrab
```

Opens `http://127.0.0.1:8000` in your browser. No disk limits, full video support, 8x parallel downloads.

<details>
<summary><strong>From source (development)</strong></summary>

```bash
git clone https://github.com/Blizzeq/coursegrab.git
cd coursegrab
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run quality checks
black src/ tests/
ruff check --fix src/ tests/
mypy src/
pytest --cov=src --cov-report=term-missing
```

</details>

## Features

| Feature | Description |
|---|---|
| Video Lectures | 720p, 540p, 360p, 240p (local only) |
| Subtitles & Transcripts | Any language via ISO codes |
| Slides | PDF and PPTX formats |
| Notebooks & Quizzes | Jupyter notebooks and quiz content |
| Real-time Terminal | Color-coded log streaming via SSE |
| Persistent Settings | CAUTH, output dir, and prefs saved in browser |

## Configuration

| Option | Description | Default |
|---|---|---|
| Course URL | Full Coursera course/lecture URL | — |
| CAUTH Cookie | Auth token from browser cookies | — |
| Output Directory | Where to save files (local only) | `~/Downloads/coursera` |
| Video Quality | 720p / 540p / 360p / 240p | `720p` |
| Subtitle Languages | Comma-separated ISO codes | `en,pl` |

## Tech Stack

**Backend:** FastAPI + Uvicorn | **Frontend:** Tailwind CSS + Vanilla JS | **Streaming:** SSE | **Engine:** [coursera-helper](https://github.com/coursera-helper/coursera-helper) | **Hosting:** Vercel

## Legal Disclaimer

This tool is provided for **personal and educational use only**. Not affiliated with or endorsed by Coursera, Inc. Users must comply with [Coursera's Terms of Service](https://www.coursera.org/about/terms). Only download materials from courses you are actively enrolled in.

## License

[MIT](LICENSE)
