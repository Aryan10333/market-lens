"""Downloads files from NSE/BSE politely: browser-like headers, a short pause between
requests, and retries on temporary errors."""

import io
import logging
import time
import zipfile

import requests

log = logging.getLogger("download")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0 Safari/537.36"
)


class DownloadBlocked(Exception):
    """The website refused the request (HTTP 401/403). Retrying will not help."""


class Downloader:
    def __init__(self, pause_seconds: float = 0.4, retries: int = 3, timeout: int = 30):
        self.pause_seconds = pause_seconds
        self.retries = retries
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})
        self._last_request = 0.0

    def get(self, url: str, referer: str) -> bytes | None:
        """Return the file content, or None if the file does not exist (HTTP 404)."""
        for attempt in range(1, self.retries + 1):
            wait = self.pause_seconds - (time.monotonic() - self._last_request)
            if wait > 0:
                time.sleep(wait)
            self._last_request = time.monotonic()
            try:
                resp = self.session.get(url, headers={"Referer": referer}, timeout=self.timeout)
            except requests.RequestException as exc:
                log.warning(
                    "Request failed, retrying", extra={"fields": {"url": url, "error": str(exc)}}
                )
                time.sleep(2 * attempt)
                continue

            if resp.status_code == 200:
                return resp.content
            if resp.status_code == 404:
                return None
            if resp.status_code in (401, 403):
                raise DownloadBlocked(f"HTTP {resp.status_code} for {url}")
            log.warning(
                "Unexpected status, retrying",
                extra={"fields": {"url": url, "status": resp.status_code}},
            )
            time.sleep(2 * attempt)
        raise RuntimeError(f"Download failed after {self.retries} attempts: {url}")


def unzip_single(content: bytes) -> bytes:
    """Return the first file inside a zip archive."""
    with zipfile.ZipFile(io.BytesIO(content)) as zf:
        return zf.read(zf.namelist()[0])
