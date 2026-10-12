"""Microsoft Public Symbol Server Client for DRAKVUF Sandbox.

Author: Nitiraj Kulkarni
"""

import logging
import os
import shutil
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

from drakvuf_auto.command import command_exists, run_command
from drakvuf_auto.exceptions import SymbolExtractionError

logger = logging.getLogger("drakvuf_auto.vmi.pdb_fetcher")


class SymbolFetcher:
    """Retrieves official Microsoft PDB debugging symbols matching guest kernel GUIDs."""

    def __init__(
        self,
        symbol_server_url: str = "https://msdl.microsoft.com/download/symbols",
        cache_dir: Optional[Path] = None,
        max_retries: int = 3,
    ):
        self.symbol_server_url = symbol_server_url.rstrip("/")
        self.cache_dir = cache_dir or Path("/var/lib/drakvuf/symbols")
        self.max_retries = max_retries
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def fetch_symbol(self, pdb_name: str, guid_age: str) -> Path:
        """Download PDB file from Microsoft Symbol Server or return cached version."""
        target_dir = self.cache_dir / pdb_name / guid_age
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / pdb_name

        if target_file.exists() and target_file.stat().st_size > 0:
            logger.info(f"Using cached PDB symbol: {target_file}")
            return target_file

        url = f"{self.symbol_server_url}/{pdb_name}/{guid_age}/{pdb_name}"
        logger.info(f"Downloading debugging symbol from: {url}")

        headers = {
            "User-Agent": "Microsoft-Symbol-Server/10.0.0.0",
        }

        # Attempt download with retries
        for attempt in range(1, self.max_retries + 1):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=30) as response:
                    with open(target_file, "wb") as out_f:
                        shutil.copyfileobj(response, out_f)

                if target_file.stat().st_size > 0:
                    logger.info(f"Successfully downloaded PDB ({target_file.stat().st_size} bytes)")
                    return target_file

            except urllib.error.HTTPError as e:
                # If uncompressed PDB fails with 404, check compressed *.pd_ format
                if e.code == 404 and not pdb_name.endswith("_"):
                    compressed_name = pdb_name[:-1] + "_"
                    compressed_url = f"{self.symbol_server_url}/{pdb_name}/{guid_age}/{compressed_name}"
                    compressed_file = target_dir / compressed_name
                    try:
                        req_comp = urllib.request.Request(compressed_url, headers=headers)
                        with urllib.request.urlopen(req_comp, timeout=30) as resp:
                            with open(compressed_file, "wb") as out_c:
                                shutil.copyfileobj(resp, out_c)

                        if command_exists("cabextract"):
                            run_command(["cabextract", str(compressed_file)], cwd=target_dir, stream=False)
                            if target_file.exists():
                                compressed_file.unlink(missing_ok=True)
                                return target_file
                    except Exception:
                        pass

                logger.warning(f"Symbol fetch attempt {attempt} failed: HTTP {e.code}")
            except Exception as e:
                logger.warning(f"Symbol fetch attempt {attempt} failed: {e}")

            time.sleep(attempt * 2)

        raise SymbolExtractionError(
            f"Failed to retrieve PDB symbol '{pdb_name}' ({guid_age}) from Microsoft Symbol Server."
        )
