
import os
import json
import base64

from io import BytesIO
from email.message import EmailMessage
from xml.sax.saxutils import escape

from dotenv import load_dotenv
from google import genai

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, RedirectResponse

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, sessionmaker

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    ListFlowable,
    ListItem,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.lib.units import inch

from database import engine, Base
from models import EmailRequest

from gmail_service import (
    create_oauth_flow,
    save_credentials,
    get_gmail_service,
)


# --------------------------------------------------
# ENVIRONMENT SETTINGS
# --------------------------------------------------

load_dotenv(override=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

gemini_client = (
    genai.Client(api_key=GEMINI_API_KEY)
    if GEMINI_API_KEY
    else None
)


# --------------------------------------------------
# DATABASE SETTINGS
# --------------------------------------------------

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


Base.metadata.create_all(bind=engine)


# --------------------------------------------------
# FASTAPI APPLICATION
# --------------------------------------------------

app = FastAPI(
    title="AI Proposal Generator",
    description="AI-powered Email-to-Proposal Generation System",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------
# GMAIL OAUTH STATE
# --------------------------------------------------

gmail_oauth_state = None


# --------------------------------------------------
# PYDANTIC SCHEMAS
# --------------------------------------------------

class RequestCreate(BaseModel):
    client: str
    email: str
    project: str
    description: str = ""
    status: str = "Pending"


class RequestUpdate(BaseModel):
    client: str | None = None
    email: str | None = None
    project: str | None = None
    description: str | None = None
    status: str | None = None


class EmailContent(BaseModel):
    subject: str
    body: str


class ProposalPDF(BaseModel):
    title: str
    client: str
    executive_summary: str
    project_objectives: list[str] = Field(default_factory=list)
    scope_of_work: list[str] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    timeline: object = ""
    pricing: object = ""
    next_steps: list[str] = Field(default_factory=list)


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def get_gemini_client():
    if gemini_client is None:
        raise HTTPException(
            status_code=500,
            detail="GEMINI_API_KEY is missing from the .env file."
        )
    return gemini_client


def request_to_dict(item):
    return {
        "id": item.id,
        "client": item.client,
        "email": item.email,
        "project": item.project,
        "description": item.description,
        "status": item.status,
    }


def create_proposal_pdf(proposal):
    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=(8.5 * inch, 11 * inch),
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ProposalTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#17365D"),
        spaceAfter=20,
    )

    heading_style = ParagraphStyle(
        "ProposalHeading",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#17365D"),
        spaceBefore=14,
        spaceAfter=8,
    )

    story = []

    story.append(
        Paragraph(
            escape(str(proposal.title)),
            title_style
        )
    )

    story.append(
        Paragraph(
            f"<b>Client:</b> {escape(str(proposal.client))}",
            styles["Normal"]
        )
    )

    story.append(Spacer(1, 18))

    story.append(
        Paragraph("Executive Summary", heading_style)
    )

    story.append(
        Paragraph(
            escape(str(proposal.executive_summary)),
            styles["BodyText"]
        )
    )

    sections = [
        ("Project Objectives", proposal.project_objectives),
        ("Scope of Work", proposal.scope_of_work),
        ("Deliverables", proposal.deliverables),
        ("Assumptions", proposal.assumptions),
        ("Next Steps", proposal.next_steps),
    ]

    for heading, items in sections:
        story.append(Paragraph(heading, heading_style))

        if items:
            bullet_items = []

            for item in items:
                bullet_items.append(
                    ListItem(
                        Paragraph(
                            escape(str(item)),
                            styles["BodyText"]
                        )
                    )
                )

            story.append(
                ListFlowable(
                    bullet_items,
                    bulletType="bullet",
                    leftIndent=18
                )
            )
        else:
            story.append(
                Paragraph("Not specified", styles["BodyText"])
            )

    story.append(
        Paragraph("Timeline", heading_style)
    )

    story.append(
        Paragraph(
            escape(str(proposal.timeline)),
            styles["BodyText"]
        )
    )

    story.append(
        Paragraph("Pricing", heading_style)
    )

    story.append(
        Paragraph(
            escape(str(proposal.pricing)),
            styles["BodyText"]
        )
    )

    document.build(story)

    buffer.seek(0)
    return buffer


# --------------------------------------------------
# HOME AND HEALTH ROUTES
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "AI Proposal Generator API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }


# --------------------------------------------------
# GET ALL CLIENT REQUESTS
# --------------------------------------------------

@app.get("/api/requests")
def get_requests(db: Session = Depends(get_db)):

    requests = (
        db.query(EmailRequest)
        .order_by(EmailRequest.id)
        .all()
    )

    return {
        "total": len(requests),
        "requests": [
            request_to_dict(item)
            for item in requests
        ]
    }


# --------------------------------------------------
# CREATE CLIENT REQUEST
# --------------------------------------------------

@app.post("/api/requests")
def create_request(
    request_data: RequestCreate,
    db: Session = Depends(get_db)
):

    new_request = EmailRequest(
        client=request_data.client,
        email=request_data.email,
        project=request_data.project,
        description=request_data.description,
        status=request_data.status,
    )

    db.add(new_request)
    db.commit()
    db.refresh(new_request)

    return request_to_dict(new_request)


# --------------------------------------------------
# UPDATE CLIENT REQUEST
# --------------------------------------------------

@app.put("/api/requests/{request_id}")
def update_request(
    request_id: int,
    request_data: RequestUpdate,
    db: Session = Depends(get_db)
):

    client_request = (
        db.query(EmailRequest)
        .filter(EmailRequest.id == request_id)
        .first()
    )

    if not client_request:
        raise HTTPException(
            status_code=404,
            detail="Request not found"
        )

    update_data = request_data.model_dump(
        exclude_unset=True
    )

    for key, value in update_data.items():
        if value is not None:
            setattr(client_request, key, value)

    db.commit()
    db.refresh(client_request)

    return request_to_dict(client_request)


# --------------------------------------------------
# DELETE CLIENT REQUEST
# --------------------------------------------------

@app.delete("/api/requests/{request_id}")
def delete_request(
    request_id: int,
    db: Session = Depends(get_db)
):

    client_request = (
        db.query(EmailRequest)
        .filter(EmailRequest.id == request_id)
        .first()
    )

    if not client_request:
        raise HTTPException(
            status_code=404,
            detail="Request not found"
        )

    db.delete(client_request)
    db.commit()

    return {
        "message": "Request deleted successfully"
    }


# --------------------------------------------------
# GEMINI EMAIL EXTRACTION
# --------------------------------------------------

@app.post("/api/extract-email")
def extract_email(
    email_data: EmailContent
):

    client = get_gemini_client()

    prompt = f"""
You are an expert B2B sales assistant.

Extract the following information from the customer email.

Email Subject:
{email_data.subject}

Email Body:
{email_data.body}

Return ONLY valid JSON with exactly these fields:

{{
    "client": "",
    "email": "",
    "project": "",
    "description": ""
}}

Do not invent missing information.
Use empty strings when information is unavailable.
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config={
                "response_mime_type": "application/json"
            }
        )

        if not response.text:
            raise HTTPException(
                status_code=502,
                detail="Gemini returned an empty response."
            )

        extracted_data = json.loads(response.text)

        return {
            "message": "Email information extracted successfully",
            "extracted_data": extracted_data
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini API error: {str(error)}"
        )


# --------------------------------------------------
# GEMINI PROPOSAL GENERATION
# --------------------------------------------------

@app.post("/api/generate-proposal/{request_id}")
def generate_proposal(
    request_id: int,
    db: Session = Depends(get_db)
):

    client_request = (
        db.query(EmailRequest)
        .filter(EmailRequest.id == request_id)
        .first()
    )

    if not client_request:
        raise HTTPException(
            status_code=404,
            detail="Client request not found"
        )

    client = get_gemini_client()

    prompt = f"""
You are a professional B2B proposal writer.

Create a detailed and professional business proposal.

Client: {client_request.client}
Email: {client_request.email}
Project: {client_request.project}
Description: {client_request.description}

Return ONLY valid JSON with these exact fields:

{{
    "title": "Professional project proposal title",
    "client": "{client_request.client}",
    "executive_summary": "A professional project summary",
    "project_objectives": [
        "Objective 1",
        "Objective 2"
    ],
    "scope_of_work": [
        "Scope item 1",
        "Scope item 2"
    ],
    "deliverables": [
        "Deliverable 1",
        "Deliverable 2"
    ],
    "assumptions": [
        "Assumption 1"
    ],
    "timeline": "Estimated project timeline",
    "pricing": "Pricing information or To be discussed",
    "next_steps": [
        "Next step 1",
        "Next step 2"
    ]
}}

Do not invent a confirmed budget or deadline.
If pricing is unknown, write "To be discussed".
Use professional business language.
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash-lite",
            contents=prompt,
            config={
                "response_mime_type": "application/json"
            }
        )

        if not response.text:
            raise HTTPException(
                status_code=502,
                detail="Gemini returned an empty proposal."
            )

        proposal = json.loads(response.text)

        return {
            "message": "Proposal generated successfully",
            "proposal": proposal
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini API error: {str(error)}"
        )


