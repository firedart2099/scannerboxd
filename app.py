import os
import json
import time
import pandas as pd
import zipfile
import random
import requests
import re
import threading
import subprocess
import platform
import webbrowser
import sqlite3
import concurrent.futures
from flask import Flask, render_template, request, jsonify, Response
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
ARQUIVO_FRASES = "frases.txt" 

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
DB_NAME = "oraculo.db"

db_lock = threading.Lock()
ia_lock = threading.Lock() # Fila indiana para as IAs

# ==========================================
# GATILHO DE ANIVERSÁRIO DA LAURA
# ==========================================
IS_LAURA_BIRTHDAY_ACTIVE = True

# ==========================================
# CONFIGURAÇÃO DO BANCO DE DADOS SQLITE
# ==========================================
def check_db_health():
    if os.path.exists(DB_NAME):
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute('PRAGMA integrity_check;')
            result = cursor.fetchone()
            conn.close()
            if result and str(result[0]).lower() != 'ok':
                os.remove(DB_NAME)
        except Exception:
            try: os.remove(DB_NAME)
            except: pass

def get_db():
    conn = sqlite3.connect(DB_NAME, timeout=20, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try: conn.execute('PRAGMA journal_mode=WAL')
    except: pass
    return conn

def init_db():
    check_db_health()
    with db_lock:
        try:
            with get_db() as conn:
                c = conn.cursor()
                c.execute('''CREATE TABLE IF NOT EXISTS sessions
                             (session_id TEXT PRIMARY KEY, vistos TEXT, amados TEXT, odiados TEXT, watchlist TEXT)''')
                c.execute('''CREATE TABLE IF NOT EXISTS progress
                             (session_id TEXT PRIMARY KEY, atual INTEGER, total INTEGER, finalizado INTEGER, filme_atual TEXT)''')
                c.execute('''CREATE TABLE IF NOT EXISTS credits
                             (ip TEXT PRIMARY KEY, creditos INTEGER)''')
                c.execute('''CREATE TABLE IF NOT EXISTS global_cache
                             (chave TEXT PRIMARY KEY, streamings TEXT)''')
                c.execute('''CREATE TABLE IF NOT EXISTS dados_finais
                             (session_id TEXT PRIMARY KEY, dados TEXT)''')
                conn.commit()
        except Exception as e:
            print("Aviso na inicialização do DB:", e)

init_db()

# ==========================================
# TRATAMENTO DE ERROS GLOBAIS DO SERVIDOR
# ==========================================
@app.errorhandler(Exception)
def handle_exception(e):
    return jsonify({"erro": f"Erro interno do servidor: {str(e)}"}), 500

# ==========================================
# MOTOR HÍBRIDO DE INTELIGÊNCIA ARTIFICIAL (GEMINI -> GROQ)
# ==========================================
def limpar_e_parsear_json(content):
    content = re.sub(r'^```json\s*', '', content, flags=re.MULTILINE|re.IGNORECASE)
    content = re.sub(r'^```\s*', '', content, flags=re.MULTILINE).strip()
    match = re.search(r'\{.*\}', content, re.DOTALL)
    if match:
        try:
            dados = json.loads(match.group(0))
            # Limpa aspas extras que a IA as vezes coloca no início/fim da descrição
            if "descricao" in dados:
                dados["descricao"] = dados["descricao"].strip().strip('"').strip("'")
            return dados
        except: pass
    return json.loads(content)

def gerar_resposta_ia(prompt):
    with ia_lock: 
        if GEMINI_API_KEY:
            try:
                url_gemini = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
                payload_gemini = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json"}
                }
                res_gemini = requests.post(url_gemini, json=payload_gemini, timeout=35) 
                if res_gemini.status_code == 200:
                    content = res_gemini.json()['candidates'][0]['content']['parts'][0]['text']
                    return limpar_e_parsear_json(content)
            except: pass

        if GROQ_API_KEY:
            try:
                url_groq = "https://api.groq.com/openai/v1/chat/completions"
                headers_groq = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
                payload_groq = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.8, 
                    "response_format": {"type": "json_object"} 
                }
                res_groq = requests.post(url_groq, headers=headers_groq, json=payload_groq, timeout=15)
                if res_groq.status_code == 200:
                    content = res_groq.json()['choices'][0]['message']['content']
                    return limpar_e_parsear_json(content)
            except: pass
        
        raise Exception("RATE_LIMIT")

