"""Stand-in for a real email/SMS provider (e.g. SendGrid, Twilio). Nothing is
actually delivered — each call just prints what *would* have been sent, so
the notification flow can be demoed end-to-end without external credentials.
Swap the bodies of these two functions for a real provider call to go live."""


def send_email(to: str, subject: str, body: str) -> None:
    print(f"[EMAIL -> {to}] {subject} | {body}")


def send_sms(to: str, body: str) -> None:
    print(f"[SMS -> {to}] {body}")
