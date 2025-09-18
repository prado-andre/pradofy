import os
import logging
import tempfile
import sys # <--- ADICIONADO
from flask import Flask, request, render_template, send_from_directory, after_this_request
import yt_dlp
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from dotenv import load_dotenv

# Carrega as variáveis de ambiente (CLIENT_ID, CLIENT_SECRET) do arquivo .env
load_dotenv()

# Configuração básica de logging
logging.basicConfig(level=logging.INFO)

# Configura a autenticação com a API do Spotify
# Envolvemos em um try/except para o app não quebrar se as credenciais estiverem erradas
try:
    spotify = spotipy.Spotify(auth_manager=SpotifyClientCredentials())
    logging.info("Autenticação com Spotify bem-sucedida.")
except Exception as e:
    logging.error(f"FALHA NA AUTENTICAÇÃO COM SPOTIFY. Verifique suas credenciais no arquivo .env. Erro: {e}")
    spotify = None

app = Flask(__name__)

# <--- FUNÇÃO ADICIONADA --->
def get_ffmpeg_path():
    """
    Determina o caminho para o ffmpeg. Se estiver rodando como um .exe (congelado),
    o caminho será para dentro do pacote. Caso contrário, assume que está no PATH do sistema.
    """
    if getattr(sys, 'frozen', False):
        # Caminho dentro do executável PyInstaller
        application_path = sys._MEIPASS
        return os.path.join(application_path, 'ffmpeg_binaries', 'ffmpeg.exe')
    else:
        # Caminho padrão (procura no PATH do sistema)
        return 'ffmpeg'

def is_spotify_url(url):
    """Verifica se uma URL pertence ao Spotify."""
    return "open.spotify.com" in url

def get_spotify_track_info(url):
    """Busca o nome da música e o artista de uma URL do Spotify."""
    if not spotify:
        raise Exception("Autenticação com Spotify não foi configurada ou falhou.")
        
    track = spotify.track(url)
    artist_name = track['artists'][0]['name']
    track_name = track['name']
    return f"{artist_name} - {track_name}"

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        video_url = request.form.get('url')
        if not video_url:
            return render_template('index.html', error="Por favor, insira uma URL.")

        temp_dir = tempfile.mkdtemp()
        search_query = video_url
        download_title = ""

        try:
            # Se a URL for do Spotify, identifica a música e prepara uma busca no YouTube
            if is_spotify_url(video_url):
                track_info = get_spotify_track_info(video_url)
                download_title = f"{track_info}.mp3" # Nome do arquivo final
                search_query = f"ytsearch1:{track_info}" # Comando de busca para o yt-dlp
                logging.info(f"Link do Spotify detectado. Buscando no YouTube por: '{track_info}'")
            else:
                logging.info(f"Link direto detectado. Baixando de: {video_url}")

            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
                'ffmpeg_location': get_ffmpeg_path(), # <--- LINHA ADICIONADA
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'noplaylist': True,
                # Evita baixar vídeos muito longos que não são músicas (ex: shows completos)
                'match_filter': yt_dlp.utils.match_filter_func("duration < 600"), 
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # O yt-dlp baixa a URL ou o primeiro resultado da busca
                info_dict = ydl.extract_info(search_query, download=True)

                # Se for uma busca no youtube, o resultado vem dentro de uma lista 'entries'
                if 'entries' in info_dict:
                    # Verifica se a lista de entries não está vazia (nenhum vídeo foi baixado)
                    if not info_dict['entries']:
                        logging.error("Nenhum vídeo foi baixado, pois todos foram filtrados.")
                        # Lança uma exceção com uma mensagem amigável para o usuário
                        raise Exception("Nenhum vídeo correspondente (com menos de 10 min) foi encontrado.")
                    
                    # Se a lista não estiver vazia, pegamos o primeiro item
                    info_dict = info_dict['entries'][0]
                
                original_filename = ydl.prepare_filename(info_dict)
                base, _ = os.path.splitext(original_filename)
                final_filename = base + '.mp3'
                downloaded_file_name = os.path.basename(final_filename)
                
                if not download_title:
                    download_title = f"{info_dict.get('title', 'audio')}.mp3"

            @after_this_request
            def cleanup(response):
                try:
                    os.remove(final_filename)
                    os.rmdir(temp_dir)
                except Exception as e:
                    logging.error(f"Erro ao limpar diretório: {e}")
                return response

            return send_from_directory(
                temp_dir,
                downloaded_file_name,
                as_attachment=True,
                download_name=download_title
            )

        except Exception as e:
            logging.error(f"Ocorreu um erro geral: {e}")
            return render_template('index.html', error=f"Ocorreu um erro: {e}")

    # Se a requisição for GET (primeiro acesso à página), apenas mostra o HTML
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)