# ==========================================
# FUNÇÕES DE ESTADO (BANCO DE DADOS)
# ==========================================
def set_progresso(session_id, atual, total, finalizado, filme_atual):
    with db_lock:
        try:
            with get_db() as conn:
                conn.execute('''INSERT OR REPLACE INTO progress (session_id, atual, total, finalizado, filme_atual)
                                VALUES (?, ?, ?, ?, ?)''', (session_id, atual, total, int(finalizado), filme_atual))
        except: pass

def get_progresso(session_id):
    try:
        with get_db() as conn:
            row = conn.execute('SELECT * FROM progress WHERE session_id = ?', (session_id,)).fetchone()
            if row:
                return {"atual": row['atual'], "total": row['total'], "finalizado": bool(row['finalizado']), "filme_atual": row['filme_atual']}
    except: pass
    return {"atual": 0, "total": 0, "finalizado": False, "filme_atual": "Aguardando..."}

def salvar_sessao(session_id, vistos, amados, odiados, watchlist):
    with db_lock:
        try:
            with get_db() as conn:
                conn.execute('''INSERT OR REPLACE INTO sessions (session_id, vistos, amados, odiados, watchlist)
                                VALUES (?, ?, ?, ?, ?)''', 
                                (session_id, json.dumps(vistos), json.dumps(amados), json.dumps(odiados), json.dumps(watchlist)))
        except: pass

def carregar_sessao(session_id):
    try:
        with get_db() as conn:
            row = conn.execute('SELECT * FROM sessions WHERE session_id = ?', (session_id,)).fetchone()
            if row:
                return {
                    'vistos': json.loads(row['vistos']),
                    'amados': json.loads(row['amados']),
                    'odiados': json.loads(row['odiados']),
                    'watchlist': json.loads(row['watchlist'])
                }
    except: pass
    return None

def get_cache_streamings(chave):
    try:
        with get_db() as conn:
            row = conn.execute('SELECT streamings FROM global_cache WHERE chave = ?', (chave,)).fetchone()
            if row:
                return json.loads(row['streamings'])
    except: pass
    return None

def set_cache_streamings(chave, streamings):
    with db_lock:
        try:
            with get_db() as conn:
                conn.execute('INSERT OR REPLACE INTO global_cache (chave, streamings) VALUES (?, ?)', (chave, json.dumps(streamings)))
        except: pass

def salvar_dados_finais(session_id, dados):
    with db_lock:
        try:
            with get_db() as conn:
                conn.execute('INSERT OR REPLACE INTO dados_finais (session_id, dados) VALUES (?, ?)', (session_id, json.dumps(dados)))
        except: pass

def get_dados_finais(session_id):
    try:
        with get_db() as conn:
            row = conn.execute('SELECT dados FROM dados_finais WHERE session_id = ?', (session_id,)).fetchone()
            if row:
                return json.loads(row['dados'])
    except: pass
    return {}

def get_ip():
    if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        return request.environ['REMOTE_ADDR']
    else:
        return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0]

def resolve_boxd_links(links_str):
    if pd.isna(links_str) or not str(links_str).strip():
        return []
    urls = [url.strip() for url in str(links_str).split(',') if url.strip()]
    filmes = []
    for url in urls:
        try:
            res = requests.head(url, allow_redirects=True, timeout=3)
            partes = res.url.strip('/').split('/')
            if 'film' in partes:
                slug = partes[partes.index('film') + 1]
                slug = re.sub(r'-\d{4}$', '', slug)
                filmes.append(slug.replace('-', ' ').title())
        except: pass
    return filmes

# ==========================================
# ROTAS DA API & FRONTEND
# ==========================================
@app.route('/api/creditos', methods=['GET'])
def check_creditos():
    return jsonify({"creditos": 999})

