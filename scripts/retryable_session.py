import requests
import requests.adapters
import urllib3.util.retry


def retryable_session(
    retries: int = 8,
) -> requests.Session:
    session = requests.Session()

    retry = urllib3.util.retry.Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=0.3,
        status_forcelist=(500, 502, 504),
    )

    adapter = requests.adapters.HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    session.headers.update({"User-Agent": "Mozilla/5.0 Firefox/100.0 www.mtgjson.com"})
    return session
