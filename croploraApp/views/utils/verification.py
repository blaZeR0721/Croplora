import logging
import random

from croploraApp.views.utils.redis_client import redis_client
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger("croplora")

VERIFICATION_CODE_TTL_SECONDS = 180
RESEND_LIMIT = 3
RESEND_WINDOW_SECONDS = 600


def verification_pending(user):
    return not user.is_verified


def onboarding_pending(user):
    return user.organization_id is None


def generate_and_send_verification_code(user):
    code = str(random.randint(100000, 999999))
    redis_client.setex(f"verify:{user.id}", VERIFICATION_CODE_TTL_SECONDS, code)

    if settings.REQUIRE_EMAIL_VERIFICATION:
        send_mail(
            subject="Verify your email",
            message=f"Your verification code is {code}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )
    else:
        logger.info(f"[VERIFICATION CODE] {user.email} -> {code}")


def check_resend_allowed(user):
    key = f"resend_count:{user.id}"
    count = redis_client.get(key)

    if count is None:
        redis_client.setex(key, RESEND_WINDOW_SECONDS, 1)
        return True

    if int(count) >= RESEND_LIMIT:
        return False

    redis_client.incr(key)
    return True