@app.route('/api/consumir_credito', methods=['POST'])
def consume_credito():
    return jsonify({"sucesso": True, "creditos": 999})

@app.route('/api/adicionar_credito', methods=['POST'])
def add_credito():
    return jsonify({"sucesso": True, "creditos": 999})

@app.route('/api/tmdb/search', methods=['GET'])
def tmdb_search():
    q = request.args.get('query', '')
    y = request.args.get('year', '')
    if not TMDB_API_KEY: 
        return jsonify({"results": []}), 200
    url = f'https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={quote(q)}&language=pt-BR'
    if y: url += f'&year={y}'
    try: 
        res = requests.get(url, timeout=10)
        return jsonify(res.json()) if res.status_code == 200 else jsonify({"results": []})
    except: return jsonify({"results": []}), 200

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ping')
def ping():
    return "Pong! Servidor acordado.", 200

@app.route('/dados')
def dados():
    session_id = request.args.get('session_id', 'default')
    return jsonify(get_dados_finais(session_id))

@app.route('/frases')
def get_frases():
    try:
        with open(ARQUIVO_FRASES, 'r', encoding='utf-8') as f:
            return jsonify([linha.strip() for linha in f.readlines() if linha.strip()])
    except: 
        return jsonify(["Analisando a sua curadoria..."])

@app.route('/progress')
def route_get_progress():
    session_id = request.args.get('session_id', 'default')
    return jsonify(get_progresso(session_id))

@app.route('/upload_profile', methods=['POST'])
def upload_profile():
    if 'file' not in request.files: 
        return jsonify({'erro': 'Nenhum arquivo enviado'}), 400
    file = request.files['file']
    session_id = request.form.get('session_id', 'default')
    try:
        stats_usuario = {"total_avaliados": 0, "media_notas": 0, "favoritos": [], "username": "", "bio": "", "profile_favorites": [], "is_laura_birthday": False}
        vistos_temp = set()
        amados_temp, odiados_temp, watchlist_temp = [], [], []
        if file.filename.lower().endswith('.zip'):
            with zipfile.ZipFile(file, 'r') as z:
                if 'profile.csv' in z.namelist():
                    with z.open('profile.csv') as f_profile:
                        df_p = pd.read_csv(f_profile)
                        if not df_p.empty:
                            row = df_p.iloc[0]
                            stats_usuario["username"] = str(row.get("Username", ""))
                            stats_usuario["bio"] = re.sub(r'<[^>]+>', '', str(row.get("Bio", ""))) if str(row.get("Bio", "")) != 'nan' else ""
                            stats_usuario["profile_favorites"] = resolve_boxd_links(str(row.get("Favorite Films", "")))
                            if IS_LAURA_BIRTHDAY_ACTIVE and stats_usuario["username"].strip().lower() == 'lauraamora':
                                stats_usuario["is_laura_birthday"] = True
                if 'watched.csv' in z.namelist():
                    with z.open('watched.csv') as f_watched:
                        df_w = pd.read_csv(f_watched)
                        vistos_temp.update(df_w['Name'].fillna("").str.lower().tolist())
                if 'ratings.csv' in z.namelist():
                    with z.open('ratings.csv') as f_ratings:
                        df_r = pd.read_csv(f_ratings)
                        vistos_temp.update(df_r['Name'].fillna("").str.lower().tolist())
                        stats_usuario["total_avaliados"] = int(len(df_r))
                        stats_usuario["media_notas"] = round(float(df_r['Rating'].mean()), 2)
                        df_5 = df_r[df_r['Rating'] >= 4.5]
                        amados_temp = df_5['Name'].fillna("").tolist()
                        favs = pd.concat([df_5, df_r[df_r['Rating'] < 4.5].sort_values(by='Rating', ascending=False)]).head(20)
                        stats_usuario["favoritos"] = favs[['Name', 'Year', 'Rating']].fillna("").to_dict('records')
                if 'watchlist.csv' in z.namelist():
                    with z.open('watchlist.csv') as f_watch: 
                        df_watch = pd.read_csv(f_watch)
                        watchlist_temp = df_watch[['Name', 'Year']].fillna("").to_dict('records')
        salvar_sessao(session_id, list(vistos_temp), amados_temp, [], watchlist_temp)
        set_progresso(session_id, 0, 0, False, "Aguardando...")
        return jsonify({'stats': stats_usuario})
    except Exception as e: return jsonify({'erro': str(e)}), 500

