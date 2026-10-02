from pathlib import Path
from typing import Any, Dict, Optional
import httpx
import json
import urllib.parse


class NPMFetcher:
    """Fetches raw package packuments from the NPM registry and caches them locally."""

    def __init__(self, raw_data_dir: Path | str = "data/raw/npm"):
        self.raw_data_dir = Path(raw_data_dir)
        self.raw_data_dir.mkdir(parents=True, exist_ok=True)
        self.registry_url = "https://registry.npmjs.org"
        self._mem_cache: Dict[str, Dict[str, Any]] = {}
        self._client: Optional[httpx.Client] = None

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(timeout=15.0, follow_redirects=True)
        return self._client

    def _get_filename(self, package_name: str) -> Path:
        """Sanitize package name into safe filename, e.g. '@types/lodash' -> '@types_lodash.json'."""
        safe_name = package_name.replace("/", "_")
        return self.raw_data_dir / f"{safe_name}.json"

    def fetch_packument_with_status(
        self, package_name: str, force_fetch: bool = False
    ) -> tuple[Optional[Dict[str, Any]], str]:
        """
        Fetches packument for a package, returning tuple of (data, source_status).
        source_status can be: 'mem_cache', 'disk_cache', 'network', or 'not_found'.
        """
        if not force_fetch and package_name in self._mem_cache:
            return self._mem_cache[package_name], "mem_cache"

        file_path = self._get_filename(package_name)

        if not force_fetch and file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._mem_cache[package_name] = data
                    return data, "disk_cache"
            except Exception:
                pass  # Re-fetch if file corrupted

        # URL encode scoped package names (e.g., @types/lodash -> @types%2flodash)
        encoded_pkg = urllib.parse.quote(package_name, safe="")
        url = f"{self.registry_url}/{encoded_pkg}"

        headers = {"Accept": "application/json"}

        try:
            client = self._get_client()
            response = client.get(url, headers=headers)
            if 400 <= response.status_code < 500:
                return None, "not_found"
            response.raise_for_status()
            raw_json = response.json()

            # Save raw packument
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(raw_json, f, indent=2)

            self._mem_cache[package_name] = raw_json
            return raw_json, "network"
        except httpx.HTTPStatusError as e:
            if 400 <= e.response.status_code < 500:
                return None, "not_found"
            raise e
        except Exception as e:
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._mem_cache[package_name] = data
                    return data, "disk_cache"
            raise e

    def fetch_packument(self, package_name: str, force_fetch: bool = False) -> Optional[Dict[str, Any]]:
        """
        Fetches packument for a package.
        Checks in-memory cache first, then local disk cache unless force_fetch is True.
        Saves raw JSON response to data/raw/npm/<package>.json.
        """
        data, _ = self.fetch_packument_with_status(package_name, force_fetch=force_fetch)
        return data

    def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            self._client.close()

    def __del__(self) -> None:
        self.close()

