
import os
import json

from dotenv import load_dotenv
from cryptography.fernet import Fernet

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from sqlalchemy.orm import sessionmaker

from database import engine
from models import GmailOAuthSession, GmailCredential


load_dotenv()

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send"
]


def get_encryption():
    key = os.getenv("GMAIL_TOKEN_ENCRYPTION_KEY")

    if not key:
        raise RuntimeError(
            "GMAIL_TOKEN_ENCRYPTION_KEY is missing."
        )

    return Fernet(key.encode())


def get_client_config(redirect_uri):
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise RuntimeError(
            "Google OAuth credentials are missing."
        )

    return {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri]
        }
    }


def create_oauth_flow(redirect_uri, state=None):

    client_config = get_client_config(redirect_uri)

    if state:
        with SessionLocal() as db:
            oauth_session = (
                db.query(GmailOAuthSession)
                .filter(GmailOAuthSession.id == 1)
                .first()
            )

            if not oauth_session or oauth_session.state != state:
                raise RuntimeError(
                    "OAuth session expired. Please try Gmail login again."
                )

            verifier = oauth_session.code_verifier

        return Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=redirect_uri,
            state=state,
            code_verifier=verifier
        )

    return Flow.from_client_config(
        client_config,
        scopes=SCOPES,
        redirect_uri=redirect_uri,
        autogenerate_code_verifier=True
    )


def save_oauth_session(state, code_verifier):

    with SessionLocal() as db:
        oauth_session = (
            db.query(GmailOAuthSession)
            .filter(GmailOAuthSession.id == 1)
            .first()
        )

        if oauth_session is None:
            oauth_session = GmailOAuthSession(
                id=1,
                state=state,
                code_verifier=code_verifier
            )
            db.add(oauth_session)
        else:
            oauth_session.state = state
            oauth_session.code_verifier = code_verifier

        db.commit()


def delete_oauth_session():

    with SessionLocal() as db:
        oauth_session = (
            db.query(GmailOAuthSession)
            .filter(GmailOAuthSession.id == 1)
            .first()
        )

        if oauth_session:
            db.delete(oauth_session)
            db.commit()


def save_credentials(credentials):

    encryption = get_encryption()

    encrypted_token = encryption.encrypt(
        credentials.to_json().encode("utf-8")
    ).decode("utf-8")

    with SessionLocal() as db:
        saved = (
            db.query(GmailCredential)
            .filter(GmailCredential.id == 1)
            .first()
        )

        if saved is None:
            saved = GmailCredential(
                id=1,
                encrypted_token=encrypted_token
            )
            db.add(saved)
        else:
            saved.encrypted_token = encrypted_token

        db.commit()


def get_gmail_service():

    encryption = get_encryption()

    with SessionLocal() as db:
        saved = (
            db.query(GmailCredential)
            .filter(GmailCredential.id == 1)
            .first()
        )

        if not saved:
            raise RuntimeError(
                "Gmail is not connected. Please authorize first."
            )

        decrypted_token = encryption.decrypt(
            saved.encrypted_token.encode("utf-8")
        ).decode("utf-8")

        credentials = Credentials.from_authorized_user_info(
            json.loads(decrypted_token),
            SCOPES
        )

        if credentials.expired:
            if not credentials.refresh_token:
                raise RuntimeError(
                    "Gmail authorization expired. Please connect Gmail again."
                )

            credentials.refresh(Request())

            encrypted_token = encryption.encrypt(
                credentials.to_json().encode("utf-8")
            ).decode("utf-8")

            saved.encrypted_token = encrypted_token
            db.commit()

    return build(
        "gmail",
        "v1",
        credentials=credentials
    )
