# Local Development

This project already supports a clean local workflow:

- Production deploy uses `render.yaml` and `Procfile`.
- Local development uses SQLite automatically when `DATABASE_URL` is not set.
- Pushing to GitHub can continue to trigger deployment from your hosting provider.

## Run locally from PowerShell

From the project root:

```powershell
.\scripts\start-local.ps1
```

Then open:

```text
http://127.0.0.1:8000
```

The script:

- uses `.\.venv\Scripts\python.exe`
- sets `DEBUG=True` for local development
- keeps localhost allowed
- forces local SQLite with `USE_SQLITE_LOCAL=True`
- runs migrations before starting the server

## Useful options

Run on a different port:

```powershell
.\scripts\start-local.ps1 -Port 8080
```

Skip migrations:

```powershell
.\scripts\start-local.ps1 -SkipMigrate
```

Use the remote database from your environment instead of local SQLite:

```powershell
.\scripts\start-local.ps1 -UseRemoteDatabase
```

## Day-to-day workflow

1. Start the app locally with `.\scripts\start-local.ps1`.
2. Make your changes.
3. Test them in the browser on localhost.
4. Commit and push to GitHub.
5. Your deployed service can redeploy from the pushed branch if auto-deploy is enabled in your hosting setup.

## Manual commands

If you ever want to run the app without the helper script:

```powershell
$env:DEBUG="True"
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```
