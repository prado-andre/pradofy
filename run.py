import webbrowser
from waitress import serve
from app import app # Importa sua aplicação Flask do arquivo app.py

# Função para abrir o navegador automaticamente
def open_browser():
    webbrowser.open("http://127.0.0.1:5000")

if __name__ == '__main__':
    # Abre o navegador
    open_browser()
    # Inicia o servidor waitress para servir a aplicação
    serve(app, host="127.0.0.1", port=5000)