#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from email.header import decode_header
from email.utils import getaddresses
from importlib.metadata import PackageNotFoundError, distribution, distributions
from pathlib import Path

try:
    from packaging.utils import canonicalize_name
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "packaging is required. Run this inside the project virtual environment."
    ) from exc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "third-party-notices.md"
LICENSECHECK = PROJECT_ROOT / ".venv" / "bin" / "licensecheck"

LICENSE_ALIASES = {
    "": "UNKNOWN",
    "0BSD": "0BSD",
    "3-CLAUSE BSD LICENSE": "BSD-3-Clause",
    "APACHE 2.0": "Apache-2.0",
    "APACHE LICENSE 2.0": "Apache-2.0",
    "APACHE SOFTWARE LICENSE": "Apache-2.0",
    "APACHE-2.0": "Apache-2.0",
    "BSD": "BSD",
    "BSD LICENSE": "BSD",
    "BSD-2-CLAUSE": "BSD-2-Clause",
    "BSD-3-CLAUSE": "BSD-3-Clause",
    "FREEBSD": "BSD-2-Clause",
    "ISC LICENSE _ISCL_": "ISC",
    "LGPL-2.1-ONLY": "LGPL-2.1-only",
    "MIT": "MIT",
    "MIT LICENSE": "MIT",
    "MIT-CMU": "MIT-CMU",
    "MOZILLA PUBLIC LICENSE 2.0 _MPL 2.0_": "MPL-2.0",
    "MPL-2.0": "MPL-2.0",
    "PSF-2.0": "PSF-2.0",
    "PUBLIC DOMAIN": "Public Domain",
    "PYTHON SOFTWARE FOUNDATION LICENSE": "PSF-2.0",
    "ZLIB": "Zlib",
}

LICENSE_URLS = {
    "0BSD": "https://opensource.org/licenses/0BSD",
    "Apache-2.0": "https://opensource.org/licenses/Apache-2.0",
    "BSD": "https://opensource.org/licenses/BSD-3-Clause",
    "BSD-2-Clause": "https://opensource.org/licenses/BSD-2-Clause",
    "BSD-3-Clause": "https://opensource.org/licenses/BSD-3-Clause",
    "CC0-1.0": "https://opensource.org/licenses/CC0-1.0",
    "ISC": "https://opensource.org/licenses/ISC",
    "LGPL-2.1-only": "https://opensource.org/licenses/LGPL-2.1",
    "MIT": "https://opensource.org/licenses/MIT",
    "MIT-CMU": "https://opensource.org/licenses/MIT",
    "MPL-2.0": "https://opensource.org/licenses/MPL-2.0",
    "PSF-2.0": "https://opensource.org/license/Python-2.0",
    "Public Domain": "https://opensource.org/licenses/Unlicense",
    "Zlib": "https://opensource.org/licenses/Zlib",
}

LICENSE_OVERRIDES = {
    # licensecheck returns the full BSD text for this package.
    "exifread": "BSD-3-Clause",
}

NAME_ALIASES = {
    "gradio-client": "gradio_client",
    "huggingface-hub": "huggingface_hub",
    "ml-dtypes": "ml_dtypes",
    "pydantic-core": "pydantic_core",
    "pytorchwildlife": "PytorchWildlife",
    "typing-extensions": "typing_extensions",
}

PROJECT_URL_PRIORITY = (
    "homepage",
    "home-page",
    "documentation",
    "repository",
    "source",
    "source code",
    "code",
)


@dataclass(frozen=True, slots=True)
class NoticeRow:
    name: str
    version: str
    project_url: str
    version_url: str
    author: str


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regenerate third-party-notices.md from licensecheck output.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Path to write. Defaults to third-party-notices.md.",
    )
    parser.add_argument(
        "--licensecheck-output",
        type=Path,
        help="Read licensecheck JSON output from a file instead of running licensecheck.",
    )
    args = parser.parse_args()

    licensecheck_output = (
        args.licensecheck_output.read_text(encoding="utf-8")
        if args.licensecheck_output
        else run_licensecheck()
    )
    package_licenses = parse_licensecheck_json(licensecheck_output)
    if not package_licenses:
        print(licensecheck_output)
        raise SystemExit(
            "licensecheck returned no package rows; refusing to overwrite "
            f"{args.output}"
        )

    notices = build_notice_groups(package_licenses)
    args.output.write_text(render_notices(notices), encoding="utf-8")


def run_licensecheck() -> str:
    command = [
        str(LICENSECHECK),
        "--license",
        "Apache-2.0",
        "--format",
        "json",
        "--requirements-paths",
        "pyproject.toml",
    ]
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return result.stdout


