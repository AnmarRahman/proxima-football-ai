"""soccerdata adapter - policy evaluation, deliberately NON-fetching.

The pilot brief asks us to evaluate the `soccerdata` package (FBref, Understat,
Sofascore, ESPN, WhoScored adapters), but only to *use* adapters that operate
without bypassing access restrictions.

Empirical finding (recorded, not re-run here): `soccerdata`'s readers reach
Understat/FBref/Sofascore by downloading and using `tls-client`
(bogdanfinn/tls-client) via `tls_requests` - a TLS-fingerprint impersonation
library whose purpose is to defeat anti-bot / Cloudflare protection. That is
exactly the "browser fingerprinting / access-control circumvention" the project
forbids.

Therefore this adapter does NOT invoke soccerdata to fetch data. It only reports
the evaluation so the pilot can record it. Flipping `allow_impersonation=True`
is intentionally unsupported.
"""

IMPERSONATION_DEPENDENCY = "tls_requests / tls-client (bogdanfinn/tls-client)"


class SoccerdataSource:
    provider = "soccerdata"

    ADAPTERS = ["FBref", "Understat", "Sofascore", "ESPN", "WhoScored"]

    def __init__(self, *_, **__):
        pass

    def evaluate(self):
        try:
            import soccerdata  # noqa: F401
            installed = getattr(soccerdata, "__version__", "unknown")
        except Exception:
            installed = None
        return {
            "provider": self.provider,
            "installed_version": installed,
            "used_for_collection": False,
            "reason": (
                "soccerdata reaches Understat/FBref/Sofascore/WhoScored by using "
                f"{IMPERSONATION_DEPENDENCY}, a TLS-fingerprint impersonation "
                "library that circumvents anti-bot protection. This violates the "
                "no-fingerprinting / no-circumvention policy, so soccerdata is "
                "excluded from the collection pipeline. ESPN's adapter may use "
                "plain requests, but was not adopted to keep one consistent, "
                "policy-compliant access path."
            ),
            "adapters_considered": self.ADAPTERS,
        }
