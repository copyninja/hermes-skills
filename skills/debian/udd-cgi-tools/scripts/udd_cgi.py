"""
UDD CGI Client — Query Ultimate Debian Database CGI endpoints.

Endpoints:
  - bugs.cgi — RC bugs for suite (at /bugs.cgi, not /cgi-bin/)
  - bugs-with-patches.cgi — bugs with patches
  - ftbfs.cgi / ftbfs-bugs.json.cgi — FTBFS packages
  - bug-blockers.cgi — transition blockers
  - autoremovals.cgi — autoremoval candidates
  - wnpp-checks.cgi — WNPP packages
  - sponsorstats.cgi — sponsorship stats
  - ddpo-bugs.cgi — maintainer/team bugs (plain text summary)
  - nobugs.cgi — zero-bug packages
  - dmd.cgi — Debian Maintainer Dashboard (requires JS)
"""

import re
import json
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

BASE_CGI = "https://udd.debian.org/cgi-bin/"
BASE_UDD = "https://udd.debian.org/"


@dataclass
class RCBug:
    package: str
    bug_number: int
    severity: str
    title: str = ""
    hints: str = ""
    deferred: str = ""
    rt_tags: str = ""
    modified: str = ""
    affects_key_package: bool = False


@dataclass
class PatchBug:
    package: str
    bug_number: int
    url: str


@dataclass
class FTBFSEntry:
    package: str
    version: str
    arch: str
    release: str
    bug_number: Optional[int] = None
    log_url: str = ""


@dataclass
class MaintainerBug:
    package: str
    bug_number: int
    severity: str
    subject: str
    status: str


@dataclass
class DDPOEntry:
    package: str
    total: int
    rc: int
    done: int
    pending: int
    forwarded: int


