"""Assemble schema `sources[]` provenance blocks from per-field provider info.

Every populated statistic must be traceable to a source. Adapters tell us which
provider supplied which field; this module groups those into one `sources[]`
entry per provider, listing the fields it `supports`.
"""


def build_sources(field_provider, provider_meta):
    """field_provider: {field_name: provider}. provider_meta:
    {provider: {"url":..., "retrieved_at":...}}. Returns a sources[] list."""
    supports_by_provider = {}
    for field, provider in field_provider.items():
        supports_by_provider.setdefault(provider, []).append(field)

    sources = []
    for provider, fields in supports_by_provider.items():
        meta = provider_meta.get(provider, {})
        sources.append({
            "provider": provider,
            "url": meta.get("url"),
            "retrieved_at": meta.get("retrieved_at"),
            "supports": sorted(fields),
        })
    # stable order
    sources.sort(key=lambda s: s["provider"])
    return sources
