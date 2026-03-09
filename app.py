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
        except Exception as e:
            print(f"Erro ao verificar integridade do DB: {e}")
            try: os.remove(DB_NAME)
            except Exception as ex: print(f"Erro ao deletar DB corrompido: {ex}")

def get_db():
    conn = sqlite3.connect(DB_NAME, timeout=20, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try: 
        conn.execute('PRAGMA journal_mode=WAL')
    except Exception as e: 
        print(f"Erro ao ativar WAL mode: {e}")
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
            print(f"Aviso na inicialização do DB: {e}")

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
            if "descricao" in dados:
                txt = dados["descricao"].strip()
                if txt.startswith('"') and txt.endswith('"'):
                    txt = txt[1:-1]
                dados["descricao"] = txt.strip()
            return dados
        except Exception as e: 
            print(f"Erro ao fazer parse do regex JSON: {e}")
    try:
        return json.loads(content)
    except Exception as e:
        print(f"Erro no fallback do parse JSON: {e}")
        return {}

def gerar_resposta_ia(prompt):
    with ia_lock: 
        if GEMINI_API_KEY:
            try:
                url_gemini = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
                payload_gemini = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json"}
                }
                res_gemini = requests.post(url_gemini, json=payload_gemini, timeout=45) 
                if res_gemini.status_code == 200:
                    content = res_gemini.json()['candidates'][0]['content']['parts'][0]['text']
                    return limpar_e_parsear_json(content)
            except Exception as e: 
                print(f"Erro na tentativa com Gemini: {e}")

        if GROQ_API_KEY:
            try:
                url_groq = "https://api.groq.com/openai/v1/chat/completions"
                headers_groq = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
                payload_groq = {
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.85, 
                    "response_format": {"type": "json_object"} 
                }
                res_groq = requests.post(url_groq, headers=headers_groq, json=payload_groq, timeout=25)
                if res_groq.status_code == 200:
                    content = res_groq.json()['choices'][0]['message']['content']
                    return limpar_e_parsear_json(content)
            except Exception as e: 
                print(f"Erro na tentativa com Groq: {e}")
        
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
        except Exception as e: 
            print(f"Erro ao atualizar progresso DB: {e}")

def get_progresso(session_id):
    try:
        with get_db() as conn:
            row = conn.execute('SELECT * FROM progress WHERE session_id = ?', (session_id,)).fetchone()
            if row:
                return {"atual": row['atual'], "total": row['total'], "finalizado": bool(row['finalizado']), "filme_atual": row['filme_atual']}
    except Exception as e: 
        print(f"Erro ao ler progresso DB: {e}")
    return {"atual": 0, "total": 0, "finalizado": False, "filme_atual": "Aguardando..."}

def salvar_sessao(session_id, vistos, amados, odiados, watchlist):
    with db_lock:
        try:
            with get_db() as conn:
                conn.execute('''INSERT OR REPLACE INTO sessions (session_id, vistos, amados, odiados, watchlist)
                                VALUES (?, ?, ?, ?, ?)''', 
                                (session_id, json.dumps(vistos), json.dumps(amados), json.dumps(odiados), json.dumps(watchlist)))
        except Exception as e: 
            print(f"Erro ao salvar sessao DB: {e}")

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
    except Exception as e: 
        print(f"Erro ao carregar sessao DB: {e}")
    return None

def get_cache_streamings(chave):
    try:
        with get_db() as conn:
            row = conn.execute('SELECT streamings FROM global_cache WHERE chave = ?', (chave,)).fetchone()
            if row:
                return json.loads(row['streamings'])
    except Exception as e: 
        print(f"Erro ao buscar cache DB: {e}")
    return None

def set_cache_streamings(chave, streamings):
    with db_lock:
        try:
            with get_db() as conn:
                conn.execute('INSERT OR REPLACE INTO global_cache (chave, streamings) VALUES (?, ?)', (chave, json.dumps(streamings)))
        except Exception as e: 
            print(f"Erro ao salvar cache DB: {e}")