class UDDClient:
    """Client for UDD CGI endpoints."""

    def __init__(self, timeout: int = 30, user_agent: str = "UDD-CGI-Tools/1.0"):
        self.session = requests.Session()
        self.session.timeout = timeout
        self.session.headers.update({"User-Agent": user_agent})

    def _get(self, path: str, params: dict = None, base: str = BASE_CGI) -> str:
        url = base + path
        if params:
            url += "?" + urlencode(params)
        resp = self.session.get(url)
        resp.raise_for_status()
        return resp.text

    def _get_json(self, path: str, params: dict = None, base: str = BASE_CGI):
        text = self._get(path, params, base)
        return json.loads(text)

    # --- RC Bugs (via bugs.cgi at BASE_UDD) ---

    def rc_bugs(self, suite: str = "forky", key_only: bool = False) -> list[RCBug]:
        """Fetch RC bugs for a suite (forky, trixie, sid, etc.)."""
        params = {
            "release": suite,
            "merged": "ign",
            "rc": "1",
            "chints": "1",
            "cdeferred": "1",
            "crttags": "1",
        }
        if key_only:
            params["keypackages"] = "only"
        html = self._get("bugs.cgi", params, base=BASE_UDD)
        return self._parse_bugs_table(html)

    def _parse_bugs_table(self, html: str) -> list[RCBug]:
        soup = BeautifulSoup(html, "html.parser")
        bugs = []

        tables = soup.find_all("table")
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) < 10:
                continue
            header_row = rows[0]
            header_cells = [c.get_text(strip=True).lower() for c in header_row.find_all(["td", "th"])]
            if "bug#" in header_cells or "package" in header_cells:
                for row in rows[1:]:
                    cells = row.find_all(["td", "th"])
                    if len(cells) < 6:
                        continue
                    texts = [c.get_text(strip=True) for c in cells]
                    bug_num = texts[0].lstrip("#")
                    pkg = texts[1]
                    title = texts[2] if len(texts) > 2 else ""
                    hints = texts[3] if len(texts) > 3 else ""
                    deferred = texts[4] if len(texts) > 4 else ""
                    rt_tags = texts[5] if len(texts) > 5 else ""
                    modified = texts[6] if len(texts) > 6 else ""

                    try:
                        bugs.append(RCBug(
                            package=pkg,
                            bug_number=int(bug_num),
                            severity="RC",
                            title=title,
                            hints=hints,
                            deferred=deferred,
                            rt_tags=rt_tags,
                            modified=modified
                        ))
                    except ValueError:
                        pass
                break
        return bugs

    # --- Bugs with Patches ---

    def bugs_with_patches(self, packages: list[str] = None) -> list[PatchBug]:
        """Fetch bugs that have patches. Optionally filter by package list."""
        text = self._get("bugs-with-patches.cgi")
        bugs = self._parse_patches(text)
        if packages:
            pkg_set = set(packages)
            bugs = [b for b in bugs if b.package in pkg_set]
        return bugs

    def _parse_patches(self, text: str) -> list[PatchBug]:
        bugs = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(",")
            if len(parts) >= 3:
                pkg, url, bug_str = parts[0], parts[1], parts[2]
                try:
                    bugs.append(PatchBug(
                        package=pkg.strip(),
                        bug_number=int(bug_str.strip()),
                        url=url.strip()
                    ))
                except ValueError:
                    pass
        return bugs

    # --- FTBFS ---

    def ftbfs(self, arch: str = "amd64", release: str = "trixie") -> list[FTBFSEntry]:
        """Fetch FTBFS packages for arch/release."""
        try:
            data = self._get_json("ftbfs-bugs.json.cgi", {"arch": arch, "release": release})
            return self._parse_ftbfs_json(data)
        except (requests.RequestException, json.JSONDecodeError):
            html = self._get("ftbfs.cgi", {"arch": arch, "release": release})
            return self._parse_ftbfs_html(html)

    def _parse_ftbfs_json(self, data: list) -> list[FTBFSEntry]:
        """Parse FTBFS JSON - it's a list of bug objects."""
        entries = []
        for item in data:
            pkg = item.get("source", "")
            if not pkg and item.get("affected_sources"):
                pkg = item["affected_sources"][0] if item["affected_sources"] else ""
            entries.append(FTBFSEntry(
                package=pkg,
                version="",
                arch="",
                release="",
                bug_number=item.get("id"),
                log_url=""
            ))
        return entries

    def _parse_ftbfs_html(self, html: str) -> list[FTBFSEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for table in soup.find_all("table"):
            for row in table.find_all("tr")[1:]:
                cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
                if len(cells) >= 4:
                    entries.append(FTBFSEntry(
                        package=cells[0],
                        version=cells[1] if len(cells) > 1 else "",
                        arch=cells[2] if len(cells) > 2 else "",
                        release=cells[3] if len(cells) > 3 else ""
                    ))
        return entries

    # --- DDPO Maintainer Summary (plain text) ---

    def maintainer_summary(self, email: str) -> list[DDPOEntry]:
        """Fetch maintainer package summary from DDPO."""
        text = self._get("ddpo-bugs.cgi", {"email": email})
        return self._parse_ddpo_summary(text)

    def _parse_ddpo_summary(self, text: str) -> list[DDPOEntry]:
        """Parse ddpo-bugs.cgi output: pkg:total(rc) done(rc) pending(rc) forwarded(rc)"""
        entries = []
        pattern = re.compile(r"([^:]+):(\d+)\((\d+)\)\s+(\d+)\((\d+)\)\s+(\d+)\((\d+)\)\s+(\d+)\((\d+)\)")
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("(?"):
                continue
            match = pattern.match(line)
            if match:
                pkg = match.group(1)
                if pkg.startswith("("):
                    continue
                total, rc, done, done_rc, pending, pending_rc, forwarded, forwarded_rc = match.groups()[1:]
                entries.append(DDPOEntry(
                    package=pkg,
                    total=int(total),
                    rc=int(rc),
                    done=int(done),
                    pending=int(pending),
                    forwarded=int(forwarded)
                ))
        return entries

    # --- Other endpoints (thin wrappers) ---

    def bug_blockers(self, release: str = "trixie") -> str:
        return self._get("bug-blockers.cgi", {"release": release})

    def autoremovals(self) -> str:
        return self._get("autoremovals.cgi")

    def wnpp_checks(self) -> str:
        return self._get("wnpp-checks.cgi")

    def sponsor_stats(self) -> str:
        return self._get("sponsorstats.cgi")

    def nobugs(self) -> str:
        return self._get("nobugs.cgi")

    def bugs_search(self, **criteria) -> str:
        return self._get("bugs.cgi", criteria, base=BASE_UDD)


# Convenience functions

def get_rc_bugs(suite: str = "forky") -> list[RCBug]:
    return UDDClient().rc_bugs(suite)


def get_patches_for_packages(packages: list[str]) -> list[PatchBug]:
    return UDDClient().bugs_with_patches(packages)


def get_ftbfs(arch: str = "amd64", release: str = "trixie") -> list[FTBFSEntry]:
    return UDDClient().ftbfs(arch, release)


def get_maintainer_summary(email: str) -> list[DDPOEntry]:
    return UDDClient().maintainer_summary(email)
