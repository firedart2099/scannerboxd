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
from contextlib import closing
from flask import Flask, render_template, request, jsonify, Response
from urllib.parse import quote
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
ARQUIVO_FRASES = "frases.txt" 

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").replace('"', '').replace("'", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").replace('"', '').replace("'", "").strip()
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "").replace('"', '').replace("'", "").strip()
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "").replace('"', '').replace("'", "").strip()

DB_NAME = "oraculo.db"

db_lock = threading.Lock()

# ==========================================
# CONFIGURAÇÃO DO BANCO DE DADOS SQLITE
# ==========================================
def check_db_health():
    if os.path.exists(DB_NAME):
        try:
            with closing(sqlite3.connect(DB_NAME)) as conn:
                cursor = conn.cursor()
                cursor.execute('PRAGMA integrity_check;')
                result = cursor.fetchone()
                if result and str(result[0]).lower() != 'ok':
                    os.remove(DB_NAME)
        except Exception as e:
            try: os.remove(DB_NAME)
            except Exception: pass

def get_db():
    conn = sqlite3.connect(DB_NAME, timeout=20, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try: conn.execute('PRAGMA journal_mode=WAL')
    except Exception: pass
    return conn

def init_db():
    check_db_health()
    with db_lock:
        try:
            with closing(get_db()) as conn:
                with conn:
                    c = conn.cursor()
                    c.execute('''CREATE TABLE IF NOT EXISTS sessions (session_id TEXT PRIMARY KEY, vistos TEXT, amados TEXT, odiados TEXT, watchlist TEXT)''')
                    c.execute('''CREATE TABLE IF NOT EXISTS progress (session_id TEXT PRIMARY KEY, atual INTEGER, total INTEGER, finalizado INTEGER, filme_atual TEXT)''')
                    c.execute('''CREATE TABLE IF NOT EXISTS credits (ip TEXT PRIMARY KEY, creditos INTEGER)''')
                    c.execute('''CREATE TABLE IF NOT EXISTS global_cache (chave TEXT PRIMARY KEY, streamings TEXT)''')
                    c.execute('''CREATE TABLE IF NOT EXISTS dados_finais (session_id TEXT PRIMARY KEY, dados TEXT)''')
        except Exception: pass

init_db()

@app.errorhandler(Exception)
def handle_exception(e):
    return jsonify({"erro": f"Erro interno do servidor: {str(e)}"}), 500

# ==========================================
# MOTOR DE INTELIGÊNCIA ARTIFICIAL (NVIDIA -> GROQ -> GEMINI)
# ==========================================
def limpar_e_parsear_json(content):
    content = re.sub(r'^```json\s*', '', content, flags=re.MULTILINE|re.IGNORECASE)
    content = re.sub(r'^```\s*', '', content, flags=re.MULTILINE).strip()
    
    dados = None
    match = re.search(r'\{.*\}', content, re.DOTALL)
    if match:
        try: dados = json.loads(match.group(0), strict=False)
        except Exception: pass
            
    if not dados:
        try: dados = json.loads(content, strict=False)
        except Exception: return {}

    if isinstance(dados, dict):
        for key, value in dados.items():
            if isinstance(value, str):
                dados[key] = value.replace('"', '').replace('*', '').strip()
        if "recomendacoes" in dados and isinstance(dados["recomendacoes"], list):
            for rec in dados["recomendacoes"]:
                for k, v in rec.items():
                    if isinstance(v, str):
                        rec[k] = v.replace('"', '').replace('*', '').strip()
    return dados

def gerar_resposta_ia(prompt, max_tokens=1000):
    if NVIDIA_API_KEY:
        try:
            url_nv = "https://integrate.api.nvidia.com/v1/chat/completions"
            headers_nv = {"Authorization": f"Bearer {NVIDIA_API_KEY}", "Content-Type": "application/json"}
            payload_nv = {
                "model": "meta/llama-3.3-70b-instruct",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.85,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"} 
            }
            res_nv = requests.post(url_nv, headers=headers_nv, json=payload_nv, timeout=25)
            if res_nv.status_code == 200: return limpar_e_parsear_json(res_nv.json()['choices'][0]['message']['content'])
            else: print(f"⚠️ NVIDIA falhou (Status {res_nv.status_code})")
        except Exception as e: print(f"Erro NVIDIA: {e}")

    if GROQ_API_KEY:
        try:
            url_groq = "https://api.groq.com/openai/v1/chat/completions"
            headers_groq = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            payload_groq = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.85,
                "max_tokens": max_tokens, 
                "response_format": {"type": "json_object"} 
            }
            res_groq = requests.post(url_groq, headers=headers_groq, json=payload_groq, timeout=12)
            if res_groq.status_code == 200: return limpar_e_parsear_json(res_groq.json()['choices'][0]['message']['content'])
            else: print(f"⚠️ Groq falhou (Status {res_groq.status_code})")
        except Exception as e: print(f"Erro de conexão com Groq: {e}")

    if GEMINI_API_KEY:
        try:
            url_gemini = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
            payload_gemini = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": max_tokens}
            }
            res_gemini = requests.post(url_gemini, json=payload_gemini, timeout=15) 
            if res_gemini.status_code == 200: return limpar_e_parsear_json(res_gemini.json()['candidates'][0]['content']['parts'][0]['text'])
            else: print(f"⚠️ Gemini falhou (Status {res_gemini.status_code})")
        except Exception as e: print(f"Erro de conexão com Gemini: {e}")
    
    raise Exception("RATE_LIMIT")

