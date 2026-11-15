
from sqlalchemy import Column, Integer, String, Text, DateTime, func
from database import Base


class EmailRequest(Base):
    __tablename__ = "email_requests"

    id = Column(Integer, primary_key=True, index=True)
    client = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    project = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="Pending")


class GmailOAuthSession(Base):
    __tablename__ = "gmail_oauth_sessions"

    id = Column(Integer, primary_key=True, default=1)
    state = Column(String(512), nullable=False)
    code_verifier = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )


class GmailCredential(Base):
    __tablename__ = "gmail_credentials"

    id = Column(Integer, primary_key=True, default=1)
    encrypted_token = Column(Text, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
