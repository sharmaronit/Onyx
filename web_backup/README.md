# Onyx React Command Layer

React + Vite frontend connected to a Python FastAPI backend that runs the same core analysis functions used by the Streamlit app.

## Features

- Network Map page with live topology and CVE tables.
- Interactive network graph using vis-network, including edge width emphasis after simulation runs.
- Attack Analysis page with real simulation and patch optimizer calls.
- Chart cards for edge frequency, CVSS-vs-simulation rank divergence, and MARL trend lines.
- Red vs Blue page with MARL results.
- Report page with generated morning report preview.
- Toast notifications and per-action progress bars for long-running operations.

## Start Full Dev Stack (Recommended)

From this `web` folder:

1. Ensure Python deps are installed once:

   pip install -r backend/requirements.txt

2. Install frontend deps:

   npm install

3. Start backend + frontend together:

   npm run dev

This starts:
- FastAPI backend at http://127.0.0.1:8020
- Vite frontend at http://localhost:5183

If Python is not on your PATH, set the interpreter explicitly:

```powershell
$env:BACKEND_PYTHON="d:/Ronit Sharma/vs code/ML Models/.conda/python.exe"
npm run dev
```

## Start Components Individually

From this `web` folder:

- Backend only:

  npm run dev:backend

- Frontend only:

  npm run dev:frontend

The Vite dev server proxies `/api` requests to `http://localhost:8020`.

## Build

npm run build
npm run preview
