# 📺 Stremio to M3U Playlist

Converte automaticamente um addon do Stremio para playlist M3U.

## 🔗 Link da Playlist

```
https://raw.githubusercontent.com/SEU_USUARIO/SEU_REPOSITORIO/main/playlist.m3u
```

> ⚠️ **Substitua `SEU_USUARIO` e `SEU_REPOSITORIO` pelos seus dados!**

## ⚙️ Como funciona

- A playlist é atualizada **automaticamente a cada 6 horas**
- Você também pode atualizar manualmente em: `Actions` → `Atualizar Playlist M3U` → `Run workflow`

## 🛠️ Configuração

### Alterar o addon de origem

1. Vá em `Settings` → `Secrets and variables` → `Actions` → `Variables`
2. Crie uma variável chamada `ADDON_URL`
3. Coloque a URL do seu addon (ex: `https://exemplo.baby-beamup.club/`)

Ou edite diretamente no arquivo `stremio_to_m3u.py`:
```python
ADDON_URL = 'https://sua-url-aqui/'
```

### Alterar frequência de atualização

Edite o arquivo `.github/workflows/update-playlist.yml`:

```yaml
schedule:
  - cron: '0 */6 * * *'  # A cada 6 horas
```

Exemplos:
- `'0 */1 * * *'` = a cada 1 hora
- `'0 */12 * * *'` = a cada 12 horas  
- `'0 0 * * *'` = uma vez por dia (meia-noite)

## 📱 Como usar a playlist

Cole o link em qualquer player IPTV:

- **VLC**: Mídia → Abrir Fluxo de Rede → Cole o link
- **Kodi**: Adicionar lista M3U no PVR IPTV Simple Client
- **TiviMate**: Adicionar playlist → M3U Playlist → Cole o link
- **IPTV Smarters**: Adicionar usuário → Load Playlist → M3U URL

## 📝 Licença

Uso pessoal. Não hospeda nenhum conteúdo, apenas converte links públicos.