# ==========================================
# FUNÇÕES DE ESTADO
# ==========================================
def set_progresso(session_id, atual, total, finalizado, filme_atual):
    with db_lock:
        try:
            with closing(get_db()) as conn:
                with conn: conn.execute('''INSERT OR REPLACE INTO progress (session_id, atual, total, finalizado, filme_atual) VALUES (?, ?, ?, ?, ?)''', (session_id, atual, total, int(finalizado), filme_atual))
        except Exception: pass

def get_progresso(session_id):
    try:
        with closing(get_db()) as conn:
            row = conn.execute('SELECT * FROM progress WHERE session_id = ?', (session_id,)).fetchone()
            if row: return {"atual": row['atual'], "total": row['total'], "finalizado": bool(row['finalizado']), "filme_atual": row['filme_atual']}
    except Exception: pass
    return {"atual": 0, "total": 0, "finalizado": False, "filme_atual": "Aguardando..."}

def salvar_sessao(session_id, vistos, amados, odiados, watchlist):
    with db_lock:
        try:
            with closing(get_db()) as conn:
                with conn: conn.execute('''INSERT OR REPLACE INTO sessions (session_id, vistos, amados, odiados, watchlist) VALUES (?, ?, ?, ?, ?)''', (session_id, json.dumps(vistos), json.dumps(amados), json.dumps(odiados), json.dumps(watchlist)))
        except Exception: pass

def carregar_sessao(session_id):
    try:
        with closing(get_db()) as conn:
            row = conn.execute('SELECT * FROM sessions WHERE session_id = ?', (session_id,)).fetchone()
            if row: return {'vistos': json.loads(row['vistos']), 'amados': json.loads(row['amados']), 'odiados': json.loads(row['odiados']), 'watchlist': json.loads(row['watchlist'])}
    except Exception: pass
    return None

def get_cache_streamings(chave):
    try:
        with closing(get_db()) as conn:
            row = conn.execute('SELECT streamings FROM global_cache WHERE chave = ?', (chave,)).fetchone()
            if row: return json.loads(row['streamings'])
    except Exception: pass
    return None

def set_cache_streamings(chave, streamings):
    with db_lock:
        try:
            with closing(get_db()) as conn:
                with conn: conn.execute('INSERT OR REPLACE INTO global_cache (chave, streamings) VALUES (?, ?)', (chave, json.dumps(streamings)))
        except Exception: pass

def salvar_dados_finais(session_id, dados):
    with db_lock:
        try:
            with closing(get_db()) as conn:
                with conn: conn.execute('INSERT OR REPLACE INTO dados_finais (session_id, dados) VALUES (?, ?)', (session_id, json.dumps(dados)))
        except Exception: pass

