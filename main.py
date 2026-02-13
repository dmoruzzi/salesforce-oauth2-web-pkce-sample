import requests
import webbrowser
import urllib.parse
import hashlib
import base64
import os
import json
import datetime
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Tuple, Optional, Dict, Any

INSTANCE: str = "https://sample-dev-ed.trailblaze.my.salesforce.com"
KEY: str = '3MVG9JJwBBbcN47K5GDwV5CMZb7YPOak6qFo8qEU0AWObcE2yBbhJtF0v18keWmZHcFkED7b3vso3NU46NIjo'
SEC: str = '99FBD74CEE363E817535EA8B13BFD11EF6AU04YSPTQS27RHFDV9MJEMPQDECKIP'

LOG_FILE: str = "oauth_trace.log"
CB: str = 'http://localhost:8000/callback'


# --------------------------------------------------
# Logging Helper
# --------------------------------------------------
def log(title: str, data: Optional[Any] = None) -> None:
    timestamp: str = datetime.datetime.now(datetime.UTC).isoformat()
    entry: Dict[str, Any] = {"timestamp_utc": timestamp, "event": title, "data": data}

    print("\n" + "=" * 80)
    print(f"[{timestamp}] {title}")
    if data is not None:
        if isinstance(data, (dict, list)):
            print(json.dumps(data, indent=2))
        else:
            print(data)
    print("=" * 80)

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, indent=2))
        f.write("\n\n")
        f.flush()
        os.fsync(f.fileno())


# --------------------------------------------------
# PKCE Generation
# --------------------------------------------------
def generate_pkce() -> Tuple[str, str]:
    raw_random: bytes = os.urandom(40)
    code_verifier: str = base64.urlsafe_b64encode(raw_random).decode().rstrip("=")
    sha256_digest: bytes = hashlib.sha256(code_verifier.encode()).digest()
    code_challenge: str = base64.urlsafe_b64encode(sha256_digest).decode().rstrip("=")

    log("PKCE_GENERATED", {
        "raw_random_bytes_hex": raw_random.hex(),
        "code_verifier": code_verifier,
        "sha256_digest_hex": sha256_digest.hex(),
        "code_challenge": code_challenge,
        "challenge_method": "S256"
    })

    return code_verifier, code_challenge


# --------------------------------------------------
# Authorization URL Build
# --------------------------------------------------
def build_auth_url(code_challenge: str, redirect_uri: str) -> str:
    params: Dict[str, str] = {
        "client_id": KEY,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "code_challenge": code_challenge,
        "code_challenge_method": "S256"
    }

    encoded_query: str = urllib.parse.urlencode(params)
    auth_url: str = f"{INSTANCE}/services/oauth2/authorize?{encoded_query}"

    log("AUTH_URL_BUILT", {
        "base_url": f"{INSTANCE}/services/oauth2/authorize",
        "query_params": params,
        "encoded_query": encoded_query,
        "final_auth_url": auth_url
    })

    return auth_url


# --------------------------------------------------
# Token Exchange
# --------------------------------------------------
def exchange_code_for_token(code: str, code_verifier: str, redirect_uri: str) -> Dict[str, Any]:
    token_url: str = f"{INSTANCE}/services/oauth2/token"
    data: Dict[str, str] = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": KEY,
        "redirect_uri": redirect_uri,
        "code_verifier": code_verifier
    }

    if SEC:
        data["client_secret"] = SEC

    log("TOKEN_REQUEST_PREPARED", {"token_url": token_url, "form_payload": data})

    response: requests.Response = requests.post(token_url, data=data)
    log("TOKEN_RESPONSE_RECEIVED", {
        "status_code": response.status_code,
        "response_headers": dict(response.headers),
        "raw_body": response.text
    })

    response.raise_for_status()
    parsed: Dict[str, Any] = response.json()
    log("TOKEN_RESPONSE_PARSED", parsed)
    return parsed


# --------------------------------------------------
# Callback HTTP Server (Threaded)
# --------------------------------------------------
def start_callback_server(code_verifier: str, redirect_uri: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    result_container: Dict[str, Any] = {}

    parsed_cb = urllib.parse.urlparse(redirect_uri)
    hostname = parsed_cb.hostname or "localhost"
    port = parsed_cb.port or 80
    callback_path = parsed_cb.path

    log("CALLBACK_SERVER_CONFIG", {"hostname": hostname, "port": port, "path": callback_path})

    def handler_factory() -> type[BaseHTTPRequestHandler]:
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                nonlocal result_container
                log("CALLBACK_RAW_PATH_RECEIVED", self.path)

                if not self.path.startswith(callback_path):
                    self.send_response(404)
                    self.end_headers()
                    log("CALLBACK_INVALID_PATH", self.path)
                    return

                parsed_url = urllib.parse.urlparse(self.path)
                params: Dict[str, list[str]] = urllib.parse.parse_qs(parsed_url.query)

                if "error" in params:
                    error_value: str = params["error"][0]
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(f"OAuth error: {error_value}".encode())
                    log("OAUTH_ERROR_RECEIVED", params)
                    result_container["error"] = error_value
                    threading.Thread(target=server.shutdown).start()
                    return

                code_list: Optional[list[str]] = params.get("code")
                if not code_list:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"No authorization code received.")
                    log("CALLBACK_NO_AUTH_CODE")
                    return

                code: str = code_list[0]
                log("AUTHORIZATION_CODE_EXTRACTED", code)

                try:
                    token: Dict[str, Any] = exchange_code_for_token(code, code_verifier, redirect_uri)
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"Authentication successful. You may close this window.")

                    log("OAUTH_FLOW_COMPLETE", {
                        "access_token": token.get("access_token"),
                        "refresh_token": token.get("refresh_token"),
                        "instance_url": token.get("instance_url"),
                        "id_url": token.get("id")
                    })

                    result_container["token"] = token
                    threading.Thread(target=server.shutdown).start()

                except Exception as e:
                    self.send_response(500)
                    self.end_headers()
                    error_text: str = str(e)
                    self.wfile.write(error_text.encode())
                    log("TOKEN_EXCHANGE_EXCEPTION", error_text)
                    result_container["error"] = error_text
                    threading.Thread(target=server.shutdown).start()

            def log_message(self, format, *args):
                return  # suppress HTTP server default logging

        return Handler

    server: HTTPServer = HTTPServer((hostname, port), handler_factory())
    log("CALLBACK_SERVER_STARTED", {"listening_on": redirect_uri, "port": port})

    server_thread: threading.Thread = threading.Thread(target=server.serve_forever)
    server_thread.start()
    server_thread.join()  # wait for shutdown

    return result_container.get("token"), result_container.get("error")


# --------------------------------------------------
# Main Execution
# --------------------------------------------------
def run(redirect_uri: str = CB) -> None:
    if os.path.exists(LOG_FILE):
        os.remove(LOG_FILE)

    log("OAUTH_FLOW_STARTED", {"instance": INSTANCE, "client_id": KEY, "redirect_uri": redirect_uri})

    code_verifier, code_challenge = generate_pkce()
    auth_url: str = build_auth_url(code_challenge, redirect_uri)

    log("OPENING_BROWSER", auth_url)
    webbrowser.open(auth_url)

    token, error = start_callback_server(code_verifier, redirect_uri)

    if token:
        log("FINAL_TOKEN_RECEIVED", token)
    elif error:
        log("FINAL_ERROR_RECEIVED", error)


if __name__ == "__main__":
    run()
