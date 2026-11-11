
import os

# Local development only
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

from dotenv import load_dotenv
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

load_dotenv(override=True)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send"
]

REDIRECT_URI = "http://localhost:8000/auth/gmail/callback"

TOKEN_FILE = os.path.join(
    os.path.dirname(__file__),
    "token.json"
)

# Keep the same OAuth flow between login and callback
_pending_flow = None


def create_oauth_flow(state=None):
    global _pending_flow

    # Reuse the original flow during the Google callback.
    # This preserves the PKCE code verifier.
    if state is not None:
        if _pending_flow is None:
            raise RuntimeError(
                "OAuth session expired. Please try Gmail login again."
            )
        return _pending_flow

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise RuntimeError(
            "Google OAuth credentials are missing. Check your .env file."
        )

    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [REDIRECT_URI]
        }
    }

    flow = Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
        autogenerate_code_verifier=True
    )

    _pending_flow = flow

    return flow


def save_credentials(credentials):
    global _pending_flow

    with open(TOKEN_FILE, "w", encoding="utf-8") as token:
        token.write(credentials.to_json())

    _pending_flow = None


def get_gmail_service():

    if not os.path.exists(TOKEN_FILE):
        raise RuntimeError(
            "Gmail is not connected. Please authorize first."
        )

    credentials = Credentials.from_authorized_user_file(
        TOKEN_FILE,
        SCOPES
    )

    return build(
        "gmail",
        "v1",
        credentials=credentials
    )