def get_dados_finais(session_id):
    try:
        with closing(get_db()) as conn:
            row = conn.execute('SELECT dados FROM dados_finais WHERE session_id = ?', (session_id,)).fetchone()
            if row: return json.loads(row['dados'])
    except Exception: pass
    return {"stats": {}, "watchlist": {}}

def resolve_boxd_links(links_str):
    if pd.isna(links_str) or not str(links_str).strip(): return []
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
        except Exception: pass
    return filmes

# ==========================================
# ROTAS DA API
# ==========================================
@app.route('/api/creditos', methods=['GET'])
def check_creditos(): return jsonify({"creditos": 999})
@app.route('/api/consumir_credito', methods=['POST'])
def consume_credito(): return jsonify({"sucesso": True, "creditos": 999})
@app.route('/api/adicionar_credito', methods=['POST'])
def add_credito(): return jsonify({"sucesso": True, "creditos": 999})

@app.route('/api/tmdb/search', methods=['GET'])
def tmdb_search():
    q = request.args.get('query', '')
    y = request.args.get('year', '')
    if not TMDB_API_KEY: return jsonify({"results": []}), 200
    url = f'https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={quote(q)}&language=pt-BR'
    if y: url += f'&year={y}'
    try: 
        res = requests.get(url, timeout=10)
        return jsonify(res.json()) if res.status_code == 200 else jsonify({"results": []})
    except Exception: return jsonify({"results": []}), 200

@app.route('/')
def index(): return render_template('index.html')

@app.route('/frases', methods=['GET'])
def get_frases():
    try:
        with open(ARQUIVO_FRASES, 'r', encoding='utf-8') as f:
            return jsonify([linha.strip() for linha in f.readlines() if linha.strip()])
    except Exception: return jsonify(["Analisando a sua curadoria..."])

@app.route('/progress', methods=['GET'])
def route_get_progress(): return jsonify(get_progresso(request.args.get('session_id', 'default')))

@app.route('/dados', methods=['GET'])
def get_dados(): return jsonify(get_dados_finais(request.args.get('session_id', 'default')))

@app.route('/upload_profile', methods=['POST'])
def upload_profile():
    if 'file' not in request.files: return jsonify({'erro': 'Arquivo ausente'}), 400
    file = request.files['file']
    sid = request.form.get('session_id', 'default')
    
    try:
        stats = {"total_avaliados": 0, "media_notas": 0, "favoritos": [], "username": "", "bio": "", "profile_favorites": [], "amados_recentes": [], "odiados_recentes": []}
        vistos, amados, watchlist = set(), [], []
        
        if file.filename.lower().endswith('.zip'):
            with zipfile.ZipFile(file, 'r') as z:
                for name in z.namelist():
                    if '__MACOSX' in name: continue 
                    if name.lower().endswith('profile.csv'):
                        with z.open(name) as f:
                            df = pd.read_csv(f)
                            if not df.empty:
                                stats["username"] = str(df.iloc[0].get("Username", ""))
                                stats["bio"] = re.sub(r'<[^>]+>', '', str(df.iloc[0].get("Bio", ""))) if str(df.iloc[0].get("Bio", "")) != 'nan' else ""
                                stats["profile_favorites"] = resolve_boxd_links(str(df.iloc[0].get("Favorite Films", "")))
                    elif name.lower().endswith('watched.csv'):
                        with z.open(name) as f: 
                            df_watched = pd.read_csv(f)
                            vistos.update(df_watched['Name'].fillna("").str.lower().tolist())
                    elif name.lower().endswith('ratings.csv'):
                        with z.open(name) as f:
                            df = pd.read_csv(f)
                            vistos.update(df['Name'].fillna("").str.lower().tolist())
                            stats["total_avaliados"] = len(df)
                            if 'Rating' in df.columns and not df.empty:
                                stats["media_notas"] = round(float(df['Rating'].mean()), 2)
                                favs = df[df['Rating'] >= 4.5]
                                amados = favs['Name'].fillna("").tolist()
                                stats["amados_recentes"] = amados[:5] 
                                odiados = df[df['Rating'] <= 2.0]
                                stats["odiados_recentes"] = odiados['Name'].fillna("").tolist()[:5] 
                                top_favs = pd.concat([favs, df[df['Rating'] < 4.5].sort_values(by='Rating', ascending=False)]).head(20)
                                stats["favoritos"] = top_favs[['Name', 'Year', 'Rating']].fillna("").to_dict('records')
                    elif name.lower().endswith('watchlist.csv'):
                        with z.open(name) as f:
                            df = pd.read_csv(f)
                            watchlist = df[['Name', 'Year']].fillna("").to_dict('records')
        
        salvar_sessao(sid, list(vistos), amados, [], watchlist)
        set_progresso(sid, 0, 0, False, "Aguardando...")
        return jsonify({'stats': stats})
    except Exception as e: return jsonify({'erro': str(e)}), 500

