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
    action = "Новый тикет" if created else "Тикет обновлён"
    subject = f"[TicketSystem] {action} #{ticket.id}: {ticket.title}"

    ticket_url = reverse("ticket_detail", kwargs={"ticket_id": ticket.id})
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    ticket_link = f"{site_url}{ticket_url}" if site_url else ticket_url

    creator_name = ticket.creator.get_full_name() or ticket.creator.username
    assigned_name = (
        (ticket.assigned_to.get_full_name() or ticket.assigned_to.username)
        if ticket.assigned_to
        else "Не назначено"
    )
    status_name = ticket.status.get_name_display() if ticket.status else "-"
    priority_name = ticket.priority.get_name_display() if ticket.priority else "-"

    message = (
        f"{action}\n\n"
        f"ID: #{ticket.id}\n"
        f"Заголовок: {ticket.title}\n"
        f"Создатель: {creator_name}\n"
        f"Назначено: {assigned_name}\n"
        f"Статус: {status_name}\n"
        f"Приоритет: {priority_name}\n\n"
        f"Ссылка: {ticket_link}\n"
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


def _get_creator_vk_id(ticket) -> str | None:
    profile = getattr(ticket.creator, "profile", None)
    if not profile:
        return None
    if not getattr(profile, "notify_vk", False):
        return None
    vk_id = (getattr(profile, "vk_user_id", "") or "").strip()
    return vk_id if vk_id else None


def _get_creator_email(ticket) -> str | None:
    profile = getattr(ticket.creator, "profile", None)
    if not profile:
        return None
    if not getattr(profile, "notify_email", False):
        return None
    custom_email = (getattr(profile, "notify_email_address", "") or "").strip()
    return custom_email or (ticket.creator.email or "").strip() or None


def _build_creator_message(ticket, created: bool) -> tuple[str, str]:
    ticket_url = reverse("ticket_detail", kwargs={"ticket_id": ticket.id})
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    ticket_link = f"{site_url}{ticket_url}" if site_url else ticket_url

    status_name = ticket.status.get_name_display() if ticket.status else "-"
    priority_name = ticket.priority.get_name_display() if ticket.priority else "-"
    assigned_name = (
        (ticket.assigned_to.get_full_name() or ticket.assigned_to.username)
        if ticket.assigned_to
        else "Не назначено"
    )

    if created:
        subject = f"[Ticket System] Ваш тикет #{ticket.id} принят"
        body = (
            f"Ваш тикет принят в работу.\n\n"
            f"#{ticket.id}: {ticket.title}\n"
            f"Статус: {status_name}\n"
            f"Приоритет: {priority_name}\n"
            f"Назначено: {assigned_name}\n\n"
            f"Ссылка: {ticket_link}"
        )
    else:
        subject = f"[Ticket System] Тикет #{ticket.id} обновлён"
        body = (
            f"Ваш тикет был обновлён.\n\n"
            f"#{ticket.id}: {ticket.title}\n"
            f"Статус: {status_name}\n"
            f"Приоритет: {priority_name}\n"
            f"Назначено: {assigned_name}\n\n"
            f"Ссылка: {ticket_link}"
        )
    return subject, body


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


def send_creator_vk_notification(ticket, created: bool) -> bool:
    if not getattr(settings, "VK_NOTIFY_ENABLED", False):
        return False
    token = getattr(settings, "VK_GROUP_TOKEN", "")
    if not token:
        return False
    if ticket.creator.is_staff:
        return False

    vk_id = _get_creator_vk_id(ticket)
    if not vk_id:
        return False

    _, message = _build_creator_message(ticket, created=created)
    api_version = getattr(settings, "VK_API_VERSION", "5.199")
    api_url = "https://api.vk.com/method/messages.send"
    recipient_params = _recipient_to_vk_params(vk_id)
    payload = {
        "access_token": token,
        "v": api_version,
        "random_id": int(time.time() * 1000),
        "message": message,
    }
    payload.update(recipient_params)

    try:
        response = requests.post(api_url, data=payload, timeout=10)
        data = response.json()
        if "error" in data:
            logger.warning(
                "VK creator notify error for ticket #%s: %s",
                ticket.id,
                data.get("error", {}).get("error_msg"),
            )
            return False
        return True
    except Exception:
        logger.exception("Failed to send VK creator notification for ticket #%s", ticket.id)
        return False


def send_creator_email_notification(ticket, created: bool) -> bool:
    if not getattr(settings, "NOTIFY_EMAIL_ENABLED", True):
        return False
    if ticket.creator.is_staff:
        return False

    email = _get_creator_email(ticket)
    if not email:
        return False

    subject, message = _build_creator_message(ticket, created=created)

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception("Failed to send email creator notification for ticket #%s", ticket.id)
        return False


def send_comment_notification(comment) -> dict[str, bool]:
    """Call this when a new non-internal comment is added to a ticket."""
    ticket = comment.ticket

    if comment.author == ticket.creator:
        return {"vk_sent": False, "email_sent": False}
    if comment.is_internal:
        return {"vk_sent": False, "email_sent": False}

    ticket_url = reverse("ticket_detail", kwargs={"ticket_id": ticket.id})
    site_url = getattr(settings, "SITE_URL", "").rstrip("/")
    ticket_link = f"{site_url}{ticket_url}" if site_url else ticket_url

    author_name = comment.author.get_full_name() or comment.author.username
    subject = f"[Ticket System] Новый ответ по тикету #{ticket.id}"
    message = (
        f"По вашему тикету добавлен новый ответ.\n\n"
        f"#{ticket.id}: {ticket.title}\n"
        f"От: {author_name}\n\n"
        f"Ссылка: {ticket_link}"
    )

    vk_sent = False
    email_sent = False

    if getattr(settings, "VK_NOTIFY_ENABLED", False) and not ticket.creator.is_staff:
        vk_id = _get_creator_vk_id(ticket)
        if vk_id:
            token = getattr(settings, "VK_GROUP_TOKEN", "")
            api_url = "https://api.vk.com/method/messages.send"
            recipient_params = _recipient_to_vk_params(vk_id)
            payload = {
                "access_token": token,
                "v": getattr(settings, "VK_API_VERSION", "5.199"),
                "random_id": int(time.time() * 1000),
                "message": message,
            }
            payload.update(recipient_params)
            try:
                response = requests.post(api_url, data=payload, timeout=10)
                data = response.json()
                if "error" not in data:
                    vk_sent = True
            except Exception:
                logger.exception("Failed to send VK comment notification for ticket #%s", ticket.id)

    if not ticket.creator.is_staff:
        email = _get_creator_email(ticket)
        if email:
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
                    recipient_list=[email],
                    fail_silently=False,
                )
                email_sent = True
            except Exception:
                logger.exception("Failed to send email comment notification for ticket #%s", ticket.id)

    return {"vk_sent": vk_sent, "email_sent": email_sent}


def send_ticket_notifications(ticket, created: bool) -> dict[str, bool]:
    email_sent = send_ticket_email_notification(ticket, created=created)
    vk_sent = send_ticket_vk_notification(ticket, created=created)
    creator_vk_sent = send_creator_vk_notification(ticket, created=created)
    creator_email_sent = send_creator_email_notification(ticket, created=created)
    return {
        "email_sent": email_sent,
        "vk_sent": vk_sent,
        "creator_vk_sent": creator_vk_sent,
        "creator_email_sent": creator_email_sent,
    }