def salvar_dados_finais(session_id, dados):
    with db_lock:
        try:
            with get_db() as conn:
                conn.execute('INSERT OR REPLACE INTO dados_finais (session_id, dados) VALUES (?, ?)', (session_id, json.dumps(dados)))
        except Exception as e: 
            print(f"Erro ao salvar dados finais DB: {e}")

def get_dados_finais(session_id):
    try:
        with get_db() as conn:
            row = conn.execute('SELECT dados FROM dados_finais WHERE session_id = ?', (session_id,)).fetchone()
            if row:
                return json.loads(row['dados'])
    except Exception as e: 
        print(f"Erro ao ler dados finais DB: {e}")
    return {"stats": {}, "watchlist": {}}

def resolve_boxd_links(links_str):
    if pd.isna(links_str) or not str(links_str).strip():
        return []
    urls = [url.strip() for url in str(links_str).split(',') if url.strip()]
    filmes = []
    for url in urls:
        try:
            res = requests.head(url, allow_redirects=True, timeout=5)
            partes = res.url.strip('/').split('/')
            if 'film' in partes:
                slug = partes[partes.index('film') + 1]
                slug = re.sub(r'-\d{4}$', '', slug)
                filmes.append(slug.replace('-', ' ').title())
        except Exception as e: 
            print(f"Erro ao resolver link Boxd ({url}): {e}")
    return filmes

# ==========================================
# ROTAS DA API
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
    except Exception as e: 
        print(f"Erro API TMDB Search: {e}")
        return jsonify({"results": []}), 200

@app.route('/')
def index(): 
    return render_template('index.html')

@app.route('/frases', methods=['GET'])
def get_frases():
    try:
        with open(ARQUIVO_FRASES, 'r', encoding='utf-8') as f:
            return jsonify([linha.strip() for linha in f.readlines() if linha.strip()])
    except Exception as e: 
        print(f"Erro ao carregar frases: {e}")
        return jsonify(["Analisando a sua curadoria..."])

@app.route('/progress', methods=['GET'])
def route_get_progress(): 
    return jsonify(get_progresso(request.args.get('session_id', 'default')))

# --- ROTA DE DADOS ATUALIZADA SEGUNDO A RECOMENDAÇÃO ---
@app.route('/dados', methods=['GET'])
def get_dados():
    sid = request.args.get('session_id', 'default')
    dados = get_dados_finais(sid)
    return jsonify(dados)

@app.route('/upload_profile', methods=['POST'])
def upload_profile():
    if 'file' not in request.files: 
        return jsonify({'erro': 'Arquivo ausente'}), 400
    
    file = request.files['file']
    sid = request.form.get('session_id', 'default')
    
    try:
        stats = {"total_avaliados": 0, "media_notas": 0, "favoritos": [], "username": "", "bio": "", "profile_favorites": []}
        vistos, amados, watchlist = set(), [], []
        if file.filename.lower().endswith('.zip'):
            with zipfile.ZipFile(file, 'r') as z:
                if 'profile.csv' in z.namelist():
                    with z.open('profile.csv') as f:
                        df = pd.read_csv(f)
                        if not df.empty:
                            stats["username"] = str(df.iloc[0].get("Username", ""))
                            stats["bio"] = re.sub(r'<[^>]+>', '', str(df.iloc[0].get("Bio", ""))) if str(df.iloc[0].get("Bio", "")) != 'nan' else ""
                            stats["profile_favorites"] = resolve_boxd_links(str(df.iloc[0].get("Favorite Films", "")))
                
                if 'watched.csv' in z.namelist():
                    with z.open('watched.csv') as f: 
                        vistas_list = pd.read_csv(f)['Name'].fillna("").str.lower().tolist()
                        vistos.update(vistas_list)
                
                if 'ratings.csv' in z.namelist():
                    with z.open('ratings.csv') as f:
                        df = pd.read_csv(f)
                        vistos.update(df['Name'].fillna("").str.lower().tolist())
                        stats["total_avaliados"] = len(df)
                        stats["media_notas"] = round(float(df['Rating'].mean()), 2)
                        favs = df[df['Rating'] >= 4.5]
                        amados = favs['Name'].fillna("").tolist()
                        top_favs = pd.concat([favs, df[df['Rating'] < 4.5].sort_values(by='Rating', ascending=False)]).head(20)
                        stats["favoritos"] = top_favs[['Name', 'Year', 'Rating']].fillna("").to_dict('records')
                
                if 'watchlist.csv' in z.namelist():
                    with z.open('watchlist.csv') as f:
                        df = pd.read_csv(f)
                        watchlist = df[['Name', 'Year']].fillna("").to_dict('records')
        
        salvar_sessao(sid, list(vistos), amados, [], watchlist)
        set_progresso(sid, 0, 0, False, "Aguardando...")
        return jsonify({'stats': stats})
    except Exception as e: 
        print(f"Erro ao processar arquivo ZIP: {e}")
        return jsonify({'erro': str(e)}), 500

