from __future__ import annotations

import logging
import time

import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.utils import OperationalError, ProgrammingError
from django.urls import reverse


logger = logging.getLogger(__name__)


def _build_ticket_message(ticket, created: bool) -> tuple[str, str]:
    action = "New ticket" if created else "Ticket updated"
    subject = f"[TicketSystem] {action} #{ticket.id}: {ticket.title}"

    ticket_url = reverse("ticket_detail", kwargs={"ticket_id": ticket.id})
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    ticket_link = f"{site_url}{ticket_url}" if site_url else ticket_url

    creator_name = ticket.creator.get_full_name() or ticket.creator.username
    assigned_name = (
        (ticket.assigned_to.get_full_name() or ticket.assigned_to.username)
        if ticket.assigned_to
        else "unassigned"
    )
    status_name = ticket.status.get_name_display() if ticket.status else "-"
    priority_name = ticket.priority.get_name_display() if ticket.priority else "-"

    message = (
        f"{action}\n\n"
        f"ID: #{ticket.id}\n"
        f"Title: {ticket.title}\n"
        f"Creator: {creator_name}\n"
        f"Assigned: {assigned_name}\n"
        f"Status: {status_name}\n"
        f"Priority: {priority_name}\n\n"
        f"Link: {ticket_link}\n"
    )
    return subject, message


def _get_admin_recipient_emails() -> list[str]:
    configured = getattr(settings, "ADMIN_NOTIFICATION_EMAILS", [])
    if configured:
        return [email for email in configured if email]

    user_model = get_user_model()
    try:
        users = user_model.objects.filter(
            is_staff=True,
            is_active=True,
            profile__notify_email=True,
        ).select_related("profile")
    except (OperationalError, ProgrammingError):
        users = user_model.objects.filter(is_staff=True, is_active=True)

    recipients: list[str] = []
    for user in users:
        custom_email = ""
        profile = getattr(user, "profile", None)
        if profile is not None:
            custom_email = (getattr(profile, "notify_email_address", "") or "").strip()

        email = custom_email or (user.email or "").strip()
        if email:
            recipients.append(email)

    # Keep order and remove duplicates.
    return list(dict.fromkeys(recipients))


def _get_admin_vk_recipients() -> list[str]:
    user_model = get_user_model()
    try:
        queryset = user_model.objects.filter(
            is_staff=True,
            is_active=True,
            profile__notify_vk=True,
        )
    except (OperationalError, ProgrammingError):
        return []

    return list(
        queryset.exclude(profile__vk_user_id__isnull=True)
        .exclude(profile__vk_user_id__exact="")
        .values_list("profile__vk_user_id", flat=True)
    )


def _recipient_to_vk_params(recipient: str) -> dict[str, str]:
    value = (recipient or "").strip()
    if value.startswith("id") and value[2:].isdigit():
        return {"user_id": value[2:]}
    if value.isdigit():
        return {"user_id": value}
    return {"domain": value}


def send_ticket_email_notification(ticket, created: bool) -> bool:
    if not getattr(settings, "NOTIFY_EMAIL_ENABLED", True):
        return False

    recipients = _get_admin_recipient_emails()
    if not recipients:
        return False

    subject, message = _build_ticket_message(ticket, created=created)

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=recipients,
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception("Failed to send email notification for ticket #%s", ticket.id)
        return False


def send_ticket_vk_notification(ticket, created: bool) -> bool:
    if not getattr(settings, "VK_NOTIFY_ENABLED", False):
        return False

    token = getattr(settings, "VK_GROUP_TOKEN", "")
    if not token:
        return False

    recipients = _get_admin_vk_recipients()
    if not recipients:
        return False

    _, message = _build_ticket_message(ticket, created=created)
    api_version = getattr(settings, "VK_API_VERSION", "5.199")
    api_url = "https://api.vk.com/method/messages.send"

    sent_any = False
    for idx, recipient in enumerate(recipients):
        recipient_params = _recipient_to_vk_params(recipient)
        if not recipient_params.get("user_id") and not recipient_params.get("domain"):
            continue

        payload = {
            "access_token": token,
            "v": api_version,
            "random_id": int(time.time() * 1000) + idx,
            "message": message,
        }
        payload.update(recipient_params)

        try:
            response = requests.post(api_url, data=payload, timeout=10)
            data = response.json()
            if "error" in data:
                logger.warning(
                    "VK notify error for recipient %s: %s",
                    recipient,
                    data.get("error", {}).get("error_msg"),
                )
                continue
            sent_any = True
        except Exception:
            logger.exception("Failed to send VK notification for ticket #%s", ticket.id)

    return sent_any


def send_ticket_notifications(ticket, created: bool) -> dict[str, bool]:
    email_sent = send_ticket_email_notification(ticket, created=created)
    vk_sent = send_ticket_vk_notification(ticket, created=created)
    return {
        "email_sent": email_sent,
        "vk_sent": vk_sent,
    }