@app.route('/gerar_perfil', methods=['POST'])
def gerar_perfil():
    dados = request.json
    stats = dados.get('stats', {})
    is_laura = stats.get('is_laura_birthday', False)
    
    if is_laura:
        prompt = f"""HOJE É O ANIVERSÁRIO DA LAURA (username: lauraamora)! 🎂
        DADOS DELA:
        - Bio: "{stats.get('bio', '')}"
        - Os 4 Favoritos: {', '.join(stats.get('profile_favorites', ['Nenhum']))}
        
        Sua missão é escrever um texto de FELIZ ANIVERSÁRIO super fofo, bem desenvolvido e natural. 
        REGRAS:
        1. Escreva 3 PARÁGRAFOS um pouco mais longos e detalhados. Nada de frases curtas de efeito.
        2. Fale como um amigo que realmente entende o gosto dela. Cite os filmes favoritos dela como parte da alma dela (ex: como ela enxerga a beleza no cotidiano tipo em 'About Time').
        3. No último parágrafo, diga que esse site inteiro foi alinhado hoje como um presente especial feito só pra ela.
        4. Use APENAS estes emojis: 🎂 ✨ 🎬 🤍.
        
        JSON estruturado OBRIGATÓRIO:
        {{
          "titulo": "✨ Feliz Aniversário, Laura! 🎂",
          "personagem_referencia": "[NOME DO PROTAGONISTA]",
          "filme_referencia": "[TITULO ORIGINAL DO FILME]",
          "descricao": "[TEXTO DESENVOLVIDO AQUI]"
        }}"""
    else:
        prompt = f"""Atue como um crítico de cinema insuportável do Letterboxd, esnobe, cronicamente online e maldoso.
        DADOS: Username: {stats.get('username')}, Bio: "{stats.get('bio')}", Favoritos: {', '.join(stats.get('profile_favorites', []))}, Média: {stats.get('media_notas')}.
        
        Missão: Faça um "Roast" letal do perfil na chave "descricao". 
        REGRAS:
        1. Escreva 2 PARÁGRAFOS com o tamanho padrão.
        2. ZERO "morde e assopra". Seja 100% julgador, irônico e maldoso do início ao fim.
        3. Ataque as contradições (ex: bio cult vs favoritos básicos, ou média alta demais indicando falta de critério). 
        4. Use EXCLUSIVAMENTE estes emojis: 🙈🤓😼🥺😿😻💋🫦🔥💅👍☠️💀😢😭😞😓😔🤤🙄.
        5. NUNCA use o emoji de red flag (🚩).
        6. REMOVA aspas extras no início e fim do texto.
        
        JSON estruturado OBRIGATÓRIO:
        {{
          "titulo": "[TITULO DEBOCHADO]",
          "personagem_referencia": "[PERSONAGEM DO FILME]",
          "filme_referencia": "[FILME ORIGINAL]",
          "descricao": "[ROAST SEM ASPAS EXTRAS]"
        }}"""

    try:
        dados_ia = gerar_resposta_ia(prompt)
        return jsonify(dados_ia)
    except Exception as e:
        if is_laura:
            return jsonify({"titulo": "✨ Feliz Aniversário, Laura! 🎂", "personagem_referencia": "Tim Lake", "filme_referencia": "About Time", "descricao": "Parabéns, Laura! ✨ Desejamos que o seu dia seja tão lindo quanto os filmes que você ama. Você tem essa sensibilidade única de encontrar magia nos pequenos momentos, e isso é raro. Hoje o site é todo seu! 🤍"})
        return jsonify({"titulo": "IAs em Colapso 🚦", "personagem_referencia": "The Flash", "filme_referencia": "Justice League", "descricao": "Limite atingido! Respire fundo 💅."})

