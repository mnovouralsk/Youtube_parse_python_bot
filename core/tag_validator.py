import re

ALLOWED_TAGS = {"b", "i"}  # только эти теги разрешены


def clean_html_for_telegram(text: str) -> str:
    if not text:
        return ""

    # Заменяем все варианты <br>, <br/> на перенос строки
    text = re.sub(r"<\s*br\s*/?\s*>", "\n", text, flags=re.IGNORECASE)

    # Удаляем все теги кроме <b> и <i>
    text = re.sub(
        r"</?(?!\s*(?:b|i)\b)[a-zA-Z0-9]+[^>]*>", "", text, flags=re.IGNORECASE
    )

    # Убираем лишние пробелы вокруг переносов строк
    text = re.sub(r"\n\s+", "\n", text)
    text = re.sub(r"\s+\n", "\n", text)

    return text


def is_only_allowed_tags(text: str) -> bool:
    tags = re.findall(r"<\s*/?\s*([a-zA-Z0-9]+)[^>]*>", text)
    for t in tags:
        if t.lower() not in ALLOWED_TAGS:
            return False
    return True
