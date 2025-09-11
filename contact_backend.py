from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from pathlib import Path
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

class ContactForm(BaseModel):
    name: str
    company: str | None = None
    subject: str
    message: str


def send_email(name: str, company: str | None, subject: str, message: str) -> None:
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    to_email = os.getenv("TO_EMAIL", "jaskp1008@gmail.com")
    # Ensure FROM_EMAIL is a real, verified email; never default to smtp_user
    from_email = os.getenv("FROM_EMAIL", to_email)

    if not smtp_host or not smtp_user or not smtp_pass:
        raise RuntimeError("SMTP configuration missing: ensure SMTP_HOST, SMTP_USER, SMTP_PASS are set")
    if not from_email or "@" not in from_email:
        raise RuntimeError("FROM_EMAIL must be a valid email address and SES-verified")

    body = f"""
New contact form submission:

Name: {name}
Company: {company or '-'}
Subject: {subject}

Message:
{message}
""".strip()

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = f"[Portfolio Contact] {subject}"
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(from_email, [to_email], msg.as_string())


@router.get("/contact")
async def get_contact_page():
    contact_file = FRONTEND_DIR / "contact.html"
    if not contact_file.exists():
        raise HTTPException(status_code=404, detail="contact.html not found")
    return FileResponse(str(contact_file))


@router.post("/contact/submit")
async def submit_contact(form: ContactForm):
    try:
        send_email(form.name, form.company, form.subject, form.message)
        return JSONResponse({"status": "ok", "message": "Your message was sent. Thanks!"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {e}")
