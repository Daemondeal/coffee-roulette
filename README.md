# Coffee Roulette

Website for tracking Coffee Roulette standings, mostly for personal use.

Somewhat vibe coded.

## Running the app

The project requires Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).
From the repository root, run:

```console
uv run run-app
```

`uv` installs the project's dependencies and starts the Flask development server at
<http://127.0.0.1:5000>. The SQLite database is created automatically at
`.data/database.db` unless `PATH_DB` is configured.

The server runs in Flask debug mode and is intended for local development, not for
direct use as a production server.

## Configuration

At startup, the app loads environment variables from a `.env` file in the repository
root. Values already present in the process environment take precedence. A local
development configuration can look like this:

```dotenv
PASSWORD=choose-a-login-password
SECRET_KEY=generate-a-long-random-value
SESSION_COOKIE_SECURE=false
SESSION_COOKIE_SAMESITE=Lax
PATH_DB=.data/database.db
LOG_LEVEL=INFO
PERCENTILE_EFFORT=100000
SLACK_HOOK_LINK=
```

The supported options are:

| Variable | Default | Purpose |
| --- | --- | --- |
| `PASSWORD` | Empty | Password used to access actions that modify or download data. Set this to a non-empty value. |
| `SECRET_KEY` | `dev_secret_key` | Signs Flask session cookies. Use a long, random, stable value anywhere beyond disposable local development; changing it logs out existing sessions. |
| `SESSION_COOKIE_SECURE` | `true` | Whether browsers may send the session cookie only over HTTPS. Accepted true values are `1`, `true`, `yes`, and `on` (case-insensitive); every other value is false. Set it to `false` when using the local HTTP server. |
| `SESSION_COOKIE_SAMESITE` | `Lax` | Flask's `SameSite` policy for the session cookie, normally `Lax`, `Strict`, or `None`. `None` should be used only with secure HTTPS cookies. |
| `PATH_DB` | `.data/database.db` | Path to the SQLite database. Relative paths are resolved from the directory where the app is started. The database and its schema are initialized automatically. |
| `LOG_LEVEL` | `WARNING` | Python logging level for the Flask app, such as `DEBUG`, `INFO`, `WARNING`, or `ERROR`. |
| `PERCENTILE_EFFORT` | `100000` | Number of random simulations used for percentile calculations. It must be a positive integer; larger values cost more CPU time and memory. |
| `SLACK_HOOK_LINK` | Empty | Slack webhook URL notified after a new coffee extraction. Leave it empty to disable notifications. |

Do not commit `.env`: it can contain the login password, session secret, and Slack
webhook credentials, and is excluded by `.gitignore`.
