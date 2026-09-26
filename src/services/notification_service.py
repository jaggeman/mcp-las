import os
import smtplib
import ssl
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import html
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
        # Ravarden till textdelen och loggning, escapade varden till HTML.
        # Faltena kommer fran ett publikt formular: utan escaping renderas
        # inskickad markup i mottagarens e-postklient, och ett citattecken i
        # adressen bryter sig ur href="mailto:...".
        raw_name = request_data.get("name", "Okänd")
        raw_email = request_data.get("email", "Ingen e-post")
        raw_company = request_data.get("company", "Ej angivet") or "Ej angivet"
        raw_reason = request_data.get("reason", "Ej angivet") or "Ej angivet"
        created_at = request_data.get("created_at", "")

        name = html.escape(str(raw_name), quote=True)
        email = html.escape(str(raw_email), quote=True)
        company = html.escape(str(raw_company), quote=True)
        reason = html.escape(str(raw_reason), quote=True)

        # Radbrytningar i en rubrik kan anvandas for att injicera e-posthuvuden.
        amne_namn = " ".join(str(raw_name).split())
        amne_foretag = " ".join(str(raw_company).split())
        subject = f"[MCP LAS] Ny ansökan om API-nyckel: {amne_namn} ({amne_foretag})"

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
      Detta är en automatisk notis från <a href="https://las.novro.se" style="color: #64748b;">las.novro.se</a>.
    </div>
  </div>
</body>
</html>
"""

        text_content = f"""Ny ansökan om API-nyckel till MCP LAS:
- Namn: {raw_name}
- E-post: {raw_email}
- Företag: {raw_company}
- Användningsområde: {raw_reason}
- Tidpunkt: {created_at}
"""

        if not self.smtp_user or not self.smtp_pass:
            logger.warning("[NOTIFICATION] SMTP credentials are not configured; notification skipped")
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.smtp_user
            msg["To"] = self.recipient
            # Adressfalt ska ha ravardet, inte HTML-escapat. Radbrytningar
            # strips av samma skal som i amnesraden: de kan injicera huvuden.
            msg["Reply-To"] = " ".join(str(raw_email).split())

            part1 = MIMEText(text_content, "plain", "utf-8")
            part2 = MIMEText(html_content, "html", "utf-8")
            msg.attach(part1)
            msg.attach(part2)

            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=10, context=ssl.create_default_context()) as server:
                    server.login(self.smtp_user, self.smtp_pass)
                    server.sendmail(self.smtp_user, [self.recipient], msg.as_string())
            else:
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                    server.starttls(context=ssl.create_default_context())
                    server.login(self.smtp_user, self.smtp_pass)
                    server.sendmail(self.smtp_user, [self.recipient], msg.as_string())

            logger.info("[NOTIFICATION] Key-request e-mail sent")
            return True
        except Exception as e:
            logger.error("[NOTIFICATION] Failed to send email")
            return False

notification_service = NotificationService()
