import re
from dataclasses import dataclass
from io import BytesIO

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

from app.core.config import settings
from app.core.errors import AppError


@dataclass(slots=True)
class ChunkDraft:
    heading_path: str
    content: str
    token_count: int


def read_limited_response(response: httpx.Response) -> bytes:
    content = bytearray()
    for part in response.iter_bytes():
        content.extend(part)
        if len(content) > settings.source_max_bytes:
            raise AppError(413, "SOURCE_TOO_LARGE", "The source exceeds the maximum allowed size.")
    return bytes(content)


def extract_pdf(content: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(content))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as error:
        raise AppError(422, "INVALID_PDF", "The PDF could not be read.") from error


def clean_html(raw_content: str) -> tuple[str, str | None]:
    soup = BeautifulSoup(raw_content, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else None
    removable = (
        "script, style, nav, footer, aside, form, noscript, iframe, .cookie, .advertisement, .ad"
    )
    for node in soup.select(removable):
        node.decompose()

    blocks: list[str] = []
    for node in soup.select("h1, h2, h3, h4, h5, h6, p, li, pre, table"):
        if node.find_parent(["li", "pre", "table"]):
            continue
        if node.name.startswith("h"):
            level = int(node.name[1])
            blocks.append(f"{'#' * level} {node.get_text(' ', strip=True)}")
        elif node.name == "li":
            blocks.append(f"- {node.get_text(' ', strip=True)}")
        elif node.name == "pre":
            blocks.append(f"```\n{node.get_text(chr(10), strip=True)}\n```")
        elif node.name == "table":
            rows = [
                " | ".join(cell.get_text(" ", strip=True) for cell in row.select("th, td"))
                for row in node.select("tr")
            ]
            blocks.append("\n".join(row for row in rows if row))
        else:
            blocks.append(node.get_text(" ", strip=True))
    return clean_plain_text("\n\n".join(blocks)), title


def clean_plain_text(raw_content: str) -> str:
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in raw_content.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def create_semantic_chunks(content: str) -> list[ChunkDraft]:
    heading_stack: list[str] = []
    chunks: list[ChunkDraft] = []
    buffer: list[str] = []
    in_code_block = False

    def flush() -> None:
        text = "\n".join(buffer).strip()
        if text:
            chunks.append(
                ChunkDraft(
                    heading_path=" > ".join(heading_stack),
                    content=text,
                    token_count=estimate_token_count(text),
                )
            )
        buffer.clear()

    for line in content.splitlines():
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading and not in_code_block:
            flush()
            level = len(heading.group(1))
            heading_stack[level - 1 :] = [heading.group(2).strip()]
            continue
        if line.startswith("```"):
            if in_code_block:
                buffer.append(line)
                in_code_block = False
                flush()
            else:
                flush()
                buffer.append(line)
                in_code_block = True
            continue
        if not line and not in_code_block:
            flush()
        else:
            buffer.append(line)
    flush()
    return chunks


def estimate_token_count(content: str) -> int:
    return max(1, round(len(content.split()) * 1.3))


def count_words(content: str) -> int:
    return len(re.findall(r"\b\w+\b", content, flags=re.UNICODE))


def detect_language(content: str) -> str:
    prose = re.sub(r"```.*?```", "", content, flags=re.DOTALL)
    prose = re.sub(r"https?://\S+|`[^`]*`", "", prose)
    letters = [character.lower() for character in prose[:12000] if character.isalpha()]
    if not letters:
        return "und"
    russian = sum("а" <= character <= "я" or character == "ё" for character in letters)
    if russian / len(letters) >= 0.3:
        return "ru"
    latin = sum("a" <= character <= "z" for character in letters)
    return "en" if latin / len(letters) > 0.8 else "und"
