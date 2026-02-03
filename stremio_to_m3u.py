#!/usr/bin/env python3
"""
Stremio Addon to M3U Converter
Converte addons do Stremio para playlists M3U
"""

import requests
import json
import sys
import os
from urllib.parse import urljoin, quote
from datetime import datetime

# Configuração - altere aqui a URL do seu addon
ADDON_URL = os.environ.get('ADDON_URL', 'https://da5f663b4690-minhatv.baby-beamup.club/')
OUTPUT_FILE = os.environ.get('OUTPUT_FILE', 'playlist.m3u')

def get_manifest(base_url):
    """Busca o manifest.json do addon"""
    manifest_url = urljoin(base_url.rstrip('/') + '/', 'manifest.json')
    print(f"📋 Buscando manifest: {manifest_url}")
    
    response = requests.get(manifest_url, timeout=30)
    response.raise_for_status()
    return response.json()

def get_catalog(base_url, catalog_type, catalog_id):
    """Busca um catálogo específico do addon"""
    catalog_url = urljoin(base_url.rstrip('/') + '/', f'catalog/{catalog_type}/{catalog_id}.json')
    print(f"📺 Buscando catálogo: {catalog_url}")
    
    try:
        response = requests.get(catalog_url, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"   ⚠️  Erro ao buscar catálogo: {e}")
        return None

def get_stream(base_url, stream_type, stream_id):
    """Busca o stream de um item específico"""
    encoded_id = quote(stream_id, safe='')
    stream_url = urljoin(base_url.rstrip('/') + '/', f'stream/{stream_type}/{encoded_id}.json')
    
    try:
        response = requests.get(stream_url, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return None

def extract_stream_url(stream_data):
    """Extrai a URL do stream dos dados retornados"""
    if not stream_data or 'streams' not in stream_data:
        return None
    
    streams = stream_data['streams']
    if not streams:
        return None
    
    for stream in streams:
        if 'url' in stream:
            return {
                'url': stream['url'],
                'name': stream.get('name', ''),
                'title': stream.get('title', '')
            }
        if 'externalUrl' in stream:
            return {
                'url': stream['externalUrl'],
                'name': stream.get('name', ''),
                'title': stream.get('title', '')
            }
    
    return None

def generate_m3u(channels, output_file):
    """Gera o arquivo M3U com os canais"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('#EXTM3U\n')
        f.write(f'# Playlist gerada automaticamente\n')
        f.write(f'# Atualizado em: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} UTC\n')
        f.write(f'# Total de canais: {len(channels)}\n\n')
        
        for channel in channels:
            name = channel.get('name', 'Sem Nome')
            logo = channel.get('logo', '')
            group = channel.get('group', 'Stremio')
            url = channel.get('url', '')
            
            extinf = f'#EXTINF:-1'
            if logo:
                extinf += f' tvg-logo="{logo}"'
            if group:
                extinf += f' group-title="{group}"'
            extinf += f',{name}'
            
            f.write(f'{extinf}\n')
            f.write(f'{url}\n')
    
    print(f"\n✅ Arquivo M3U salvo: {output_file}")
    print(f"   Total de canais: {len(channels)}")

def main():
    base_url = ADDON_URL
    output_file = OUTPUT_FILE
    
    print("=" * 60)
    print("🎬 Stremio Addon to M3U Converter")
    print("=" * 60)
    print(f"   Addon: {base_url}")
    print(f"   Output: {output_file}")
    print("=" * 60)
    
    # 1. Buscar manifest
    try:
        manifest = get_manifest(base_url)
    except Exception as e:
        print(f"❌ Erro ao buscar manifest: {e}")
        sys.exit(1)
    
    print(f"\n📦 Addon: {manifest.get('name', 'Desconhecido')}")
    print(f"   Versão: {manifest.get('version', '?')}")
    
    # 2. Identificar catálogos
    catalogs = manifest.get('catalogs', [])
    print(f"\n📂 Catálogos encontrados: {len(catalogs)}")
    
    # 3. Buscar todos os itens
    all_channels = []
    
    for catalog in catalogs:
        cat_type = catalog.get('type')
        cat_id = catalog.get('id')
        cat_name = catalog.get('name', cat_id)
        
        catalog_data = get_catalog(base_url, cat_type, cat_id)
        
        if not catalog_data:
            continue
        
        metas = catalog_data.get('metas', [])
        print(f"   Encontrados {len(metas)} itens em '{cat_name}'")
        
        # 4. Para cada item, buscar o stream
        for meta in metas:
            item_id = meta.get('id')
            item_name = meta.get('name', 'Sem Nome')
            item_poster = meta.get('poster', meta.get('logo', ''))
            
            stream_data = get_stream(base_url, cat_type, item_id)
            stream_info = extract_stream_url(stream_data)
            
            if stream_info:
                all_channels.append({
                    'name': item_name,
                    'url': stream_info['url'],
                    'logo': item_poster,
                    'group': cat_name
                })
                print(f"   ✓ {item_name}")
            else:
                print(f"   ✗ {item_name}")
    
    # 5. Gerar arquivo M3U
    if all_channels:
        generate_m3u(all_channels, output_file)
    else:
        print("\n❌ Nenhum canal encontrado.")
        sys.exit(1)

if __name__ == '__main__':
    main()
