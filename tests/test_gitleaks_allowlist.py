"""The secret-scan allowlist must remain exact and value-scoped."""
from pathlib import Path
import re
import tomllib


ROOT = Path(__file__).resolve().parents[1]
_POSTHOG_TOKEN = re.search(
    r"phc_[A-Za-z0-9]{20,}",
    (ROOT / "backend/core/analytics.py").read_text(encoding="utf-8"),
)
assert _POSTHOG_TOKEN is not None
# Retired public tokens remain in git history, and scheduled full-history scans
# read every commit. Built from parts so the token guard keeps phc_ literals in
# the canonical source files only.
_RETIRED_POSTHOG_TOKENS = {
    "phc_" + "v5wMjnYMPMaEcRNLRKQsTYCzPaYWh7wcHPhXNkNajVf9",  # EU project, #1193
}
EXPECTED_EXACT_REGEXES = {
    f"^{_POSTHOG_TOKEN.group(0)}$",
    *(f"^{token}$" for token in _RETIRED_POSTHOG_TOKENS),
    "^528e871c2a26c4f0f7773b9754e2e1acae20899d$",
    "^hf_abcdefghijklmnopqrstuvwxyz01234567890abcd$",
    "^hf_abcdefghijklmnopqrstuvwxyz0123456789ABCDEF$",
    "^hf_QWERTYUIOPasdfghjklZXCVBNM0123456789xyzAB$",
    "^max_length=400$",
    "^Ed25519PrivateKey$",
    r"^omnivoice\.dubSplit\.v1$",
}


def test_gitleaks_allowlist_contains_only_reviewed_exact_values():
    config = tomllib.loads((ROOT / ".gitleaks.toml").read_text(encoding="utf-8"))
    allowlist = config["allowlist"]

    assert set(allowlist) == {"description", "regexes"}
    assert set(allowlist["regexes"]) == EXPECTED_EXACT_REGEXES
    assert all(
        regex.startswith("^") and regex.endswith("$")
        for regex in allowlist["regexes"]
    )
    assert "rules" not in config


def test_dub_storage_key_allowlist_does_not_hide_similar_credentials():
    config = tomllib.loads((ROOT / ".gitleaks.toml").read_text(encoding="utf-8"))
    regexes = config["allowlist"]["regexes"]
    assert any(re.fullmatch(regex, "omnivoice.dubSplit.v1") for regex in regexes)
    for value in (
        "omnivoiceXdubSplitXv1",
        "omnivoice.dubSplit.v1-secret",
        "secret-omnivoice.dubSplit.v1",
    ):
        assert not any(re.fullmatch(regex, value) for regex in regexes)
