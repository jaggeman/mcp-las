import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        self.recipient = os.environ.get("NOTIFICATION_EMAIL", "jagge@novro.se")
        self.smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "465"))
        self.smtp_user = os.environ.get("SMTP_USER", "")
        self.smtp_pass = os.environ.get("SMTP_PASS", "")

    def send_key_request_notification(self, request_data: Dict[str, Any]) -> bool:
        """
        Sends an email notification when a user submits an API key request.
        """
        name = request_data.get("name", "Okänd")
        email = request_data.get("email", "Ingen e-post")
        company = request_data.get("company", "Ej angivet") or "Ej angivet"
        reason = request_data.get("reason", "Ej angivet") or "Ej angivet"
        created_at = request_data.get("created_at", "")

        subject = f"[MCP LAS] Ny ansökan om API-nyckel: {name} ({company})"
        
        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1e293b; background-color: #f8fafc; margin: 0; padding: 20px; }}
    .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05); }}
    .header {{ background: linear-gradient(135deg, #16a34a, #15803d); color: #ffffff; padding: 24px; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 20px; font-weight: 700; }}
    .content {{ padding: 24px; }}
    .field {{ margin-bottom: 16px; }}
    .label {{ font-size: 12px; font-weight: 700; text-transform: uppercase; color: #64748b; margin-bottom: 4px; }}
    .value {{ font-size: 15px; color: #0f172a; font-weight: 500; background: #f1f5f9; padding: 8px 12px; border-radius: 6px; }}
    .reason-box {{ background: #f8fafc; border-left: 4px solid #16a34a; padding: 12px; border-radius: 0 6px 6px 0; font-style: italic; }}
    .footer {{ padding: 16px 24px; background: #f8fafc; border-top: 1px solid #e2e8f0; text-align: center; font-size: 12px; color: #94a3b8; }}
    .action-btn {{ display: inline-block; background: #16a34a; color: #ffffff !important; text-decoration: none; padding: 10px 20px; border-radius: 6px; font-weight: 600; margin-top: 12px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Ny API-nyckelansökan mottagen</h1>
    </div>
    <div class="content">
      <div class="field">
        <div class="label">Sökande Namn</div>
        <div class="value">{name}</div>
      </div>
      <div class="field">
        <div class="label">E-postadress</div>
        <div class="value"><a href="mailto:{email}" style="color: #16a34a; text-decoration: none;">{email}</a></div>
      </div>
      <div class="field">
        <div class="label">Företag / Organisation</div>
        <div class="value">{company}</div>
      </div>
      <div class="field">
        <div class="label">Användningsområde / Motivering</div>
        <div class="reason-box">{reason}</div>
      </div>
      <div class="field">
        <div class="label">Tidpunkt (UTC)</div>
        <div class="value">{created_at}</div>
      </div>
      <div style="text-align: center; margin-top: 24px;">
        <a href="mailto:{email}?subject=Din%20API-nyckel%20f%C3%B6r%20MCP%20LAS" class="action-btn">Svara direkt till {name} &rarr;</a>
      </div>
    </div>
    <div class="footer">
      Detta är en automatisk notis från <a href="https://mcp-las-rules.web.app" style="color: #64748b;">mcp-las-rules.web.app</a>.
    </div>
  </div>
</body>
</html>
"""

        text_content = f"""Ny ansökan om API-nyckel till MCP LAS:
- Namn: {name}
- E-post: {email}
- Företag: {company}
- Användningsområde: {reason}
- Tidpunkt: {created_at}
"""

        if not self.smtp_user or not self.smtp_pass:
            logger.warning(
                f"[NOTIFICATION] SMTP credentials (SMTP_USER / SMTP_PASS) not configured. "
                f"Notification for {email} logged locally. Target recipient: {self.recipient}"
            )
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.smtp_user
            msg["To"] = self.recipient
            msg["Reply-To"] = email

            part1 = MIMEText(text_content, "plain", "utf-8")
            part2 = MIMEText(html_content, "html", "utf-8")
            msg.attach(part1)
            msg.attach(part2)

            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=10) as server:
                    server.login(self.smtp_user, self.smtp_pass)
                    server.sendmail(self.smtp_user, [self.recipient], msg.as_string())
            else:
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_pass)
                    server.sendmail(self.smtp_user, [self.recipient], msg.as_string())

            logger.info(f"[NOTIFICATION] E-mail sent to {self.recipient} for request by {email}")
            return True
        except Exception as e:
            logger.error(f"[NOTIFICATION] Failed to send email: {e}")
            return False

notification_service = NotificationService()
