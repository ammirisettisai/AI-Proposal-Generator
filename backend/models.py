from sqlalchemy import Column, Integer, String, Text
from database import Base


class EmailRequest(Base):
    __tablename__ = "email_requests"

    id = Column(Integer, primary_key=True, index=True)
    client = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    project = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="Pending")