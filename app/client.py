import time

import requests


class ApiError(Exception):
    pass


class AuthError(ApiError):
    
class RetryExhausted(ApiError):
    pass


class APIClient:
    RETRYABLE_STATUS = (429, 500, 502, 503, 504)

    def __init__(self, base_url, token, max_retries=4, timeout=10.0, backoff_base=0.25,
                 sleep=time.sleep):
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.timeout = timeout
        self.backoff_base = backoff_base
        self._sleep = sleep
        self.retries = 0            
        self.rate_limited = 0      
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": token, "Accept": "application/json"})

    def get(self, path, params):
        """Return (status_code, raw_text, parsed_json) of the first good response."""
        url = self.base_url + path
        last_problem = "unknown"
        for attempt in range(self.max_retries + 1):
            delay = min(self.backoff_base * (2 ** attempt), 2.0)
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                last_problem = f"network error: {type(exc).__name__}"
            else:
                if response.status_code in (401, 403):
                    raise AuthError(f"HTTP {response.status_code}: check API_TOKEN")
                if response.status_code in self.RETRYABLE_STATUS:
                    last_problem = f"HTTP {response.status_code}"
                    if response.status_code == 429:
                        self.rate_limited += 1
                    try:
                        delay = min(float(response.headers.get("Retry-After", delay)), 2.0)
                    except ValueError:
                        pass
                else:
                    response.raise_for_status()    
                    try:
                        return response.status_code, response.text, response.json()
                    except ValueError:
                        last_problem = "malformed JSON body"    
            if attempt < self.max_retries:
                self.retries += 1
                self._sleep(max(0.0, delay))
        raise RetryExhausted(f"{path}: gave up after {self.max_retries} retries ({last_problem})")
