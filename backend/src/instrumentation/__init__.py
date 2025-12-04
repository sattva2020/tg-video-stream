# -*- coding: utf-8 -*-
"""
Модуль инструментирования приложения.
Включает Sentry, трейсинг и другие инструменты мониторинга.
"""

from .sentry import (
    init_sentry,
    capture_exception,
    capture_message,
    set_user_context,
    set_extra_context,
    add_breadcrumb,
    SentryContext,
    sentry_span,
)

__all__ = [
    "init_sentry",
    "capture_exception",
    "capture_message", 
    "set_user_context",
    "set_extra_context",
    "add_breadcrumb",
    "SentryContext",
    "sentry_span",
]
