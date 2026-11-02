#!/usr/bin/env python3
"""Fast offline pre-check: will ADT Studio accept this ADT bundle for import?

Mirrors the static rules ADT Studio's ADT import applies (PR #803, editing
contract v1/v2). It is a pre-check, not the authority: ADT Studio's
`POST /api/books/preview-import` is the final gate.

Usage:  python3 check_studio_import.py <bundle-folder>
Exit code 0 = no errors (warnings may remain), 1 = errors found.
Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

ALLOWED_ROOT_ENTRIES = {
    "assets", "content", "images", "manifest.json", "index.html", "cover.png",
    "cover.jpg", "cover.jpeg", "cover.webp", "AGENTS.md", "CLAUDE.md",
    "imsmanifest.xml", ".build-hash", ".build-version", ".DS_Store", "Thumbs.db",
    "__MACOSX",
}
STANDARD_STYLESHEETS = {
    "content/tailwind_output.css",
    "assets/libs/fontawesome/css/all.min.css",
    "assets/fonts.css",
}
STANDARD_SCRIPTS = {
    "assets/offline-preloader.js", "assets/scorm.js", "assets/base.bundle.local.js",
    "assets/base.bundle.min.js", "assets/auto-fit.js", "assets/activities.bundle.local.js",
}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
        "source", "track", "wbr"}
IMAGE_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")
QUIZ_SECTION = re.compile(r"^(?:qz|quiz)[-_]?\d*", re.I)


class Node:
    def __init__(self, tag, attrs, parent):
        self.tag, self.attrs, self.parent = tag, attrs, parent
        self.children: list = []
        self.text = ""

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()

    def inside(self, other) -> bool:
        node = self
        while node is not None:
            if node is other:
                return True
            node = node.parent
        return False

    def text_content(self) -> str:
        if self.tag in ("script", "style"):
            return ""
        return self.text + "".join(child.text_content() for child in self.children)


class TreeBuilder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("#document", {}, None)
        self.current = self.root

    def handle_starttag(self, tag, attrs):
        node = Node(tag, {k: (v or "") for k, v in attrs}, self.current)
        self.current.children.append(node)
        if tag not in VOID:
            self.current = node

    def handle_startendtag(self, tag, attrs):
        self.current.children.append(Node(tag, {k: (v or "") for k, v in attrs}, self.current))

    def handle_endtag(self, tag):
        node = self.current
        while node is not None and node.tag != tag:
            node = node.parent
        if node is not None and node.parent is not None:
            self.current = node.parent

    def handle_data(self, data):
        self.current.text += data


def parse(path: Path) -> Node:
    builder = TreeBuilder()
    builder.feed(path.read_text(encoding="utf-8"))
    return builder.root


def normalize_local(value: str) -> str | None:
    value = unquote(value.strip().split("?", 1)[0].split("#", 1)[0])
    value = re.sub(r"^\./", "", value)
    if not value or re.match(r"^(?:[a-z]+:|/|\\)", value, re.I) or ".." in value.split("/"):
        return None
    return "/".join(part for part in value.split("/") if part and part != ".")


def inspect(bundle: Path) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    def error(where, message):
        errors.append(f"ERROR  {where}: {message}")

    def warn(where, message):
        warnings.append(f"WARN   {where}: {message}")

    pages_path = bundle / "content" / "pages.json"
    if not pages_path.exists():
        return {"errors": ["ERROR  content/pages.json is missing"], "warnings": [], "page_count": 0}
    pages = json.loads(pages_path.read_text(encoding="utf-8"))
    if not isinstance(pages, list) or not pages:
        return {"errors": ["ERROR  content/pages.json must be a nonempty array"], "warnings": [], "page_count": 0}
    if bundle.is_symlink() or any(p.is_symlink() for p in bundle.rglob("*")):
        return {"errors": ["ERROR  bundle contains a symlink"], "warnings": [], "page_count": len(pages)}
    page_hrefs = {page["href"] for page in pages}

    # Root entries and stray archives
    for entry in bundle.iterdir():
        if entry.name not in ALLOWED_ROOT_ENTRIES and entry.name not in page_hrefs:
            error(entry.name, "unexpected entry at the bundle root (move it outside the bundle)")
    for archive in [*bundle.rglob("*.zip"), *bundle.rglob("*.tar*"), *bundle.rglob("*.7z")]:
        error(str(archive.relative_to(bundle)), "archive inside the bundle folder")
    for asset in ("content/pdf-components.css",):
        if (bundle / asset).exists():
            warn(asset, "leftover custom stylesheet file; delete it once its rules are converted")

    seen_sections, seen_hrefs = set(), set()
    owners: dict[str, set[str]] = defaultdict(set)
    text_ids: set[str] = set()
    page_data_ids: dict[str, list[str]] = {}

    for page in pages:
        href, section_id = page["href"], page["section_id"]
        if normalize_local(href) != href or "/" in href or not href.endswith(".html"):
            error(str(href), "unsafe or nested page href; page HTML must be at the bundle root")
            continue
        if section_id in seen_sections:
            error("content/pages.json", f"duplicate section_id {section_id}")
        if href in seen_hrefs:
            error("content/pages.json", f"duplicate href {href}")
        seen_sections.add(section_id)
        seen_hrefs.add(href)
        if "/" in href:
            error(href, "page HTML must be at the bundle root")
        path = bundle / href
        if not path.exists():
            error(href, "listed in content/pages.json but missing")
            continue

        doc = parse(path)
        nodes = list(doc.walk())
        roots = [n for n in nodes if n.attrs.get("id") == "content"]
        if len(roots) != 1:
            error(href, f"expected exactly one #content root, found {len(roots)}")
            continue
        content = roots[0]
        quiz = bool(QUIZ_SECTION.match(section_id))
        sections = [
            n for n in content.walk()
            if n.tag == "section" and (
                n.attrs.get("data-section-id") == section_id
                or (quiz and n.attrs.get("data-id") == section_id)
            )
        ]
        if len(sections) != 1:
            error(href, f"expected one <section data-section-id=\"{section_id}\">, found {len(sections)}")
            continue
        section = sections[0]
        section_type = section.attrs.get("data-section-type", "").strip()
        if not section_type:
            error(href, "canonical <section> is missing data-section-type")
        elif section_type.startswith("activity_") and not section_type.startswith("activity_custom_") and section_type not in {
            "activity_multiple_choice", "activity_multi_select", "activity_true_false", "activity_fill_in_the_blank",
            "activity_fill_in_a_table", "activity_open_ended_answer", "activity_underline_text", "activity_matching",
            "activity_sorting", "activity_quiz", "activity_other",
        }:
            error(href, f"unknown activity type {section_type}; classify from actual behavior")
        for node in nodes:
            if node.tag == "style":
                error(href, "<style> elements are not supported by the import preparation contract")

        ids_in_order: list[str] = []
        for node in content.walk():
            data_id = node.attrs.get("data-id", "").strip()
            if node is not content and node.tag == "img" and node.inside(section) and not data_id:
                error(href, f"<img src=\"{node.attrs.get('src', '')}\"> inside the section has no data-id")
            if not data_id:
                continue
            if not node.inside(section):
                error(href, f"data-id \"{data_id}\" is outside the canonical <section>; Studio keeps only the section, so move it inside or remove it")
                continue
            if quiz and node is section:
                continue
            if data_id in ids_in_order:
                error(href, f"data-id \"{data_id}\" appears twice on this page")
            ids_in_order.append(data_id)
            owners[data_id].add(href)
            if data_id.startswith("activity_gen_"):
                warn(href, f"data-id \"{data_id}\" uses the reserved activity_gen_ prefix and will be renumbered")
            if node.tag == "img":
                if not IMAGE_ID.match(data_id):
                    error(href, f"image data-id \"{data_id}\" must match [a-zA-Z0-9][a-zA-Z0-9._-]*")
                src = normalize_local(node.attrs.get("src", "")) or ""
                same_id_files = [p for p in (bundle / "images").glob(f"{data_id}.*")]
                if same_id_files and f"images/{same_id_files[0].name}" != src:
                    warn(href, f"image \"{data_id}\" points at {src} but images/{same_id_files[0].name} exists; Studio imports the file named after the data-id")
            elif node.text_content().strip() or node.attrs.get("alt", "").strip():
                text_ids.add(data_id)
        page_data_ids[href] = ids_in_order

        # Linked resources anywhere in the document
        for node in nodes:
            attr = {"link": "href", "script": "src", "img": "src", "source": "src",
                    "audio": "src", "video": "src"}.get(node.tag)
            value = node.attrs.get(attr, "").strip() if attr else ""
            if not value or value.startswith(("#", "data:")):
                continue
            if re.match(r"^(?:https?:)?//", value, re.I):
                google_fonts = node.tag == "link" and (
                    value in ("https://fonts.googleapis.com", "https://fonts.gstatic.com")
                    or value.lower().startswith("https://fonts.googleapis.com/css2?")
                )
                if not google_fonts:
                    error(href, f"remote asset {value}")
                continue
            local = normalize_local(value)
            if local is None:
                error(href, f"unsafe asset path {value}")
                continue
            if not (bundle / local).exists():
                error(href, f"missing local asset {value}")
            rel = node.attrs.get("rel", "").split()
            if node.tag == "link" and "stylesheet" in rel and local not in STANDARD_STYLESHEETS:
                error(href, f"custom stylesheet {value}; convert its rules to Tailwind classes or inline style attributes")
            elif node.tag == "script" and local not in STANDARD_SCRIPTS:
                error(href, f"custom script {value}; remove it (only the inline adtRegisterCustomActivity call is supported)")
            elif node.tag in ("img", "source", "audio", "video") and not local.startswith("images/"):
                error(href, f"media {value} must live under images/")

        # Activity markers
        if section_type.startswith("activity_custom_"):
            if not (section.attrs.get("aria-label", "").strip() or section.attrs.get("aria-labelledby", "").strip()):
                error(href, "custom activity <section> needs aria-labelledby or aria-label")
            if not any(n.attrs.get("role") == "status" or n.attrs.get("aria-live") for n in section.walk()):
                error(href, "custom activity needs a role=\"status\" aria-live=\"polite\" feedback element")
            if not any(n.tag == "script" and "adtRegisterCustomActivity" in n.text for n in section.walk()):
                error(href, "custom activity needs an inline window.adtRegisterCustomActivity(section, { validate, reset }) call")
        elif not section_type.startswith("activity_") and not quiz:
            interactive = any(
                n.tag in ("button", "select", "textarea")
                or (n.tag == "input" and n.attrs.get("type", "text").lower() != "hidden")
                or any(a.startswith("data-activity-") for a in n.attrs)
                or n.attrs.get("draggable") == "true"
                for n in section.walk() if n is not section
            )
            if interactive and section.attrs.get("data-adt-non-activity", "").lower() != "true":
                warn(href, "interactive controls in a non-activity section; Studio will ask for review unless it gets an activity_* type or data-adt-non-activity=\"true\"")
        if section_type.startswith("activity_") and section_type != "activity_open_ended_answer" and not quiz and not section_type.startswith("activity_custom_"):
            if any(n.tag == "script" and not n.inside(section) and "window.correctAnswers" in n.text for n in nodes):
                warn(href, "grading depends on window.correctAnswers outside the canonical section; verify answer-key recovery after Studio export, because preview acceptance alone does not preserve this configuration")

    # Book-wide uniqueness
    for data_id, hrefs in sorted(owners.items()):
        if len(hrefs) > 1:
            listed = ", ".join(sorted(hrefs)[:4]) + (" …" if len(hrefs) > 4 else "")
            error("book", f"data-id \"{data_id}\" is used on {len(hrefs)} pages ({listed}); every page needs its own id")

    # index.html is not necessarily in the navigation spine. Inspect its own
    # presentation dependencies too; don't falsely certify an unexamined shell.
    index = bundle / "index.html"
    if not index.is_file():
        error("index.html", "missing reader entry point")
    elif "index.html" not in page_hrefs:
        for node in parse(index).walk():
            if node.tag == "style":
                error("index.html", "<style> elements are not supported")
            attr = "href" if node.tag == "link" else "src" if node.tag == "script" else None
            value = node.attrs.get(attr, "") if attr else ""
            if not value:
                continue
            if value.startswith("https://fonts.googleapis.com/css2?") and node.tag == "link":
                continue
            local = normalize_local(value)
            if local is None:
                error("index.html", f"unsafe or remote asset {value}")
            elif not (bundle / local).is_file():
                error("index.html", f"missing local asset {value}")
            elif node.tag == "link" and "stylesheet" in node.attrs.get("rel", "").split() and local not in STANDARD_STYLESHEETS:
                error("index.html", f"custom stylesheet {value}")
            elif node.tag == "script" and local not in STANDARD_SCRIPTS:
                error("index.html", f"custom script {value}")

    # Text catalogs
    i18n = bundle / "content" / "i18n"
    for lang_dir in sorted(p for p in i18n.iterdir() if p.is_dir()) if i18n.exists() else []:
        texts_path = lang_dir / "texts.json"
        if not texts_path.exists():
            continue
        texts = json.loads(texts_path.read_text(encoding="utf-8"))
        missing = sorted(text_ids - texts.keys())
        if missing:
            warn(f"content/i18n/{lang_dir.name}/texts.json", f"{len(missing)} page text ids have no entry, e.g. {missing[:5]}")

    # Editing contract bookkeeping (bundles exported with a manifest)
    manifest_path = bundle / "manifest.json"
    if manifest_path.exists():
        contract = json.loads(manifest_path.read_text(encoding="utf-8")).get("editingContract")
        if contract:
            order = [(p.get("sectionId"), p.get("href")) for p in contract.get("pageOrder", [])]
            if order != [(p["section_id"], p["href"]) for p in pages]:
                error("manifest.json", "editingContract.pageOrder does not match content/pages.json")
            declared = contract.get("pageDataIds") or {}
            for href, ids in page_data_ids.items():
                if href in declared and declared[href] and declared[href] != ids:
                    error("manifest.json", f"editingContract.pageDataIds[\"{href}\"] does not list the page's data-ids in document order")
                if href not in declared and contract.get("version", 0) >= 2:
                    error("manifest.json", f"editingContract.pageDataIds has no entry for {href}")

    return {"errors": errors, "warnings": warnings, "page_count": len(pages),
            "passed": not errors, "authority": "offline preflight, not Studio acceptance or visual/behavior certification"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--json", action="store_true", help="Machine-readable findings")
    args = parser.parse_args()
    try:
        result = inspect(args.bundle)
    except (ValueError, OSError, KeyError, TypeError) as error:
        result = {"errors": [f"ERROR  malformed bundle: {error}"], "warnings": [], "page_count": 0, "passed": False}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for line in result["errors"] + result["warnings"]:
            print(line)
        print(f'\n{len(result["errors"])} error(s), {len(result["warnings"])} warning(s) across {result["page_count"]} pages')
    sys.exit(1 if result["errors"] else 0)
