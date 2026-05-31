#!/usr/bin/env python3
"""
Stremio Addon to M3U Converter
Converts Stremio addons to M3U playlists
"""

import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from urllib.parse import quote, urljoin

import requests

# ---------------------------------------------------------------------------
# 1. Immutable data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Config:
    addon_url: str
    output_file: str
    quality_filter: str


@dataclass(frozen=True)
class CatalogRef:
    type: str
    id: str
    name: str
    genres: tuple[str, ...] = ()


@dataclass(frozen=True)
class Manifest:
    name: str
    version: str
    catalogs: tuple[CatalogRef, ...]


@dataclass(frozen=True)
class StreamInfo:
    url: str
    name: str
    title: str


@dataclass(frozen=True)
class Channel:
    name: str
    url: str
    logo: str
    group: str


# ---------------------------------------------------------------------------
# 2. Pure functions (no IO, no side effects)
# ---------------------------------------------------------------------------


def _normalize_base(base_url: str) -> str:
    return base_url.rstrip("/") + "/"


def build_manifest_url(base_url: str) -> str:
    return urljoin(_normalize_base(base_url), "manifest.json")


def build_catalog_url(base_url: str, type: str, id: str) -> str:
    return urljoin(_normalize_base(base_url), f"catalog/{type}/{id}.json")


def build_catalog_genre_url(base_url: str, type: str, id: str, genre: str) -> str:
    encoded = quote(genre, safe="")
    return urljoin(_normalize_base(base_url), f"catalog/{type}/{id}/genre={encoded}.json")


def build_stream_url(base_url: str, type: str, id: str) -> str:
    encoded_id = quote(id, safe="")
    return urljoin(_normalize_base(base_url), f"stream/{type}/{encoded_id}.json")


def parse_manifest(data: dict) -> Manifest:
    catalogs = tuple(
        CatalogRef(
            type=c.get("type", ""),
            id=c.get("id", ""),
            name=c.get("name", c.get("id", "")),
            genres=tuple(
                opt
                for extra in c.get("extra", [])
                if extra.get("name") == "genre"
                for opt in extra.get("options", [])
            ),
        )
        for c in data.get("catalogs", ())
    )
    return Manifest(
        name=data.get("name", "Unknown"),
        version=data.get("version", "?"),
        catalogs=catalogs,
    )


def extract_stream_info(data: Optional[dict]) -> Optional[StreamInfo]:
    if not data or "streams" not in data:
        return None
    return next(
        (
            StreamInfo(
                url=s.get("url") or s.get("externalUrl", ""),
                name=s.get("name", ""),
                title=s.get("title", ""),
            )
            for s in data["streams"]
            if "url" in s or "externalUrl" in s
        ),
        None,
    )


def meta_to_channel(meta: dict, stream_info: StreamInfo, group: str) -> Channel:
    return Channel(
        name=meta.get("name", "No Name"),
        url=stream_info.url,
        logo=meta.get("poster", meta.get("logo", "")),
        group=group,
    )


def format_channel_extinf(channel: Channel) -> str:
    extinf = "#EXTINF:-1"
    if channel.logo:
        extinf += f' tvg-logo="{channel.logo}"'
    if channel.group:
        extinf += f' group-title="{channel.group}"'
    extinf += f",{channel.name}"
    return extinf


def format_m3u(channels: tuple[Channel, ...], timestamp: str) -> str:
    header = (
        "#EXTM3U\n"
        "# Automatically generated playlist\n"
        f"# Updated at: {timestamp} UTC\n"
        f"# Total channels: {len(channels)}\n"
    )
    body = "\n".join(
        f"{format_channel_extinf(ch)}\n{ch.url}" for ch in channels
    )
    return header + "\n" + body + "\n" if channels else header


# ---------------------------------------------------------------------------
# 3. IO boundary (side effects)
# ---------------------------------------------------------------------------


MAX_WORKERS = 10


def load_config() -> Config:
    return Config(
        addon_url=os.environ.get(
            "ADDON_URL", "https://kangaroostreams.hayd.uk/Brisbane/radio/ausports/nz/nzradio/nzsports/uktv/uksports/ustv/ussports/catv/casports/eusports/worldsports/epl/extras/exgrp-ca-dazn/exgrp-int-netflix-events/exgrp-int-dirtvision/exgrp-uk-epl/exgrp-uk-dazn/exgrp-au-kayo-sports/exgrp-uk-tnt-sports/exgrp-uk-sky-sports/exgrp-nz-sky-sport/exgrp-int-f1-tv/exgrp-uk-spfl/exgrp-int-rugby-events/exgrp-au-stan-sports-events/exgrp-ppv-events/"
        ),
        output_file=os.environ.get("OUTPUT_FILE", "playlist.m3u"),
        quality_filter=os.environ.get("QUALITY_FILTER", ""),
    )


