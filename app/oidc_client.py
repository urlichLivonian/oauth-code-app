import json
import logging
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests


class OidcClientError(RuntimeError):
    """Raised when an OIDC provider API call fails."""


class OidcClient:
    def __init__(
        self,
        client_id: str,
        authorization_url: str,
        token_url: str,
        userinfo_url: str,
        redirect_uri: str,
        scope: str,
        logger: Optional[logging.Logger] = None,
        logout_url: Optional[str] = None,
        client_secret: Optional[str] = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.authorization_url = authorization_url
        self.token_url = token_url
        self.userinfo_url = userinfo_url
        self.redirect_uri = redirect_uri
        self.scope = scope
        self.logout_url = logout_url
        self.session = requests.Session()
        self.logger = logger or logging.getLogger("oauth_app.oidc")

    def build_authorization_url(self, state: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": self.scope,
            "state": state,
        }
        return f"{self.authorization_url}?{urlencode(params)}"

    def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "code": code,
            "redirect_uri": self.redirect_uri,
        }
        if self.client_secret:
            data["client_secret"] = self.client_secret
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        response = self._execute_request(
            method="POST",
            url=self.token_url,
            headers=headers,
            data=data,
        )
        try:
            return response.json()
        except ValueError as exc:
            raise OidcClientError("Failed to parse token response as JSON.") from exc

    def fetch_user_info(self, access_token: str) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        response = self._execute_request(
            method="GET",
            url=self.userinfo_url,
            headers=headers,
        )
        try:
            return response.json()
        except ValueError as exc:
            raise OidcClientError("Failed to parse userinfo response as JSON.") from exc

    def build_logout_url(
        self,
        post_logout_redirect_uri: str,
        id_token_hint: Optional[str] = None,
    ) -> Optional[str]:
        if not self.logout_url:
            return None
        params = {
            "client_id": self.client_id,
            "post_logout_redirect_uri": post_logout_redirect_uri,
        }
        if id_token_hint:
            params["id_token_hint"] = id_token_hint
        return f"{self.logout_url}?{urlencode(params)}"

    def _execute_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> requests.Response:
        safe_headers = headers or {}
        self.logger.info(
            "Sending request to IdP | method=%s url=%s headers=%s body=%s",
            method,
            url,
            self._sanitize_headers(safe_headers),
            self._format_body(data),
        )

        response = self.session.request(
            method=method,
            url=url,
            headers=headers,
            data=data,
            timeout=15,
        )

        self.logger.info(
            "Received response from IdP | status=%s headers=%s payload=%s",
            response.status_code,
            self._sanitize_headers(dict(response.headers)),
            self._format_body(self._safe_json(response)),
        )

        if response.ok:
            return response

        raise OidcClientError(
            f"OIDC provider request failed with status {response.status_code}: {response.text}"
        )

    @staticmethod
    def _sanitize_headers(headers: Dict[str, Any]) -> Dict[str, Any]:
        filtered = {}
        for key, value in headers.items():
            if key.lower() in {"authorization"} and isinstance(value, str):
                filtered[key] = "***REDACTED***"
            else:
                filtered[key] = value
        return filtered

    @staticmethod
    def _format_body(body: Optional[Any]) -> str:
        if body is None:
            return ""
        try:
            return json.dumps(body)
        except TypeError:
            return str(body)

    @staticmethod
    def _safe_json(response: requests.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return response.text