@app.route('/oraculo', methods=['GET', 'POST'])
def oraculo():
    session_id = request.args.get('session_id', 'default')
    sessao = carregar_sessao(session_id)
    if not sessao: return jsonify({"erro": "Sessão não encontrada"}), 400
    try:
        vistos = sessao.get('vistos', [])
        excl = request.json.get('exclude', []) if request.is_json else []
        prompt = f"""Atue como um curador de cinema. Recomende 25 filmes baseados nestes favoritos: {request.json.get('favorites', [])}.
        REGRAS: 1. JSON estruturado. 2. Títulos originais em INGLÊS. 3. Ignorar: {excl}.
        {{ "recomendacoes": [ {{"rec_original": "TITLE", "rec": "TITLE", "ano": 2000, "base": "GENERO", "desc": "DESC"}} ] }}"""
        dados_json = gerar_resposta_ia(prompt)
        recs = [r for r in dados_json.get("recomendacoes", []) if r.get('rec', '').lower() not in vistos and r.get('rec', '').lower() not in [f.lower() for f in excl]]
        return jsonify({"recomendacoes": recs})
    except: return jsonify({"erro": "Falha", "recomendacoes": []})

def processar_em_segundo_plano(watchlist_data, session_id):
    dados_filmes, total, atual = {}, len(watchlist_data), 0
    def fetch_movie(row):
        filme, ano = row.get('Name', ''), row.get('Year', '')
        chave = f"{filme} ({ano})"
        cache = get_cache_streamings(chave)
        if cache: return chave, cache
        streamings = []
        try:
            url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={quote(filme)}&language=pt-BR"
            if ano: url += f"&year={int(float(ano))}"
            res = requests.get(url, timeout=10).json()
            if res.get('results'):
                mid = res['results'][0]['id']
                p_url = f"https://api.themoviedb.org/3/movie/{mid}/watch/providers?api_key={TMDB_API_KEY}"
                p_res = requests.get(p_url, timeout=10).json()
                br = p_res.get('results', {}).get('BR', {})
                for cat in ['flatrate', 'free', 'ads']:
                    if cat in br:
                        for p in br[cat]:
                            if p['provider_name'] not in streamings: streamings.append(p['provider_name'])
        except: pass
        if not streamings: streamings.append("Não disponível")
        set_cache_streamings(chave, streamings)
        return chave, streamings
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_movie, row): row for row in watchlist_data}
            for future in concurrent.futures.as_completed(futures):
                chave, st = future.result()
                dados_filmes[chave] = st
                atual += 1
                set_progresso(session_id, atual, total, False, chave)
        salvar_dados_finais(session_id, {"stats": {}, "watchlist": dados_filmes})
        set_progresso(session_id, total, total, True, "Finalizado!")
    except: set_progresso(session_id, total, total, True, "Erro.")

@app.route('/process_watchlist', methods=['POST'])
def process_watchlist():
    sid = (request.json or {}).get('session_id', 'default')
    sessao = carregar_sessao(sid)
    if not sessao or not sessao.get('watchlist'): return jsonify({'erro': 'Watchlist vazia'}), 400
    set_progresso(sid, 0, len(sessao['watchlist']), False, "Iniciando...")
    threading.Thread(target=processar_em_segundo_plano, args=(sessao['watchlist'], sid)).start()
    return jsonify({'mensagem': 'Iniciado'})

def liberar_porta(porta):
    try:
        if platform.system() == 'Windows':
            res = subprocess.run(f'netstat -ano | findstr :{porta}', shell=True, capture_output=True, text=True)
            for l in res.stdout.splitlines():
                if 'LISTENING' in l: subprocess.run(f'taskkill /F /PID {l.strip().split()[-1]}', shell=True)
        else:
            res = subprocess.run(f'lsof -t -i:{porta}', shell=True, capture_output=True, text=True)
            for p in res.stdout.strip().split('\n'):
                if p: os.system(f'kill -9 {p}')
    except: pass

if __name__ == '__main__':
    PORTA = 5000
    liberar_porta(PORTA)
    threading.Timer(1.5, lambda: webbrowser.open(f'http://127.0.0.1:{PORTA}')).start()
    app.run(port=PORTA, debug=False, threaded=True)
