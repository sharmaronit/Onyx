# Repo Instructions

- The web backend must prefer the project `.venv` Python at `D:\dehradun\.venv\Scripts\python.exe` when launching simulation routes.
- The `/api/simulate` path depends on `gymnasium` and the shared Onyx ML stack from the root `requirements.txt`.
- If the backend is started with a system or conda Python that does not have those packages, `/api/simulate` can return a 500 even when the UI loads.
- Keep `web/backend/requirements.txt` aligned with the root requirements for any shared simulation dependencies.