import sys
import os
from flask import Flask, render_template
from dotenv import load_dotenv

# Lógica de carregamento do .env que já tínhamos
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(base_path, '.env')
load_dotenv(dotenv_path=dotenv_path)

app = Flask(__name__)

# A única função do Flask agora é mostrar a página principal
@app.route('/')
def home():
    return render_template('index.html')