"""Convert the supplied MHTML archive into a safe, self-contained writing library."""

from __future__ import annotations

import hashlib
import html
import json
import re
import sys
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse
from zipfile import ZipFile

ALLOWED = {"p", "ul", "ol", "li", "strong", "em", "b", "i", "blockquote", "h2", "h3", "h4", "pre", "code", "a", "br", "hr", "table", "thead", "tbody", "tr", "th", "td", "img"}
VOID = {"br", "hr", "img"}
IMAGE_EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif", "image/svg+xml": ".svg"}


def safe_url(value: str) -> str | None:
    return value if urlparse(value).scheme in {"http", "https"} else None


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\ufffd", "’")).strip()


class MediaStore:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.by_digest: dict[str, str] = {}
        self.local_count = 0
        self.remote_count = 0

    def preserve(self, url: str, part) -> str:
        if not part:
            self.remote_count += 1
            return url
        payload = part.get_payload(decode=True) or b""
        if not payload:
            self.remote_count += 1
            return url
        digest = hashlib.sha256(payload).hexdigest()
        if digest in self.by_digest:
            return self.by_digest[digest]
        extension = IMAGE_EXTENSIONS.get(part.get_content_type(), Path(urlparse(url).path).suffix.lower())
        if extension not in IMAGE_EXTENSIONS.values():
            extension = ".jpg"
        relative = f"assets/library/{digest[:24]}{extension}"
        (self.directory / f"{digest[:24]}{extension}").write_bytes(payload)
        self.by_digest[digest] = relative
        self.local_count += 1
        return relative


class LessonExtractor(HTMLParser):
    def __init__(self, image_parts: dict[str, object], media: MediaStore) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.buffer: list[str] = []
        self.blocks: list[str] = []
        self.images: list[dict[str, str]] = []
        self.image_parts = image_parts
        self.media = media

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        classes = (values.get("class") or "").split()
        if not self.depth and tag == "div" and "tiptap" in classes and "skool-editor2" in classes:
            self.depth, self.buffer = 1, []
            return
        if not self.depth:
            return
        if tag not in VOID:
            self.depth += 1
        if tag not in ALLOWED:
            return
        rendered = ""
        if tag == "a" and safe_url(values.get("href") or ""):
            rendered = f' href="{html.escape(values["href"], quote=True)}" target="_blank" rel="noopener noreferrer"'
        elif tag == "img" and safe_url(values.get("src") or ""):
            original = values["src"]
            source = self.media.preserve(original, self.image_parts.get(original))
            alt = clean(values.get("alt") or values.get("title") or "Lesson image")
            rendered = f' src="{html.escape(source, quote=True)}" alt="{html.escape(alt, quote=True)}" loading="lazy"'
            self.images.append({"src": source, "alt": alt})
        elif tag == "img":
            return
        self.buffer.append(f"<{tag}{rendered}>")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if not self.depth:
            return
        if tag not in VOID:
            self.depth -= 1
        if self.depth == 0:
            cleaned = "".join(self.buffer).strip()
            if cleaned:
                self.blocks.append(cleaned)
            return
        if tag in ALLOWED and tag not in VOID:
            self.buffer.append(f"</{tag}>")

    def handle_data(self, data):
        if self.depth:
            self.buffer.append(html.escape(data))


class MetaExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title, self.description, self.image, self.in_title = "", "", "", False

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "title":
            self.in_title = True
        if tag == "meta":
            key, value = values.get("name") or values.get("property"), values.get("content") or ""
            if key == "description" and not self.description:
                self.description = value
            if key == "og:image" and safe_url(value):
                self.image = value

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data


def title_from(raw: str) -> str:
    value = re.sub(r"\s*[·|]\s*AI Writing Skool.*$", "", clean(raw), flags=re.I)
    return re.sub(r"\s+-\s+(?:AIWS Asset Hub|Digital (?:Writing|Niche|Mindset) Fundamentals|Exclusive Mini-Courses|Ship 30 for 30(?: - October 2026)?)$", "", value, flags=re.I).strip()


def kind_from(title: str) -> str:
    upper = title.upper()
    for marker, label in (("[PROMPT]", "Prompt"), ("[SKILL]", "Skill"), ("[CHEAT SHEET]", "Cheat sheet"), ("[REPLAY]", "Replay"), ("[BONUS]", "Bonus"), ("ASSIGNMENT", "Assignment"), ("TEMPLATE", "Template"), ("REPLAY", "Replay")):
        if marker in upper:
            return label
    return "Lesson"


