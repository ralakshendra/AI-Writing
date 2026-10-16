"""Convert the supplied MHTML archive into a safe, self-contained writing library."""

from __future__ import annotations

import hashlib
import html
import json
import mimetypes
import posixpath
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


class ArchivePart:
    """Small adapter that lets saved-HTML assets use the MHTML media pipeline."""

    def __init__(self, payload: bytes, content_type: str) -> None:
        self.payload = payload
        self.content_type = content_type

    def get_payload(self, decode=True):
        return self.payload

    def get_content_type(self):
        return self.content_type


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
        elif tag == "img" and (safe_url(values.get("src") or "") or values.get("src") in self.image_parts):
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
        self.title, self.description, self.image, self.canonical, self.in_title = "", "", "", "", False

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
            if key == "og:url" and safe_url(value):
                self.canonical = value
        if tag == "link" and "canonical" in (values.get("rel") or "").lower() and safe_url(values.get("href") or ""):
            self.canonical = values["href"]

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


def parse_html(name: str, raw: bytes, archive: ZipFile):
    page = raw.decode("utf-8", "replace")
    meta = MetaExtractor()
    meta.feed(page)
    current_page = re.search(r'https://www\.skool\.com/[^"\'<>\\ ]+/classroom/[^"\'<>\\ ]+\?md=[a-f0-9]+', page, re.I)
    image_parts: dict[str, object] = {}
    for source in re.findall(r'<img[^>]+src=["\']([^"\']+)', page, re.I):
        if safe_url(source) or source.startswith("data:"):
            continue
        candidate = posixpath.normpath(posixpath.join(posixpath.dirname(name), source.replace("\\", "/")))
        try:
            payload = archive.read(candidate)
        except KeyError:
            continue
        content_type = mimetypes.guess_type(candidate)[0] or "image/jpeg"
        image_parts[source] = ArchivePart(payload, content_type)
    return page, (current_page.group(0) if current_page else meta.canonical), [], image_parts


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


def build_record(name: str, raw: bytes, index: int, media: MediaStore, archive: ZipFile):
    if name.lower().endswith(".mhtml"):
        page, source, parts = parse_mhtml(raw)
        supplied_image_parts = None
    else:
        page, source, parts, supplied_image_parts = parse_html(name, raw, archive)
    if not page:
        return None
    image_parts = supplied_image_parts or {clean(str(part.get("Content-Location", ""))): part for part in parts if part.get_content_type().startswith("image/")}
    meta = MetaExtractor()
    meta.feed(page)
    lesson = LessonExtractor(image_parts, media)
    lesson.feed(page)
    path = PurePosixPath(name)
    pieces = path.parts
    folders = [clean(piece) for piece in pieces[2:-1]]
    course = folders[0] if folders else "AI Writing Library"
    collection = folders[1] if len(folders) > 1 else course
    # Saved HTML pages occasionally contain stale metadata from the page viewed
    # immediately before saving. The supplied filename is the authoritative label.
    title = title_from(path.stem if name.lower().endswith(".html") else (meta.title or path.stem))
    content = max(lesson.blocks, key=len, default="")
    plain = clean(re.sub(r"<[^>]+>", " ", html.unescape(content)))
    videos = video_links(meta, parts, image_parts, media)
    return {
        "id": f"writing-{index:03d}", "title": title, "course": clean(course), "collection": clean(collection),
        "folders": folders, "archivePath": name,
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
        mhtml_names = sorted(name for name in archive.namelist() if name.lower().endswith(".mhtml") and "_files/" not in name.lower())
        html_names = sorted(name for name in archive.namelist() if name.lower().endswith(".html") and "_files/" not in name.lower())
        names = mhtml_names + html_names
        records = [record for index, name in enumerate(names, 1) if (record := build_record(name, archive.read(name), index, media, archive))]
    pillars = []
    for course in dict.fromkeys(item["course"] for item in records):
        items = [item for item in records if item["course"] == course]
        pillars.append({"name": course, "count": len(items), "collections": len(set(item["collection"] for item in items))})
    folder_index = []
    paths = []
    for item in records:
        for depth in range(1, len(item["folders"]) + 1):
            prefix = item["folders"][:depth]
            if prefix not in paths:
                paths.append(prefix)
    for prefix in paths:
        descendants = [item for item in records if item["folders"][:len(prefix)] == prefix]
        direct = [item for item in descendants if len(item["folders"]) == len(prefix)]
        children = {item["folders"][len(prefix)] for item in descendants if len(item["folders"]) > len(prefix)}
        folder_index.append({"path": prefix, "name": prefix[-1], "count": len(descendants), "directCount": len(direct), "childCount": len(children)})
    payload = {
        "title": "AI Writing", "rootName": "AI Writing Community", "generated": "2026-10-16",
        "source": "AI Writing community archive supplied by the site owner on 15 October 2026.",
        "count": len(records), "archiveAudit": {"sourcePages": len(names), "importedPages": len(records), "missingPages": len(names) - len(records), "mhtmlPages": len(mhtml_names), "htmlPages": len(html_names)},
        "pillars": pillars, "folderIndex": folder_index, "records": records,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({"records": len(records), "withContent": sum(1 for item in records if item["hasContent"]), "withImages": sum(1 for item in records if item["images"]), "withVideos": sum(1 for item in records if item["videos"]), "localMedia": media.local_count, "remoteFallbacks": media.remote_count, "output": str(output_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