# --------------------------------------------------
# GENERATE AND DOWNLOAD PROPOSAL PDF
# --------------------------------------------------

@app.post("/api/generate-proposal-pdf/{request_id}")
def generate_proposal_pdf(
    request_id: int,
    proposal: ProposalPDF,
    db: Session = Depends(get_db)
):

    client_request = (
        db.query(EmailRequest)
        .filter(EmailRequest.id == request_id)
        .first()
    )

    if not client_request:
        raise HTTPException(
            status_code=404,
            detail="Client request not found"
        )

    try:
        pdf_buffer = create_proposal_pdf(proposal)

        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition":
                f"attachment; filename=proposal_{request_id}.pdf"
            }
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"PDF generation failed: {str(error)}"
        )


# --------------------------------------------------
# GMAIL LOGIN
# --------------------------------------------------

@app.get("/auth/gmail/login")
def gmail_login():

    global gmail_oauth_state

    try:
        flow = create_oauth_flow()

        authorization_url, state = (
            flow.authorization_url(
                access_type="offline",
                include_granted_scopes="true",
                prompt="consent"
            )
        )

        gmail_oauth_state = state

        return RedirectResponse(
            authorization_url
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Gmail authorization failed: {str(error)}"
        )


# --------------------------------------------------
# GMAIL CALLBACK
# --------------------------------------------------