def parse_mhtml(raw: bytes):
    message = BytesParser(policy=policy.default).parsebytes(raw)
    source = clean(message.get("Snapshot-Content-Location", ""))
    parts = list(message.walk())
    for part in parts:
        if part.get_content_type() == "text/html":
            payload = part.get_payload(decode=True) or b""
            return payload.decode("utf-8", "replace"), source or clean(part.get("Content-Location", "")), parts
    return "", source, parts


def video_links(meta: MetaExtractor, parts, image_parts: dict[str, object], media: MediaStore):
    videos: list[dict[str, str]] = []
    seen: set[str] = set()
    youtube = re.search(r"i\.ytimg\.com/vi/([\w-]{6,})/", meta.image)
    if youtube:
        video_id = youtube.group(1)
        thumb = media.preserve(meta.image, image_parts.get(meta.image))
        videos.append({"provider": "YouTube", "url": f"https://www.youtube.com/watch?v={video_id}", "thumbnail": thumb})
        seen.add(video_id)
    for part in parts:
        location = clean(str(part.get("Content-Location", "")))
        match = re.search(r"loom\.com/embed/([a-f0-9]{16,})", location, re.I)
        if not match or match.group(1) in seen or part.get_content_type() != "text/html":
            continue
        video_id = match.group(1)
        thumbnail_url = next((url for url in image_parts if f"thumbnails/{video_id}" in url), "")
        thumbnail = media.preserve(thumbnail_url, image_parts.get(thumbnail_url)) if thumbnail_url else ""
        videos.append({"provider": "Loom", "url": f"https://www.loom.com/share/{video_id}", "thumbnail": thumbnail})
        seen.add(video_id)
    return videos


def build_record(name: str, raw: bytes, index: int, media: MediaStore):
    page, source, parts = parse_mhtml(raw)
    if not page:
        return None
    image_parts = {clean(str(part.get("Content-Location", ""))): part for part in parts if part.get_content_type().startswith("image/")}
    meta = MetaExtractor()
    meta.feed(page)
    lesson = LessonExtractor(image_parts, media)
    lesson.feed(page)
    path = PurePosixPath(name)
    pieces = path.parts
    course = pieces[2] if len(pieces) > 2 else "AI Writing Library"
    collection = pieces[3] if len(pieces) > 4 else course
    title = title_from(meta.title or path.stem)
    content = max(lesson.blocks, key=len, default="")
    plain = clean(re.sub(r"<[^>]+>", " ", html.unescape(content)))
    videos = video_links(meta, parts, image_parts, media)
    return {
        "id": f"writing-{index:03d}", "title": title, "course": clean(course), "collection": clean(collection),
        "kind": kind_from(title), "description": clean(meta.description) or plain[:260],
        "source": source if safe_url(source) else "", "content": content, "hasContent": bool(content),
        "images": lesson.images, "videos": videos,
    }


def main() -> int:
    if len(sys.argv) not in {3, 4}:
        print("Usage: import_library.py <archive.zip> <output.json> [media-directory]", file=sys.stderr)
        return 2
    archive_path, output_path = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    media_directory = Path(sys.argv[3]).resolve() if len(sys.argv) == 4 else output_path.parent.parent / "assets" / "library"
    media_directory.mkdir(parents=True, exist_ok=True)
    for existing in media_directory.iterdir():
        if existing.is_file():
            existing.unlink()
    media = MediaStore(media_directory)
    with ZipFile(archive_path) as archive:
        names = sorted(name for name in archive.namelist() if name.lower().endswith(".mhtml") and "_files/" not in name)
        records = [record for index, name in enumerate(names, 1) if (record := build_record(name, archive.read(name), index, media))]
    pillars = []
    for course in dict.fromkeys(item["course"] for item in records):
        items = [item for item in records if item["course"] == course]
        pillars.append({"name": course, "count": len(items), "collections": len(set(item["collection"] for item in items))})
    payload = {"title": "AI Writing", "generated": "2026-10-16", "source": "AI Writing community archive supplied by the site owner on 15 October 2026.", "count": len(records), "pillars": pillars, "records": records}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({"records": len(records), "withContent": sum(1 for item in records if item["hasContent"]), "withImages": sum(1 for item in records if item["images"]), "withVideos": sum(1 for item in records if item["videos"]), "localMedia": media.local_count, "remoteFallbacks": media.remote_count, "output": str(output_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
