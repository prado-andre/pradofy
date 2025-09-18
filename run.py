import webview
import os
import sys
import logging
import tempfile
import yt_dlp
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from app import app # Importa a instância do Flask do app.py

# --- Configurações Iniciais ---
# logging.basicConfig(level=logging.INFO)

try:
    spotify = spotipy.Spotify(auth_manager=SpotifyClientCredentials())
    logging.info("Autenticação com Spotify bem-sucedida.")
except Exception as e:
    spotify = None
    logging.error(f"FALHA NA AUTENTICAÇÃO COM SPOTIFY: {e}")

def get_ffmpeg_path():
    if getattr(sys, 'frozen', False):
        application_path = sys._MEIPASS
        return os.path.join(application_path, 'ffmpeg_binaries', 'ffmpeg.exe')
    else:
        return 'ffmpeg'

# --- A classe API que será a "ponte" entre Python e JavaScript ---

class Api:
    def get_title(self, url):
        """Busca apenas o título de uma URL para feedback rápido."""
        try:
            if "spotify.com" in url:
                if not spotify:
                     raise Exception("Autenticação com Spotify não foi configurada.")
                track = spotify.track(url)
                track_info = f"{track['artists'][0]['name']} - {track['name']}"
                return {'status': 'success', 'title': track_info}
            else:
                ydl_opts = {'noplaylist': True, 'quiet': True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(url, download=False)
                    return {'status': 'success', 'title': info_dict.get('title', 'Título desconhecido')}
        except Exception as e:
            logging.error(f"Erro ao buscar título: {e}")
            return {'status': 'error', 'message': f'Não foi possível obter o título da URL.'}

    def download(self, url, quality):
        """Executa o download e salva o arquivo na qualidade escolhida."""
        if not url:
            return {'status': 'error', 'message': 'URL não pode estar vazia.'}

        downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
        temp_dir = tempfile.mkdtemp()
        search_query = url
        download_title_base = "audio"

        try:
            if "spotify.com" in url:
                if not spotify:
                     raise Exception("Autenticação com Spotify não foi configurada ou falhou.")
                track = spotify.track(url)
                track_info = f"{track['artists'][0]['name']} - {track['name']}"
                download_title_base = track_info
                search_query = f"ytsearch1:{track_info}"
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                'ffmpeg_location': get_ffmpeg_path(),
                'noplaylist': True,
                'match_filter': yt_dlp.utils.match_filter_func("duration < 600"),
            }

            if quality == 'mp3':
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(search_query, download=True)
                if 'entries' in info_dict:
                    if not info_dict['entries']:
                        raise Exception("Nenhum vídeo correspondente (com menos de 10 min) foi encontrado.")
                    info_dict = info_dict['entries'][0]

                if "spotify.com" not in url:
                    download_title_base = info_dict.get('title', 'audio')
                
                temp_filename = ydl.prepare_filename(info_dict)

                if quality == 'mp3':
                    base, _ = os.path.splitext(temp_filename)
                    final_temp_path = base + '.mp3'
                    final_extension = '.mp3'
                else:
                    final_temp_path = temp_filename
                    _, final_extension = os.path.splitext(temp_filename)

                sanitized_title = "".join(i for i in download_title_base if i not in r'\/:*?"<>|')
                final_file_path = os.path.join(downloads_path, f"{sanitized_title}{final_extension}")
                
                count = 1
                while os.path.exists(final_file_path):
                    final_file_path = os.path.join(downloads_path, f"{sanitized_title} ({count}){final_extension}")
                    count += 1

                os.rename(final_temp_path, final_file_path)
                
            logging.info(f"Download concluído! Arquivo salvo em: {final_file_path}")
            return {'status': 'success', 'title': sanitized_title}

        except Exception as e:
            logging.error(f"Ocorreu um erro geral: {e}")
            return {'status': 'error', 'message': f'Erro: {str(e)}'}

# --- Ponto de entrada da aplicação ---

if __name__ == '__main__':
    api = Api()
    window = webview.create_window(
        'Pradofy',
        app,
        js_api=api,
        width=800,
        height=650
    )
    webview.start(debug=False, gui='edgechromium')