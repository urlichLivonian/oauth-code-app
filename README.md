# OAuth Code App

Flask 3.0 example that demonstrates the Authorization Code grant flow against a generic OpenID Connect (OIDC) Identity Provider.
The application traces every interaction with the IdP to the console so you can inspect requests, headers, and payloads in real time. While the sample was validated with Keycloak, it is not tied to any specific provider.

## Features

- Authorization Code flow with state validation and token exchange.
- User profile retrieval through the IdP UserInfo endpoint.
- Structured console logging for every IdP request and response.
- Configurable through environment variables only—no external URLs are hard-coded.
- Docker Compose setup for local validation and demo environments.

## Prerequisites

- Python 3.12 (recommended to install via [pyenv](https://github.com/pyenv/pyenv) or the official installer).
- Access to an OIDC-compliant Identity Provider with a public client that supports the Authorization Code flow.
- Docker & Docker Compose (for containerised workflows).

## Configuration

Create a `.env.local` file (ignored by Git) with the settings from your Identity Provider:

```bash
cat <<'EOF' > .env.local
FLASK_SECRET_KEY=replace-with-secret
APP_LOG_LEVEL=INFO
APP_BASE_URL=http://localhost:5000
OIDC_CLIENT_ID=your-public-client-id
OIDC_AUTH_URL=https://idp.example.com/oauth2/v1/authorize
OIDC_TOKEN_URL=https://idp.example.com/oauth2/v1/token
OIDC_USERINFO_URL=https://idp.example.com/oauth2/v1/userinfo
OIDC_LOGOUT_URL=https://idp.example.com/oauth2/v1/logout
OIDC_SCOPE=openid profile email
EOF
```

| Variable            | Description                                                                                                        |
| ------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `FLASK_SECRET_KEY`  | Secret key for Flask sessions. Generate a unique random value.                                                     |
| `APP_LOG_LEVEL`     | Log level for the application (e.g. `INFO`, `DEBUG`).                                                              |
| `APP_BASE_URL`      | External URL of the Flask app (e.g. `http://localhost:5000`). Must match the redirect URI registered with the IdP. |
| `OIDC_CLIENT_ID`    | Public OAuth client ID configured in your IdP.                                                                     |
| `OIDC_AUTH_URL`     | OIDC authorization endpoint URL.                                                                                   |
| `OIDC_TOKEN_URL`    | OIDC token endpoint URL.                                                                                           |
| `OIDC_USERINFO_URL` | OIDC UserInfo endpoint URL.                                                                                        |
| `OIDC_LOGOUT_URL`   | (Optional) OIDC end-session endpoint URL.                                                                          |
| `OIDC_SCOPE`        | OAuth scopes requested during login (defaults to `openid profile email`).                                          |

> **Important:** Register `APP_BASE_URL/callback` and (optionally) `APP_BASE_URL/` as valid redirect URIs in your provider's client configuration.

### Note for external contributors

Forks and clones never receive IdP endpoints or credentials through the repository. Create your own `.env.local` (using the snippet above as a template) and keep it private—every file ending with `.local` is ignored by Git automatically.

## Running Locally (Python)

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Launch the development server (the app reads configuration from `.env.local` automatically):

   ```bash
   flask --app wsgi:app run --port 5000
   ```

4. Browse to `http://localhost:5000` and follow the login link.

Console logs show outbound requests, headers, and payloads exchanged with your IdP. Use `APP_LOG_LEVEL=DEBUG` to see verbose Flask routing logs.

## Running with Docker Compose

1. Ensure the `.env.local` file is populated.
2. Build and start the service:

   ```bash
   docker compose up --build
   ```

   > **macOS tip:** If you receive `bind: address already in use` for port `5000`, Control Center may have reserved it while AirDrop receiving is enabled. Open Control Center → AirDrop and temporarily set *Receiving* to *Off*, start the container, then re-enable AirDrop after your test run.

3. Visit `http://localhost:5000` to initiate the Authorization Code flow.

To stop the stack, press `Ctrl+C` or run:

```bash
docker compose down
```

## Code Quality Checks

Install [pipx](https://pipx.pypa.io/stable/installation/) if it is not already available, then set up the provided pre-commit hooks:

1. Ensure `pipx` is on your `PATH`:

   ```bash
   python3 -m pip install --user pipx
   python3 -m pipx ensurepath
   ```

2. Install `pre-commit` via pipx:

   ```bash
   pipx install pre-commit
   ```

3. Install the Git hooks and run them once across the repo:

   ```bash
   pre-commit install
   pre-commit run --all-files
   ```

The configured hooks apply formatting (`black`, `isort`), linting (`ruff`), static analysis (`mypy --strict`), and security checks (`bandit`). Running `pre-commit run --all-files` before pushing helps catch issues early. You can optionally install other tools (e.g., `pipx install black`) if you prefer running them manually outside of pre-commit.

## IDE Guidance

- **Visual Studio Code**
  1. Install the official *Python* extension.
  2. Open the repository folder.
  3. Select the created virtual environment (`.venv`) as the Python interpreter.
  4. Add the `.env.local` file path in `.vscode/settings.json` using `"python.envFile": "${workspaceFolder}/.env.local"` for automatic variable loading.

- **JetBrains PyCharm**
  1. Open the project directory.
  2. Set the Python interpreter to the `.venv` folder or configure a Docker Compose interpreter that points to the `app` service.
  3. Add an *Environment variables* entry for your `.env.local` file, or mark the file under *Run/Debug Configurations → EnvFile*.

Both IDEs provide built-in HTTP logging consoles where you can observe the structured logs emitted by the Flask service.

## Observing IdP Interactions

During the login flow the application logs entries similar to:

```
2024-05-01 12:00:00 - oauth_app.oidc - INFO - Sending request to IdP | method=POST url=https://idp.example.com/... headers={'Content-Type': 'application/x-www-form-urlencoded'} body={"grant_type": "authorization_code", ...}
2024-05-01 12:00:00 - oauth_app.oidc - INFO - Received response from IdP | status=200 headers={...} payload={"access_token": "...", "refresh_token": "..."}
```

These logs provide full visibility into how the client and the IdP exchange information, making the setup suitable for debugging or demonstrations.

> **Security note:** Request and response logs contain sensitive tokens and secrets. Never enable this level of logging in production environments.

## Project Structure

```
.
├── app
│   ├── __init__.py
│   └── oidc_client.py
├── templates
│   ├── error.html
│   └── home.html
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── wsgi.py
```

.env.local is intentionally excluded from source control—create it locally when configuring the app.

## Next Steps

- Add automated tests that mock IdP responses for CI pipelines.
- Extend the UI to display additional claims or downstream API calls protected by the obtained access token.
