"""Delivery adapters behind a common interface (spec §7).

In-app push goes through the event hub; Telegram and SMTP email are external channels. Each
adapter degrades gracefully (returns False, logs) when unconfigured, so the engine can record
per-channel delivery status without crashing.
"""

from __future__ import annotations

import logging
import smtplib
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from email.message import EmailMessage

import httpx

from app.core.config import Settings
from app.core.config import settings as default_settings
from app.core.events import event_hub
from app.db.models import Analysis, Article, Config

log = logging.getLogger(__name__)

_ARROWS = {"bullish": "▲", "bearish": "▼", "neutral": "◆", "unclear": "◇"}


def format_alert_message(analysis: Analysis, article: Article | None) -> str:
    arrow = _ARROWS.get(analysis.expected_direction or "", "•")
    instruments = ", ".join(analysis.instruments_affected or ["BRENT"])
    summary = analysis.headline_summary or (article.title if article else "")
    lines = [
        f"\U0001f6e2 {arrow} {instruments}  ·  importance {analysis.importance_score or 0:.0f}",
        summary,
        f"{analysis.event_category} · {analysis.expected_direction} "
        f"· {analysis.magnitude} · {analysis.time_horizon}",
    ]
    if article and article.url:
        lines.append(article.url)
    return "\n".join(line for line in lines if line)


def build_event(analysis: Analysis, article: Article | None, config: Config) -> dict:
    return {
        "type": "alert",
        "analysis_id": analysis.id,
        "config_id": config.id,
        "importance_score": analysis.importance_score,
        "event_category": analysis.event_category,
        "direction": analysis.expected_direction,
        "magnitude": analysis.magnitude,
        "instruments": analysis.instruments_affected,
        "headline_summary": analysis.headline_summary,
        "url": article.url if article else None,
    }


class Notifier(ABC):
    name: str

    @property
    @abstractmethod
    def configured(self) -> bool: ...

    @abstractmethod
    def send(self, *, text: str, target: str | None) -> bool: ...


class TelegramNotifier(Notifier):
    name = "telegram"

    def __init__(self, bot_token: str | None) -> None:
        self.bot_token = bot_token

    @property
    def configured(self) -> bool:
        return bool(self.bot_token)

    def send(self, *, text: str, target: str | None) -> bool:
        if not self.configured or not target:
            return False
        try:
            resp = httpx.post(
                f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
                json={"chat_id": target, "text": text, "disable_web_page_preview": True},
                timeout=10.0,
            )
            if resp.status_code == 200:
                return True
            log.warning("Telegram send failed: %s %s", resp.status_code, resp.text[:200])
            return False
        except httpx.HTTPError:
            log.exception("Telegram send error")
            return False


class EmailNotifier(Notifier):
    name = "email"

    def __init__(self, settings: Settings = default_settings) -> None:
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.user = settings.smtp_user
        self.password = settings.smtp_pass
        self.from_email = settings.alert_from_email

    @property
    def configured(self) -> bool:
        return bool(self.host and self.from_email)

    def send(self, *, text: str, target: str | None) -> bool:
        if not self.configured or not target:
            return False
        try:
            msg = EmailMessage()
            msg["From"] = self.from_email
            msg["To"] = target
            msg["Subject"] = "Oil News Alert"
            msg.set_content(text)
            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                server.starttls()
                if self.user and self.password:
                    server.login(self.user, self.password)
                server.send_message(msg)
            return True
        except (smtplib.SMTPException, OSError):
            log.exception("Email send error")
            return False


@dataclass
class Notifiers:
    telegram: Notifier | None = None
    email: Notifier | None = None
    publish_in_app: Callable[[dict], None] = field(default=lambda event: None)


def build_default_notifiers(settings: Settings = default_settings) -> Notifiers:
    return Notifiers(
        telegram=(
            TelegramNotifier(settings.telegram_bot_token) if settings.telegram_bot_token else None
        ),
        email=EmailNotifier(settings) if settings.smtp_host else None,
        publish_in_app=event_hub.publish,
    )