@app.route('/gerar_perfil', methods=['POST'])
def gerar_perfil():
    stats = request.json.get('stats', {})
    username = stats.get('username', 'Usuário')
    bio = stats.get('bio', '')
    
    filmes_amados = stats.get('profile_favorites', []) if stats.get('profile_favorites') else [f['Name'] for f in stats.get('favoritos', [])[:5]]
    amados_recentes = stats.get('amados_recentes', [])
    odiados_recentes = stats.get('odiados_recentes', [])
    
    emojis_permitidos = "🙈🤓😼🥺😿😻💋🫦🔥💅👍☠️💀😢😭😞😓😔🤤🙄"

    prompt = f"""Atue como um psicanalista de cinema que é muito cínico e sarcástico. Você está analisando o gosto de {username}.
    Bio: "{bio}". Favoritos: {', '.join(filmes_amados) if filmes_amados else 'Nenhum'}. Odiou (nota baixa): {', '.join(odiados_recentes) if odiados_recentes else 'Nenhum'}. Média: {stats.get('media_notas', 0)}.
    
    REGRAS DE OURO (Siga ou o código quebra):
    1. ELOQUÊNCIA E FLUIDEZ: NUNCA escreva frases robóticas ou fragmentadas do tipo "Você gosta de The Matrix. Você odeia Star Wars." Escreva um texto coeso, inteligente e fluido, como uma fofoca ácida ou uma crônica sarcástica, ligando os pontos do gosto dele. Use pontos finais adequadamente para não cansar a leitura.
    2. SINCERIDADE (SEM PUXA-SACO): Zombe das contradições do gosto dele. Seja afiado. É PROIBIDO usar palavras babonas como "refinado", "fascinante", "incrível", "digno de nota".
    3. EMOJIS (TRAVA RÍGIDA): Use EXATAMENTE entre 3 e 5 emojis espalhados no meio do texto. Você SÓ PODE usar emojis desta lista: {emojis_permitidos}. NUNCA crie uma lista explicando o que cada emoji significa.
    4. PERSONAGEM REFERÊNCIA: Escolha um personagem FAMOSO do cinema que represente a "vibe" dessa pessoa. É ESTRITAMENTE PROIBIDO escolher Tyler Durden, Patrick Bateman ou o Coringa. Escolha personagens complexos, mas conhecidos, e justifique a escolha numa única frase de encerramento sem repetir ideias anteriores.
    
    Responda OBRIGATORIAMENTE em JSON estrito:
    {{ 
        "titulo": "Rótulo Sarcástico (Ex: O Caçador de Contradições)", 
        "personagem_referencia": "Nome do Personagem Fictício", 
        "filme_referencia": "Nome do Filme Deste Personagem", 
        "descricao": ["Parágrafo 1 fluido focado na bio e filmes que ele ama.", "Parágrafo 2 fluido detonando o que ele odeia e concluindo brilhantemente com a revelação do personagem."] 
    }}"""
    
    try: 
        dados = gerar_resposta_ia(prompt, max_tokens=1000)
        if not dados or "titulo" not in dados: raise Exception("Falha JSON")
        if isinstance(dados.get("descricao"), list): dados["descricao"] = "\n\n".join(dados["descricao"])
        return jsonify(dados)
    except Exception as e: 
        return jsonify({
            "titulo": "O Explorador Silencioso", 
            "personagem_referencia": "Driver",
            "filme_referencia": "Drive", 
            "descricao": "O Oráculo está Meditando... 🧘‍♂️\n\nOpa desculpa pae! As IAs do servidor derreteram com tanto acesso hoje e não conseguiram decifrar seu gosto peculiar.\n\nMas ó, aproveite pra ver onde assistir sua Watchlist ali na aba do lado! 🍿"
        })

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

        while len(recs_finais) < 10 and tentativas_ia < 2:
            favoritos = request.json.get('favorites', [])
            blacklist_amostra = random.sample(list(blacklist_total), min(25, len(blacklist_total)))

            # Pede 12 filmes de uma vez para o buffer do frontend!
            prompt = f"""Atue como curador profissional. Favoritos do usuário: {favoritos}.
            Recomende EXATAMENTE 12 filmes de estilo similar mas que sejam ABSOLUTAMENTE INÉDITOS para ele.
            ESQUEÇA ESTES FILMES: {', '.join(blacklist_amostra)}. 
            NÃO USE asteriscos (*) nos nomes.
            Responda OBRIGATORIAMENTE em JSON:
            {{ "recomendacoes": [ {{"rec_original": "TITLE", "rec": "TITLE", "ano": 2000, "base": "GENERO", "desc": "Pequena sinopse."}} ] }}"""

            dados_json = gerar_resposta_ia(prompt, max_tokens=1500)
            recs_ia = dados_json.get("recomendacoes", []) if dados_json else []
            
            for r in recs_ia:
                nome = r.get('rec', '').strip().lower()
                orig = r.get('rec_original', '').strip().lower()
                if nome not in blacklist_total and orig not in blacklist_total:
                    if nome not in [rf['rec'].lower() for rf in recs_finais]:
                        recs_finais.append(r)
            
            tentativas_ia += 1
            if len(recs_finais) < 10: time.sleep(0.5)

        # RETORNA A LISTA CHEIA PRO FRONTEND ARMAZENAR NO BUFFER!
        return jsonify({"recomendacoes": recs_finais})
    except Exception as e:
        if "RATE_LIMIT" in str(e): return jsonify({"erro": "RATE_LIMIT", "recomendacoes": []})
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
        if cache: return chave, cache
            
        streamings = []
        try:
            url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={quote(filme)}&language=pt-BR"
            if ano and str(ano).isdigit(): url += f"&year={int(float(ano))}"
            res = requests.get(url, timeout=10)
            if res.status_code == 200 and res.json().get('results'):
                mid = res.json()['results'][0]['id']
                p_url = f"https://api.themoviedb.org/3/movie/{mid}/watch/providers?api_key={TMDB_API_KEY}"
                p_res = requests.get(p_url, timeout=10)
                if p_res.status_code == 200:
                    br = p_res.json().get('results', {}).get('BR', {})
                    for cat in ['flatrate', 'free', 'ads']:
                        if cat in br:
                            for p in br[cat]:
                                if p['provider_name'] not in streamings: streamings.append(p['provider_name'])
        except Exception: pass
            
        if not streamings: streamings.append("Não disponível")
        set_cache_streamings(chave, streamings)
        return chave, streamings
    
    try:
        # AUMENTADO PARA 15 MOTORES SIMULTÂNEOS! Watchlist turbo.
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            futures = {executor.submit(fetch_movie, row): row for row in watchlist_data}
            for future in concurrent.futures.as_completed(futures):
                try:
                    chave, st = future.result()
                    dados_filmes[chave] = st
                    atual += 1
                    set_progresso(sid, atual, total, False, chave)
                except Exception: pass
        salvar_dados_finais(sid, {"stats": {}, "watchlist": dados_filmes})
    except Exception: salvar_dados_finais(sid, {"stats": {}, "watchlist": dados_filmes})
    finally: set_progresso(sid, total, total, True, "Finalizado!")

@app.route('/process_watchlist', methods=['POST'])
def process_watchlist():
    sid = (request.json or {}).get('session_id', 'default')
    sessao = carregar_sessao(sid)
    if not sessao or not sessao.get('watchlist'): return jsonify({'erro': 'Vazia'}), 400
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
    except Exception: pass

if __name__ == '__main__':
    PORTA = 5000
    liberar_porta(PORTA)
    threading.Timer(1.5, lambda: webbrowser.open(f'http://127.0.0.1:{PORTA}')).start()
    app.run(port=PORTA, debug=False, threaded=True)