@app.route('/gerar_perfil', methods=['POST'])
def gerar_perfil():
    stats = request.json.get('stats', {})
    prompt = f"""Atue como um crítico de cinema do Letterboxd insuportável, esnobe e cronicamente online.
    Username: {stats.get('username')}, Bio: "{stats.get('bio')}", Favoritos: {', '.join(stats.get('profile_favorites', []))}, Média: {stats.get('media_notas')}.
    MISSÃO: Escreva um Roast letal em 2 PARÁGRAFOS curtos. Use apenas: 🙈🤓😼🥺😿😻💋🫦🔥💅👍☠️💀😢😭😞😓😔🤤🙄.
    {{ "titulo": "TÍTULO", "personagem_referencia": "NOME", "filme_referencia": "FILME", "descricao": "ROAST" }}"""
    try: 
        return jsonify(gerar_resposta_ia(prompt))
    except Exception as e: 
        print(f"Erro ao gerar perfil IA: {e}")
        return jsonify({"titulo": "Algoritmo em Choque 💀", "personagem_referencia": "Bateman", "filme_referencia": "American Psycho", "descricao": "Gosto caótico demais. 🙄💅"})

@app.route('/oraculo', methods=['GET', 'POST'])
def oraculo():
    sid = request.args.get('session_id', 'default')
    sessao = carregar_sessao(sid)
    if not sessao: return jsonify({"erro": "Sessão não encontrada"}), 400
    
    try:
        vistos = set(sessao.get('vistos', []))
        watchlist_names = set(f.get('Name', '').lower().strip() for f in sessao.get('watchlist', []))
        excl_sessao = set(f.lower().strip() for f in (request.json.get('exclude', []) if request.is_json else []))
        blacklist_total = vistos.union(watchlist_names).union(excl_sessao)
        
        recs_finais = []
        tentativas_ia = 0
        is_real_terror = False

        while len(recs_finais) < 4 and tentativas_ia < 4:
            favoritos = request.json.get('favorites', [])
            blacklist_amostra = random.sample(list(blacklist_total), min(150, len(blacklist_total)))

            prompt = f"""Atue como curador profissional. Favoritos do usuário: {favoritos}.
            Recomende 25 filmes de estilo similar mas que sejam ABSOLUTAMENTE INÉDITOS para ele.
            
            ESQUEÇA ESTES FILMES (O usuário já viu ou conhece):
            {', '.join(blacklist_amostra)}
            {', '.join(list(excl_sessao)[:50])}
            
            DICA: Se ele gosta de coisas populares, procure o 'lado B'. Se gosta de cult, procure o 'underground'.
            {{ "recomendacoes": [ {{"rec_original": "TITLE", "rec": "TITLE", "ano": 2000, "base": "GENERO", "desc": "DESC"}} ] }}"""

            dados_json = gerar_resposta_ia(prompt)
            recs_ia = dados_json.get("recomendacoes", [])
            
            for r in recs_ia:
                nome = r.get('rec', '').strip().lower()
                orig = r.get('rec_original', '').strip().lower()
                
                if nome not in blacklist_total and orig not in blacklist_total:
                    if nome not in [rf['rec'].lower() for rf in recs_finais]:
                        recs_finais.append(r)
                        if len(recs_finais) >= 15: break 
            
            tentativas_ia += 1
            if tentativas_ia >= 3 and len(recs_finais) < 4:
                is_real_terror = True
            
            if len(recs_finais) < 4: 
                time.sleep(1.5)

        res_payload = {"recomendacoes": recs_finais}
        if is_real_terror:
            res_payload["terror_mode"] = True
            if len(recs_finais) > 0:
                recs_finais[0]["base"] = "O REAL TERROR"
                recs_finais[0]["desc"] = "Você já viu tudo o que existe? A IA desistiu de tentar te surpreender. Você é o verdadeiro terror do Letterboxd. 💀💅"

        return jsonify(res_payload)
    except Exception as e:
        print(f"Erro Oráculo: {e}")
        return jsonify({"erro": "Falha", "recomendacoes": []})

