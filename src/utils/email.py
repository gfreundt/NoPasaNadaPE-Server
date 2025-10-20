import smtplib
from email.message import EmailMessage
from email.utils import formataddr


class Email:

    def __init__(self, from_account, password):
        self.from_account = from_account
        self.password = password

    def send_email(self, emails):

        # if user sends single email, change format to list
        if type(emails) is not list:
            emails = [emails]

        for email in emails:
            # create the email message
            msg = EmailMessage()
            msg["From"] = (
                formataddr(self.from_account)
                if isinstance(self.from_account, tuple)
                else self.from_account
            )
            msg["To"] = email["to"]
            msg["Subject"] = email["subject"]

            # add plain text / HTML
            if email.get("plain_content"):
                msg.set_content(email["plain_content"])
            if email.get("html_content"):
                msg.add_alternative(email["html_content"], subtype="html")

            # process attachments
            if email.get("attachments"):
                for attachment in email["attachments"]:
                    msg.add_attachment(
                        attachment["bytes_data"],
                        maintype=attachment["maintype"],
                        subtype=attachment["subtype"],
                        filename=attachment["filename"],
                    )

            # send the email via Zoho's SMTP server
            try:
                with smtplib.SMTP("smtp.zoho.com", 587) as server:
                    server.starttls()  # Secure the connection
                    server.login(self.from_account[1], self.password)
                    server.send_message(msg)
                    return True
            except Exception:
                return False