def parse_licensecheck_json(output: str) -> list[tuple[str, tuple[str, ...]]]:
    payload = json.loads(extract_json_payload(output))
    rows: list[tuple[str, tuple[str, ...]]] = []
    for package_info in payload.get("packages", []):
        package = str(package_info["name"]).strip()
        raw_license = LICENSE_OVERRIDES.get(
            canonicalize_name(package),
            str(package_info.get("license") or "").strip(),
        )
        rows.append((package, normalize_licenses(raw_license)))

    return rows


def extract_json_payload(output: str) -> str:
    start = output.find("{")
    if start < 0:
        raise ValueError("licensecheck did not return JSON output")
    return output[start:]


def normalize_licenses(raw_license: str) -> tuple[str, ...]:
    licenses: list[str] = []
    for raw_part in raw_license.split(";;"):
        key = " ".join(raw_part.upper().split())
        licenses.append(LICENSE_ALIASES.get(key, raw_part.strip() or "UNKNOWN"))
    return tuple(licenses)


def build_notice_groups(
    package_licenses: Iterable[tuple[str, tuple[str, ...]]],
) -> dict[str, list[NoticeRow]]:
    groups: dict[str, list[NoticeRow]] = defaultdict(list)
    for package, licenses in package_licenses:
        row = notice_row_for_package(package)
        for license_name in licenses:
            if row not in groups[license_name]:
                groups[license_name].append(row)

    return groups


def notice_row_for_package(package: str) -> NoticeRow:
    dist = distribution_for_package(package)
    display_name = dist.metadata.get("Name") or package
    version = dist.version
    pypi_name = display_name.replace("_", "-")
    return NoticeRow(
        name=display_name,
        version=version,
        project_url=project_url_for_distribution(dist, package),
        version_url=f"https://pypi.org/project/{pypi_name}/{version}/",
        author=author_for_distribution(dist),
    )


def distribution_for_package(package: str):
    candidates = [package, NAME_ALIASES.get(package, package)]
    for candidate in candidates:
        try:
            return distribution(candidate)
        except PackageNotFoundError:
            pass

    target = canonicalize_name(package)
    for dist in distributions():
        if canonicalize_name(dist.metadata.get("Name") or "") == target:
            return dist

    raise PackageNotFoundError(package)


def project_url_for_distribution(dist, package: str) -> str:
    metadata = dist.metadata
    urls: list[tuple[str, str]] = []
    for item in metadata.get_all("Project-URL") or []:
        if "," not in item:
            continue
        label, url = item.split(",", 1)
        urls.append((label.strip().lower(), url.strip()))

    home_page = metadata.get("Home-page")
    if home_page:
        urls.append(("homepage", home_page.strip()))

    for wanted_label in PROJECT_URL_PRIORITY:
        for label, url in urls:
            if label == wanted_label:
                return url

    if urls:
        return urls[0][1]

    return f"https://pypi.org/project/{package}/"


def author_for_distribution(dist) -> str:
    author = sanitize_author(dist.metadata.get("Author"))
    if author:
        return author

    author_email = dist.metadata.get("Author-email")
    if not author_email:
        return ""

    names = [
        name.strip()
        for name, _email in getaddresses([author_email])
        if name.strip()
    ]
    if names:
        return sanitize_author(", ".join(names))

    return sanitize_author(author_email)


def sanitize_author(author: str | None) -> str:
    if not author:
        return ""

    author = decode_rfc2047_words(author)
    author = re.sub(
        r"<?[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}>?",
        "",
        author,
    )
    author = re.sub(r"\b(?:https?://|www\.)\S+", "", author, flags=re.IGNORECASE)
    author = re.sub(r"\s+@\w+\b", "", author)
    author = re.sub(r"<\s*>", "", author)
    author = re.sub(r"\(\s*\)", "", author)
    author = re.sub(r"\s+([,;])", r"\1", author)
    author = re.sub(r"(?:\s*[,;]\s*){2,}", ", ", author)
    author = author.strip(" ,;")
    return md_escape(" ".join(author.split()))


def decode_rfc2047_words(value: str) -> str:
    if "=?" not in value:
        return value

    parts = []
    for payload, charset in decode_header(value):
        if isinstance(payload, bytes):
            parts.append(payload.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(payload)
    return "".join(parts)


def render_notices(groups: dict[str, list[NoticeRow]]) -> str:
    lines = ["# Third-Party Notices", ""]
    for license_name in sorted(groups):
        license_url = LICENSE_URLS[license_name]
        rows = sorted(groups[license_name], key=lambda row: row.name.lower())
        lines.append(f"## [{license_name}]({license_url})")
        lines.append("")
        lines.append("| Project | Version | Author |")
        lines.append("|---|---:|---|")
        for row in rows:
            lines.append(
                f"| [{md_escape(row.name)}]({row.project_url}) "
                f"| [`{md_escape(row.version)}`]({row.version_url}) "
                f"| {row.author} |"
            )
        lines.append("")
    return "\n".join(lines)


def md_escape(value: str) -> str:
    return value.replace("|", "\\|")


if __name__ == "__main__":
    main()
