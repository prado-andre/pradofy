import webview
import os
import sys
import logging
import tempfile
import yt_dlp
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from app import app # Importa a instância do Flask do app.py

# --- As funções que antes estavam em app.py agora estão aqui ---

logging.basicConfig(level=logging.INFO)

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
    def download(self, url):
        if not url:
            return {'status': 'error', 'message': 'URL não pode estar vazia.'}

        # Encontra a pasta de Downloads do usuário
        downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
        temp_dir = tempfile.mkdtemp()
        search_query = url
        download_title_base = "audio"

        try:
            if "spotify.com" in url:
                if not spotify:
                     raise Exception("Autenticação com Spotify não foi configurada ou falhou.")
                track_info = spotify.track(url)['name'] + ' - ' + spotify.track(url)['artists'][0]['name']
                download_title_base = track_info
                search_query = f"ytsearch1:{track_info}"
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                'ffmpeg_location': get_ffmpeg_path(),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'noplaylist': True,
                'match_filter': yt_dlp.utils.match_filter_func("duration < 600"),
            }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info_dict = ydl.extract_info(search_query, download=True)
                if 'entries' in info_dict:
                    if not info_dict['entries']:
                        raise Exception("Nenhum vídeo correspondente (com menos de 10 min) foi encontrado.")
                    info_dict = info_dict['entries'][0]

                if "spotify.com" not in url:
                    download_title_base = info_dict.get('title', 'audio')

                temp_file_path = ydl.prepare_filename(info_dict).replace('.webm', '.mp3').replace('.m4a', '.mp3')
                final_file_path = os.path.join(downloads_path, f"{download_title_base}.mp3")
                
                # Move o arquivo do diretório temporário para a pasta de Downloads
                os.rename(temp_file_path, final_file_path)
                
            logging.info(f"Download concluído! Arquivo salvo em: {final_file_path}")
            return {'status': 'success', 'message': f'Download Concluído! Salvo em "{final_file_path}"'}

        except Exception as e:
            logging.error(f"Ocorreu um erro geral: {e}")
            return {'status': 'error', 'message': f'Erro: {str(e)}'}

# --- Ponto de entrada da aplicação ---

if __name__ == '__main__':
    api = Api()
    # Expomos a classe 'api' para o JavaScript
    window = webview.create_window('Download do Prado', app, js_api=api, width=800, height=650)
    webview.start(debug=False)