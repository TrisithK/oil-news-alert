"""Send a test Telegram alert: `make telegram-test` (optionally `CHAT=<chat_id>`).

Confirms TELEGRAM_BOT_TOKEN + a chat id actually deliver before you rely on them for alerts.
"""

from __future__ import annotations

import sys

from app.core.config import settings
from app.core.logging import setup_logging
from worker.alerting.notifier import TelegramNotifier


def main() -> None:
    setup_logging()

    if not settings.telegram_bot_token:
        print("TELEGRAM_BOT_TOKEN is not set in .env — create a bot via @BotFather first.")
        return

    chat_id = sys.argv[1] if len(sys.argv) > 1 else settings.telegram_default_chat_id
    if not chat_id:
        print(
            "No chat id. Pass one (`make telegram-test CHAT=12345`) "
            "or set TELEGRAM_DEFAULT_CHAT_ID."
        )
        print(
            "Tip: message your bot once, then open "
            "https://api.telegram.org/bot<TOKEN>/getUpdates to find your chat id."
        )
        return

    notifier = TelegramNotifier(settings.telegram_bot_token)
    ok = notifier.send(
        text=(
            "\U0001f6e2 Oil News Alert — test message. "
            "If you can read this, Telegram alerts are wired. ✓"
        ),
        target=str(chat_id),
    )
    if ok:
        print("Telegram send: OK ✓ — check your chat.")
    else:
        print(
            "Telegram send: FAILED ✗ — verify the token and chat id (see the logged error above)."
        )


if __name__ == "__main__":
    main()
