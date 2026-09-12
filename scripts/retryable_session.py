import requests
import requests.adapters
import urllib3.util.retry


class TimeoutSession(requests.Session):
    """Use bounded connect/read waits unless the caller supplies a timeout."""

    def request(self, method, url, **kwargs):
        kwargs.setdefault("timeout", (10, 60))
        return super().request(method, url, **kwargs)


def retryable_session(
    retries: int = 8,
) -> requests.Session:
    session = TimeoutSession()

    retry = urllib3.util.retry.Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=0.3,
        status_forcelist=(429, 500, 502, 503, 504),
    )

    adapter = requests.adapters.HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    session.headers.update({"User-Agent": "Mozilla/5.0 Firefox/100.0 www.mtgjson.com"})
    return session
