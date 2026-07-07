import re
from django.core.exceptions import ValidationError


def validate_password_strength(password):
    """
    Validate that the password meets minimum requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    errors = []

    if len(password) < 8:
        errors.append("8+ chars")

    if not re.search(r"[A-Z]", password):
        errors.append("1 uppercase")

    if not re.search(r"[a-z]", password):
        errors.append("1 lowercase")

    if not re.search(r"[0-9]", password):
        errors.append("1 number")

    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("1 special char")

    if errors:
        error_message = "Password must contain " + ", ".join(errors) + "."
        raise ValidationError(error_message)

    return password