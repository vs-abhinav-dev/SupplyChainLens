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

    def _get_filename(self, package_name: str) -> Path:
        """Sanitize package name into safe filename, e.g. '@types/lodash' -> '@types_lodash.json'."""
        safe_name = package_name.replace("/", "_")
        return self.raw_data_dir / f"{safe_name}.json"

    def fetch_packument(self, package_name: str, force_fetch: bool = False) -> Optional[Dict[str, Any]]:
        """
        Fetches packument for a package.
        Checks local disk cache first unless force_fetch is True.
        Saves raw JSON response to data/raw/npm/<package>.json.
        """
        file_path = self._get_filename(package_name)

        if not force_fetch and file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass  # Re-fetch if file corrupted

        # URL encode scoped package names (e.g., @types/lodash -> @types%2flodash)
        encoded_pkg = urllib.parse.quote(package_name, safe="")
        url = f"{self.registry_url}/{encoded_pkg}"

        headers = {
            "Accept": "application/json"
        }

        try:
            with httpx.Client(timeout=15.0, follow_redirects=True) as client:
                response = client.get(url, headers=headers)
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                raw_json = response.json()

            # Save raw packument
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(raw_json, f, indent=2)

            return raw_json
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise e
        except Exception as e:
            # If offline or request fails, check if we have a cached copy
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            raise e
