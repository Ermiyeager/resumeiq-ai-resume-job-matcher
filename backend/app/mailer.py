"""Outgoing email.

Development uses ConsoleMailer, which prints links to the server log.
Plug in an SMTP or provider-backed mailer for production by calling set_mailer().
"""

from __future__ import annotations

import logging
from typing import Protocol

log = logging.getLogger("resumeiq.mail")


class Mailer(Protocol):
    def send(self, to: str, subject: str, body: str) -> None: ...


class ConsoleMailer:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []

    def send(self, to: str, subject: str, body: str) -> None:
        self.sent.append((to, subject, body))
        log.info("Email to %s | %s\n%s", to, subject, body)


_mailer: Mailer = ConsoleMailer()


def get_mailer() -> Mailer:
    return _mailer


def set_mailer(mailer: Mailer) -> None:
    global _mailer
    _mailer = mailer