def processar_em_segundo_plano(watchlist_data, sid):
    dados_filmes = {}
    total = len(watchlist_data)
    atual = 0
    
    def fetch_movie(row):
        filme = row.get('Name', '')
        ano = row.get('Year', '')
        chave = f"{filme} ({ano})"
        
        cache = get_cache_streamings(chave)
        if cache: 
            return chave, cache
            
        streamings = []
        try:
            time.sleep(0.1) 
            
            url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={quote(filme)}&language=pt-BR"
            if ano and str(ano).isdigit(): 
                url += f"&year={int(float(ano))}"
            
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data.get('results'):
                    mid = data['results'][0]['id']
                    p_url = f"https://api.themoviedb.org/3/movie/{mid}/watch/providers?api_key={TMDB_API_KEY}"
                    p_res = requests.get(p_url, timeout=10)
                    if p_res.status_code == 200:
                        br = p_res.json().get('results', {}).get('BR', {})
                        for cat in ['flatrate', 'free', 'ads']:
                            if cat in br:
                                for p in br[cat]:
                                    if p['provider_name'] not in streamings: 
                                        streamings.append(p['provider_name'])
        except Exception as e: 
            print(f"Erro ao consultar TMDB para o filme '{filme}': {e}")
            
        if not streamings: 
            streamings.append("Não disponível")
        set_cache_streamings(chave, streamings)
        return chave, streamings
    
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_movie, row): row for row in watchlist_data}
            for future in concurrent.futures.as_completed(futures):
                try:
                    chave, st = future.result()
                    dados_filmes[chave] = st
                    atual += 1
                    set_progresso(sid, atual, total, False, chave)
                except Exception as ex:
                    print(f"Erro em uma das threads de busca de filme: {ex}")
                    
        salvar_dados_finais(sid, {"stats": {}, "watchlist": dados_filmes})
        
    except Exception as e:
        print(f"Processamento em background foi interrompido ou falhou brutalmente: {e}")
        salvar_dados_finais(sid, {"stats": {}, "watchlist": dados_filmes})
    finally:
        set_progresso(sid, total, total, True, "Finalizado!")

@app.route('/process_watchlist', methods=['POST'])
def process_watchlist():
    sid = (request.json or {}).get('session_id', 'default')
    sessao = carregar_sessao(sid)
    if not sessao or not sessao.get('watchlist'): 
        return jsonify({'erro': 'Vazia'}), 400
        
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
    except Exception as e: 
        print(f"Erro ao liberar porta: {e}")

if __name__ == '__main__':
    PORTA = 5000
    liberar_porta(PORTA)
    threading.Timer(1.5, lambda: webbrowser.open(f'http://127.0.0.1:{PORTA}')).start()
    app.run(port=PORTA, debug=False, threaded=True)
