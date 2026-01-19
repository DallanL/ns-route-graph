import re


def format_phone_number(number: str) -> str:
    """Formats a 10 or 11 digit number as (NPA) NXX-XXXX."""
    digits = re.sub(r"\D", "", number)

    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]

    if len(digits) == 10:
        return f"({digits[0:3]}) {digits[3:6]}-{digits[6:]}"

    return number


def generate_portal_link(domain: str, type_hint: str, id_value: str) -> str:
    """Generates a deep link path to the portal based on type."""

    if type_hint == "ingress":  # DID
        return "/portal/inventory/index/phonenumbers"

    elif type_hint == "user":
        # Link to answering rules
        return f"/portal/answerrules/index/{id_value}@{domain}"

    elif type_hint == "call_queue":
        return "/portal/callqueues"

    elif type_hint == "auto_attendant":
        # ID is usually "user:prompt"
        if ":" in id_value:
            user, prompt = id_value.split(":", 1)
            return f"/portal/attendants/edit/{user}@{domain}/{prompt}"
        else:
            return "/portal/attendants"

    elif type_hint == "voicemail":
        clean_user = id_value.replace("vmail_", "")
        return f"/portal/users/edit/voicemail/{clean_user}@{domain}"

    elif type_hint == "conference":
        return "/portal/conferences"

    return ""