def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; Stremio/4.4)"})
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=MAX_WORKERS, pool_maxsize=MAX_WORKERS
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def fetch_manifest(session: requests.Session, base_url: str) -> dict:
    url = build_manifest_url(base_url)
    print(f"Fetching manifest: {url}")
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_catalog(
    session: requests.Session,
    base_url: str,
    catalog_ref: CatalogRef,
    genre: Optional[str] = None,
) -> Optional[list]:
    if genre is not None:
        url = build_catalog_genre_url(base_url, catalog_ref.type, catalog_ref.id, genre)
    else:
        url = build_catalog_url(base_url, catalog_ref.type, catalog_ref.id)
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data.get("metas", [])
    except Exception as e:
        print(f"   Error fetching catalog: {e}")
        return None


def fetch_stream(
    session: requests.Session, base_url: str, type: str, id: str
) -> Optional[dict]:
    url = build_stream_url(base_url, type, id)
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception:
        return None


def resolve_channel(
    session: requests.Session,
    base_url: str,
    catalog_ref: CatalogRef,
    meta: dict,
    group: Optional[str] = None,
) -> Optional[Channel]:
    item_id = meta.get("id")
    stream_data = fetch_stream(session, base_url, catalog_ref.type, item_id)
    stream_info = extract_stream_info(stream_data)
    if stream_info is None:
        return None
    return meta_to_channel(meta, stream_info, group or catalog_ref.name)


def filter_metas_by_quality(
    metas: list[dict], quality_filter: str
) -> list[dict]:
    if not quality_filter:
        return metas
    keywords = [k.strip().upper() for k in quality_filter.split(",") if k.strip()]
    if not keywords:
        return metas
    return [
        m
        for m in metas
        if any(kw in m.get("name", "").upper() for kw in keywords)
    ]


def resolve_catalog_channels(
    session: requests.Session,
    base_url: str,
    catalog_ref: CatalogRef,
    quality_filter: str = "",
) -> tuple[Channel, ...]:
    genres_to_fetch: tuple[Optional[str], ...] = (
        catalog_ref.genres if catalog_ref.genres else (None,)
    )

    resolved: list[Channel] = []
    seen_ids: set[str] = set()

    for genre in genres_to_fetch:
        metas = fetch_catalog(session, base_url, catalog_ref, genre=genre)
        if not metas:
            continue

        group = genre if genre is not None else catalog_ref.name
        new_metas = [m for m in metas if m.get("id") not in seen_ids]
        seen_ids.update(m.get("id", "") for m in new_metas)
        new_metas = filter_metas_by_quality(new_metas, quality_filter)

        print(f"   '{group}': {len(new_metas)} items")

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            future_to_meta = {
                pool.submit(resolve_channel, session, base_url, catalog_ref, meta, group): meta
                for meta in new_metas
            }
            for future in as_completed(future_to_meta):
                meta = future_to_meta[future]
                channel = future.result()
                if channel is not None:
                    resolved.append(channel)
                    print(f"   ✓ {channel.name}")
                else:
                    print(f"   ✗ {meta.get('name', 'No Name')}")

    resolved.sort(key=lambda ch: ch.name)
    return tuple(resolved)


def resolve_all_channels(
    session: requests.Session,
    base_url: str,
    manifest: Manifest,
    quality_filter: str = "",
) -> tuple[Channel, ...]:
    return tuple(
        channel
        for catalog_ref in manifest.catalogs
        for channel in resolve_catalog_channels(
            session, base_url, catalog_ref, quality_filter
        )
    )


def write_m3u(content: str, output_file: str) -> None:
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(content)


# ---------------------------------------------------------------------------
# 4. Orchestration (main)
# ---------------------------------------------------------------------------


def main() -> None:
    config = load_config()

    print("=" * 60)
    print("🎬 Stremio Addon to M3U Converter")
    print("=" * 60)
    print(f"   Addon: {config.addon_url}")
    print(f"   Output: {config.output_file}")
    print(f"   Quality filter: {config.quality_filter or 'none (all channels)'}")
    print("=" * 60)

    session = create_session()

    try:
        raw_manifest = fetch_manifest(session, config.addon_url)
    except Exception as e:
        print(f"Error fetching manifest: {e}")
        sys.exit(1)

    manifest = parse_manifest(raw_manifest)

    print(f"\nAddon: {manifest.name}")
    print(f"   Version: {manifest.version}")
    print(f"\nCatalogs found: {len(manifest.catalogs)}")

    all_channels = resolve_all_channels(
        session, config.addon_url, manifest, config.quality_filter
    )

    if not all_channels:
        print("\nNo channels found.")
        sys.exit(1)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = format_m3u(all_channels, timestamp)
    write_m3u(content, config.output_file)

    print(f"\nM3U file saved: {config.output_file}")
    print(f"   Total channels: {len(all_channels)}")


if __name__ == "__main__":
    main()
