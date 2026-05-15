#!/usr/bin/env python3
import hashlib
import html
import os
import re
import sys
import urllib.request

HISTORY_URL = "https://codeberg.org/thomasokken/plus42desktop/raw/branch/master/HISTORY"
MANIFEST = "com.thomasokken.plus42.yml"
METAINFO = "com.thomasokken.plus42.metainfo.xml"
TGZ_URL_TEMPLATE = "https://thomasokken.com/plus42/upstream/plus42-upstream-{version}.tgz"
TGZ_URL_PATTERN = re.escape(TGZ_URL_TEMPLATE).replace(r"\{version\}", r"[^\s]+")


def fetch_history():
    with urllib.request.urlopen(HISTORY_URL) as r:
        return r.read().decode("utf-8")


def latest_version(history):
    for line in history.splitlines():
        m = re.match(r"^\d{4}-\d{2}-\d{2}: release (\S+)", line)
        if m:
            return m.group(1)
    raise RuntimeError("Could not find any release in HISTORY")


def parse_history_releases(history):
    lines = history.splitlines()
    release_header = re.compile(r"^(\d{4}-\d{2}-\d{2}): release (\S+)")
    releases = []
    current_version = None
    current_date = None
    bullets = []
    current_bullet = []

    for line in lines:
        m = release_header.match(line)
        if m:
            if current_version is not None:
                if current_bullet:
                    bullets.append(" ".join(current_bullet))
                    current_bullet = []
                releases.append(
                    {
                        "version": current_version,
                        "date": current_date,
                        "bullets": bullets,
                    }
                )
            current_date = m.group(1)
            current_version = m.group(2)
            bullets = []
            current_bullet = []
            continue

        if current_version is None:
            continue

        if line.startswith("* "):
            if current_bullet:
                bullets.append(" ".join(current_bullet))
            current_bullet = [line[2:].strip()]
        elif line.strip() and current_bullet:
            current_bullet.append(line.strip())

    if current_version is not None:
        if current_bullet:
            bullets.append(" ".join(current_bullet))
        releases.append(
            {
                "version": current_version,
                "date": current_date,
                "bullets": bullets,
            }
        )

    if not releases:
        raise RuntimeError("Could not parse any releases from HISTORY")
    return releases


def releases_up_to_target(history_releases, to_version):
    idx = {r["version"]: i for i, r in enumerate(history_releases)}
    if to_version not in idx:
        raise RuntimeError(f"Release {to_version} not found in HISTORY")
    to_i = idx[to_version]

    # history_releases is newest -> oldest, so this returns target and all older releases.
    return history_releases[to_i:]


def sha256_of_url(url):
    import shutil
    import tempfile
    cache_dir = os.path.join(".flatpak-builder", "downloads")
    os.makedirs(cache_dir, exist_ok=True)
    source_name = os.path.basename(url.rstrip("/")) or "download"
    print(f"Downloading {url} ...")
    with urllib.request.urlopen(url) as r, \
         tempfile.NamedTemporaryFile(dir=cache_dir, delete=False) as tmp:
        h = hashlib.sha256()
        while chunk := r.read(65536):
            h.update(chunk)
            tmp.write(chunk)
        tmp_path = tmp.name
    digest = h.hexdigest()
    cache_path = os.path.join(cache_dir, digest)
    if not os.path.exists(cache_path):
        os.makedirs(cache_path, exist_ok=True)
        cached_file = os.path.join(cache_path, source_name)
        shutil.move(tmp_path, cached_file)
        print(f"Cached to {cached_file}")
    else:
        os.unlink(tmp_path)
        print(f"Already cached at {cache_path}")
    return digest


def release_block(version, date, bullets):
    if not bullets:
        raise RuntimeError(f"Release {version} has no bullet points in HISTORY")

    escaped_bullets = [html.escape(b, quote=False) for b in bullets]
    li_lines = "\n".join(f"          <li>{b}</li>" for b in escaped_bullets)
    return (
        f"    <release version=\"{version}\" date=\"{date}\">\n"
        f"      <description>\n"
        f"        <ul>\n"
        f"{li_lines}\n"
        f"        </ul>\n"
        f"      </description>\n"
        f"      <url>https://thomasokken.com/plus42/history.html</url>\n"
        f"    </release>"
    )


def update_metainfo(releases):
    with open(METAINFO) as f:
        content = f.read()

    if re.search(r"<releases>\s*</releases>", content, flags=re.DOTALL):
        content = re.sub(
            r"<releases>\s*</releases>",
            "<releases>\n  </releases>",
            content,
            count=1,
        )
    if "<releases>" not in content or "</releases>" not in content:
        content = content.replace(
            "</component>",
            "  <releases>\n  </releases>\n</component>",
            1,
        )

    for r in releases:
        version = r["version"]
        content = re.sub(
            rf"\n\s*<release\s+version=\"{re.escape(version)}\"[\s\S]*?</release>",
            "",
            content,
            count=1,
        )

    for r in reversed(releases):
        block = release_block(r["version"], r["date"], r["bullets"])
        content = content.replace("  <releases>\n", f"  <releases>\n{block}\n", 1)

    with open(METAINFO, "w") as f:
        f.write(content)

    latest = releases[0]["version"]
    print(f"Updated {METAINFO}: latest release {latest}")


def main():
    history = fetch_history()
    history_releases = parse_history_releases(history)
    version = sys.argv[1] if len(sys.argv) > 1 else latest_version(history)
    tgz_url = TGZ_URL_TEMPLATE.format(version=version)
    sha256 = sha256_of_url(tgz_url)

    with open(MANIFEST) as f:
        old_content = f.read()

    content, url_count = re.subn(
        rf"(url:\s*){TGZ_URL_PATTERN}",
        rf"\g<1>{tgz_url}",
        old_content,
    )
    content, sha_count = re.subn(
        r"(sha256:\s*)[0-9a-f]{64}",
        rf"\g<1>{sha256}",
        content,
    )

    if url_count == 0:
        raise RuntimeError("Could not find archive url in manifest")
    if sha_count == 0:
        raise RuntimeError("Could not find sha256 in manifest")

    if content == old_content:
        print(f"No changes needed in {MANIFEST}: already at version {version}")
    else:
        with open(MANIFEST, "w") as f:
            f.write(content)
        print(f"Updated {MANIFEST}: version {version}, sha256 {sha256}")

    releases = releases_up_to_target(history_releases, version)
    update_metainfo(releases)


if __name__ == "__main__":
    main()