@app.get("/auth/gmail/callback")
def gmail_callback(
    request: Request,
    state: str | None = None
):

    global gmail_oauth_state

    try:
        if not state or state != gmail_oauth_state:
            raise HTTPException(
                status_code=400,
                detail="Invalid Gmail OAuth state. Please log in again."
            )

        flow = create_oauth_flow(state=state)

        flow.fetch_token(
            authorization_response=str(request.url)
        )

        save_credentials(flow.credentials)

        gmail_oauth_state = None

        return {
            "message": "Gmail authorization successful!"
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Gmail authorization failed: {str(error)}"
        )


# --------------------------------------------------
# SEND PROPOSAL THROUGH GMAIL
# AND AUTOMATICALLY UPDATE STATUS
# --------------------------------------------------

@app.post("/api/send-proposal/{request_id}")
def send_proposal_email(
    request_id: int,
    proposal: ProposalPDF,
    db: Session = Depends(get_db),
):

    client_request = (
        db.query(EmailRequest)
        .filter(EmailRequest.id == request_id)
        .first()
    )

    if not client_request:
        raise HTTPException(
            status_code=404,
            detail="Client request not found"
        )

    if not client_request.email:
        raise HTTPException(
            status_code=400,
            detail="Client email address is missing"
        )

    try:
        pdf_buffer = create_proposal_pdf(proposal)
        pdf_bytes = pdf_buffer.getvalue()

        message = EmailMessage()

        message["To"] = client_request.email

        message["Subject"] = (
            f"Project Proposal - {proposal.client}"
        )

        message.set_content(f"""Hello {proposal.client},

Please find attached the project proposal for:

{proposal.title}

Kindly review the attached proposal.

Please contact us if you have any questions.

Best regards,
AI Proposal Generator
""")

        message.add_attachment(
            pdf_bytes,
            maintype="application",
            subtype="pdf",
            filename=f"proposal_{request_id}.pdf",
        )

        gmail_service = get_gmail_service()

        encoded_message = base64.urlsafe_b64encode(
            message.as_bytes()
        ).decode("utf-8")

        sent_message = (
            gmail_service.users()
            .messages()
            .send(
                userId="me",
                body={"raw": encoded_message}
            )
            .execute()
        )

        # Update status only after Gmail confirms sending
        client_request.status = "Sent"

        db.commit()
        db.refresh(client_request)

        return {
            "message": "Proposal email sent successfully!",
            "recipient": client_request.email,
            "gmail_message_id": sent_message.get("id"),
            "status": client_request.status,
        }

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"Gmail sending failed: {str(error)}"
        )


