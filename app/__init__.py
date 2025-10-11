import logging
import os
import secrets
from dataclasses import dataclass
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from flask import Flask, redirect, render_template, request, session, url_for

from .oidc_client import OidcClient, OidcClientError


@dataclass(frozen=True)
class Settings:
    client_id: str
    authorization_url: str
    token_url: str
    userinfo_url: str
    logout_url: Optional[str]
    app_base_url: str
    scope: str
    secret_key: str
    log_level: str


def load_settings() -> Settings:
    required_vars = {
        "OIDC_CLIENT_ID": os.getenv("OIDC_CLIENT_ID"),
        "OIDC_AUTH_URL": os.getenv("OIDC_AUTH_URL"),
        "OIDC_TOKEN_URL": os.getenv("OIDC_TOKEN_URL"),
        "OIDC_USERINFO_URL": os.getenv("OIDC_USERINFO_URL"),
        "APP_BASE_URL": os.getenv("APP_BASE_URL"),
    }

    missing = [name for name, value in required_vars.items() if not value]
    if missing:
        missing_vars = ", ".join(missing)
        raise RuntimeError(
            f"Missing required environment variables: {missing_vars}. "
            "Review your configuration or .env file."
        )

    logout_url = os.getenv("OIDC_LOGOUT_URL")

    scope = os.getenv("OIDC_SCOPE", "openid profile email")
    secret_key = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(16)
    log_level = os.getenv("APP_LOG_LEVEL", "INFO")

    return Settings(
        client_id=required_vars["OIDC_CLIENT_ID"],
        authorization_url=required_vars["OIDC_AUTH_URL"],
        token_url=required_vars["OIDC_TOKEN_URL"],
        userinfo_url=required_vars["OIDC_USERINFO_URL"],
        logout_url=logout_url,
        app_base_url=required_vars["APP_BASE_URL"],
        scope=scope,
        secret_key=secret_key,
        log_level=log_level,
    )


def configure_logging(level: str) -> logging.Logger:
    logger = logging.getLogger("oauth_app")
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level.upper())
    return logger


def create_app() -> Flask:
    load_dotenv(".env.local")
    load_dotenv()
    settings = load_settings()
    logger = configure_logging(settings.log_level)

    template_dir = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "templates")
    )
    app = Flask(__name__, template_folder=template_dir)
    app.config.update(
        SECRET_KEY=settings.secret_key,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )

    oidc_client = OidcClient(
        client_id=settings.client_id,
        authorization_url=settings.authorization_url,
        token_url=settings.token_url,
        userinfo_url=settings.userinfo_url,
        logout_url=settings.logout_url,
        redirect_uri=f"{settings.app_base_url.rstrip('/')}/callback",
        scope=settings.scope,
        logger=logger.getChild("oidc"),
    )

    @app.route("/")
    def index():
        tokens = session.get("tokens")
        user_info = session.get("user_info")
        return render_template(
            "home.html",
            tokens=tokens,
            user_info=user_info,
            authenticated=bool(tokens and user_info),
        )

    @app.route("/login")
    def login():
        state = secrets.token_urlsafe(16)
        session["oauth_state"] = state
        authorization_url = oidc_client.build_authorization_url(state=state)
        return redirect(authorization_url)

    @app.route("/callback")
    def callback():
        error = request.args.get("error")
        if error:
            return render_template("error.html", error=error)

        state = request.args.get("state")
        code = request.args.get("code")
        if not state or state != session.get("oauth_state"):
            return render_template(
                "error.html",
                error="State mismatch. Restart the authentication flow.",
            )

        if not code:
            return render_template(
                "error.html",
                error="Authorization code missing from the response.",
            )

        try:
            token_response = oidc_client.exchange_code_for_tokens(code)
        except OidcClientError as exc:
            return render_template("error.html", error=str(exc))

        session["tokens"] = token_response

        access_token = token_response.get("access_token")
        if not access_token:
            return render_template(
                "error.html",
                error="Access token missing in token response.",
            )

        try:
            user_info = oidc_client.fetch_user_info(access_token)
        except OidcClientError as exc:
            return render_template("error.html", error=str(exc))

        session["user_info"] = user_info
        session.pop("oauth_state", None)

        return redirect(url_for("index"))

    @app.route("/logout")
    def logout():
        post_logout_redirect = f"{settings.app_base_url.rstrip('/')}/"
        tokens = session.get("tokens") or {}
        id_token = tokens.get("id_token") if isinstance(tokens, dict) else None
        end_session_url = oidc_client.build_logout_url(
            post_logout_redirect_uri=post_logout_redirect,
            id_token_hint=id_token,
        )
        session.clear()
        if end_session_url:
            return redirect(end_session_url)
        return redirect(url_for("index"))

    @app.route("/health")
    def health() -> Dict[str, Any]:
        return {"status": "ok"}

    return app


app = create_app()
