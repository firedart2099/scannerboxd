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

# TÚNEL DE CONEXÃO TURBO PARA O TMDB
tmdb_session = requests.Session()

def check_db_health():
    if os.path.exists(DB_NAME):
        try:
            with closing(sqlite3.connect(DB_NAME)) as conn:
                cursor = conn.cursor()
                cursor.execute('PRAGMA integrity_check;')
                result = cursor.fetchone()
                if result and str(result[0]).lower() != 'ok':
                    os.remove(DB_NAME)
        except Exception:
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
                    c.execute('''CREATE TABLE IF NOT EXISTS global_cache (chave TEXT PRIMARY KEY, streamings TEXT)''')
                    c.execute('''CREATE TABLE IF NOT EXISTS dados_finais (session_id TEXT PRIMARY KEY, dados TEXT)''')
        except Exception: pass

init_db()

@app.errorhandler(Exception)
def handle_exception(e):
    return jsonify({"erro": f"Erro interno: {str(e)}"}), 500

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
            if isinstance(value, str): dados[key] = value.replace('"', '').replace('*', '').strip()
        if "recomendacoes" in dados and isinstance(dados["recomendacoes"], list):
            for rec in dados["recomendacoes"]:
                for k, v in rec.items():
                    if isinstance(v, str): rec[k] = v.replace('"', '').replace('*', '').strip()
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
            res_nv = requests.post(url_nv, headers=headers_nv, json=payload_nv, timeout=28)
            if res_nv.status_code == 200: return limpar_e_parsear_json(res_nv.json()['choices'][0]['message']['content'])
        except Exception: pass

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
        except Exception: pass

    if GEMINI_API_KEY:
        try:
            url_gemini = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
            payload_gemini = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": max_tokens}
            }
            res_gemini = requests.post(url_gemini, json=payload_gemini, timeout=15) 
            if res_gemini.status_code == 200: return limpar_e_parsear_json(res_gemini.json()['candidates'][0]['content']['parts'][0]['text'])
        except Exception: pass
    
    raise Exception("RATE_LIMIT")

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

def normalize_title(title):
    if not isinstance(title, str): return ""
    t = title.lower().strip()
    t = re.sub(r'^(the |a |an |o |os |a |as )', '', t)
    t = re.sub(r'[^a-z0-9]', '', t)
    if 'thirteenthfloor' in t or '13andar' in t: return '13thfloor'
    if 'seven' in t or 'se7en' in t: return 'se7en'
    return t

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
                                stats["amados_recentes"] = amados[:12] 
                                odiados = df[df['Rating'] <= 2.0]
                                stats["odiados_recentes"] = odiados['Name'].fillna("").tolist()[:12] 
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

    prompt = f"""Atue como um psicanalista de cinema brilhante, astuto e levemente cínico. O seu objetivo é fazer uma crônica psicológica do gosto cinematográfico de {username}.
    
    DADOS DA VÍTIMA:
    - Nome: {username}
    - Bio: "{bio}"
    - Filmes favoritos/amados: {', '.join(filmes_amados)}, {', '.join(amados_recentes)}
    - Filmes odiados: {', '.join(odiados_recentes)}
    
    REGRAS INQUEBRÁVEIS DE ESTILO:
    1. PROIBIDO FRASES ROBÓTICAS: Jamais escreva "Ele gosta disso, mas odeia aquilo". Flua o texto como uma crônica elegante e fluida, analisando a energia da pessoa e os contrastes. 
    2. PONTUAÇÃO (LEITURA DINÂMICA): Use pontos finais! Proibido criar frases infinitas com mil vírgulas. Cada parágrafo deve ter no máximo 4 frases diretas e matadoras.
    3. O PERSONAGEM: Escolha OBRIGATORIAMENTE um personagem de filme LIVE-ACTION (nada de livros, animações ou CGI) que tenha a exata energia e contradição dessa pessoa. É ESTRITAMENTE PROIBIDO escolher Tyler Durden, Coringa ou Patrick Bateman. Seja criativo.
    4. SINCERIDADE SEM BAJULAÇÃO: Seja 100% sincero e perspicaz, julgue o gosto com ironia, mas sem ofender de graça e SEM PUXAR O SACO. Pare de chamar o gosto de "refinado" ou "fascinante" toda hora.
    5. EMOJIS: Use EXCLUSIVAMENTE os emojis desta lista: {emojis_permitidos}. Espalhe uns 6 ou 7 pelo texto, NUNCA crie uma lista de significados no final.
    6. IDIOMA DOS FILMES: Mantenha os nomes dos filmes OBRIGATORIAMENTE EM INGLÊS.
    
    Responda OBRIGATORIAMENTE em JSON:
    {{ 
        "titulo": "Rótulo Criativo", 
        "personagem_referencia": "Nome do Personagem Fictício", 
        "filme_referencia": "Nome do Filme do Personagem (Inglês)", 
        "descricao": [
            "Primeiro parágrafo de análise psicológica ácida e fluida usando a bio e os filmes.",
            "Segundo parágrafo expondo as contradições e justificando o personagem de forma direta e matadora, sem repetição."
        ]
    }}"""
    
    try: 
        dados = gerar_resposta_ia(prompt, max_tokens=1500)
        if not dados or "titulo" not in dados: raise Exception("Falha JSON")
        if isinstance(dados.get("descricao"), list): dados["descricao"] = "\n\n".join(dados["descricao"])
        return jsonify(dados)
    except Exception as e: 
        return jsonify({
            "titulo": "O Explorador Silencioso 🧘‍♂️", 
            "personagem_referencia": "Driver",
            "filme_referencia": "Drive",
            "descricao": "Opa, desculpa pae! A Inteligência Artificial fritou os circuitos com tanta informação.\n\nMas ó, deslize pra aba do lado e aproveite pra ver onde assistir sua Watchlist ali na última aba! 🍿"
        })

@app.route('/oraculo', methods=['POST'])
def oraculo():
    sid = request.args.get('session_id', 'default')
    sessao = carregar_sessao(sid)
    if not sessao: return jsonify({"erro": "Sessão não encontrada"}), 400
    
    try:
        vistos = set(sessao.get('vistos', []))
        watchlist_names = set(f.get('Name', '').lower().strip() for f in sessao.get('watchlist', []))
        excl_sessao = set(f.lower().strip() for f in (request.json.get('exclude', []) if request.is_json else []))
        blacklist_total = vistos.union(watchlist_names).union(excl_sessao)
        
        blacklist_norm = {normalize_title(f) for f in blacklist_total if f}
        
        recs_finais = []
        tentativas_ia = 0

        while len(recs_finais) < 12 and tentativas_ia < 2:
            favoritos = request.json.get('favorites', [])
            blacklist_amostra = random.sample(list(blacklist_total), min(25, len(blacklist_total)))

            prompt = f"""Atue como curador profissional. Favoritos do usuário: {favoritos}.
            Recomende EXATAMENTE 15 filmes cults ou obscuros ABSOLUTAMENTE INÉDITOS para ele.
            NÃO recomende blockbusters genéricos. Vá fundo no catálogo Lado B.
            
            ESQUEÇA ESTES FILMES: {', '.join(blacklist_amostra)}
            
            Responda OBRIGATORIAMENTE em JSON:
            {{ "recomendacoes": [ {{"rec_original": "TITLE", "rec": "TITLE", "ano": 2000, "base": "GENERO", "desc": "Pequena sinopse."}} ] }}"""

            dados_json = gerar_resposta_ia(prompt, max_tokens=2500)
            recs_ia = dados_json.get("recomendacoes", []) if dados_json else []
            
            for r in recs_ia:
                nome = r.get('rec', '')
                orig = r.get('rec_original', '')
                
                norm_nome = normalize_title(nome)
                norm_orig = normalize_title(orig)
                
                if norm_nome not in blacklist_norm and norm_orig not in blacklist_norm:
                    clone = False
                    for rf in recs_finais:
                        rf_nome = normalize_title(rf.get('rec', ''))
                        rf_orig = normalize_title(rf.get('rec_original', ''))
                        if norm_nome in [rf_nome, rf_orig] or norm_orig in [rf_nome, rf_orig]:
                            clone = True
                            break
                    if not clone:
                        recs_finais.append(r)
            
            tentativas_ia += 1

        res_payload = {"recomendacoes": recs_finais}
        
        if len(recs_finais) == 0:
            res_payload["terror_mode"] = True

        return jsonify(res_payload)
    except Exception as e:
        print(f"Erro Oráculo: {e}")
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
            res = tmdb_session.get(url, timeout=5)
            if res.status_code == 200 and res.json().get('results'):
                mid = res.json()['results'][0]['id']
                p_url = f"https://api.themoviedb.org/3/movie/{mid}/watch/providers?api_key={TMDB_API_KEY}"
                p_res = tmdb_session.get(p_url, timeout=5)
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
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(fetch_movie, row): row for row in watchlist_data}
            for future in concurrent.futures.as_completed(futures):
                try:
                    chave, st = future.result()
                    dados_filmes[chave] = st
                    atual += 1
                    # Aceleração monstruosa: só escreve no disco a cada 5 filmes!
                    if atual % 5 == 0 or atual == total:
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
```

### 2. A INTERFACE OTIMIZADA E PÔSTER INSTANTÂNEO (`index (1).html`)
```html:Scannerbox Frontend:index (1).html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Scannerboxd</title>
    
    <!-- FAVICON -->
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><circle cx=%2220%22 cy=%2250%22 r=%2215%22 fill=%22%2300e054%22/><circle cx=%2250%22 cy=%2250%22 r=%2215%22 r=%2215%22 fill=%22%2340bcf4%22/><circle cx=%2280%22 cy=%2250%22 r=%2215%22 fill=%22%23ff8000%22/></svg>">
    
    <script>
        const twScript = document.createElement('script');
        twScript.src = "https://cdn.tailwindcss.com";
        document.head.appendChild(twScript);
    </script>
    
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;700;900&family=Space+Grotesk:wght@300;700;900&display=swap" rel="stylesheet">
    
    <style>
        body { 
            font-family: 'Inter', sans-serif;
            background-color: #0f1115;
            color: #ffffff;
            margin: 0; padding: 0;
            overflow-x: hidden;
        }

        h1, h2, h3, .space-font { font-family: 'Space Grotesk', sans-serif !important; }

        ::-webkit-scrollbar { width: 10px; }
        ::-webkit-scrollbar-track { background: rgba(15, 17, 21, 0.9); }
        ::-webkit-scrollbar-thumb { background: rgba(64, 188, 244, 0.4); border-radius: 10px; border: 2px solid rgba(15, 17, 21, 0.9); }
        ::-webkit-scrollbar-thumb:hover { background: rgba(64, 188, 244, 0.7); }

        .no-scrollbar::-webkit-scrollbar { display: none; }
        .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }

        /* O GLASSMORPHISM PREMIUM */
        .fluent-glass {
            background: rgba(24, 28, 33, 0.55) !important; 
            backdrop-filter: blur(24px) saturate(150%) !important; 
            -webkit-backdrop-filter: blur(24px) saturate(150%) !important;
            border: 1px solid rgba(255, 255, 255, 0.04) !important; 
            border-top: 1px solid rgba(255, 255, 255, 0.08) !important;
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.05) !important; 
            border-radius: 16px;
            transition: all 0.3s ease;
        }

        .fluent-glass:hover {
            border-color: rgba(64, 188, 244, 0.5) !important;
        }

        .bottom-nav-dot {
            width: 14px; height: 14px;
            border-radius: 50%;
            cursor: pointer;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            box-shadow: 0 0 10px rgba(0,0,0,0.5);
            user-select: none;
            -webkit-user-select: none;
        }
        .bottom-nav-dot.active { transform: scale(1.5); z-index: 10; box-shadow: 0 0 15px currentColor; }
        .dot-green { background-color: #00e054; color: #00e054; }
        .dot-blue { background-color: #40bcf4; color: #40bcf4; }
        .dot-orange { background-color: #ff8000; color: #ff8000; }

        .movie-card { aspect-ratio: 2/3; position: relative; border-radius: 12px; overflow: hidden; background: transparent; transition: border 0.3s ease; }
        
        .ps-trophy {
            position: fixed;
            top: 24px;
            right: -450px;
            width: 320px;
            background: rgba(20, 24, 28, 0.95);
            border: 1px solid rgba(64, 188, 244, 0.4);
            border-radius: 12px;
            padding: 16px;
            display: flex;
            align-items: center;
            gap: 16px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.8), inset 0 0 15px rgba(64,188,244,0.1);
            z-index: 100000;
            transition: right 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            backdrop-filter: blur(10px);
        }
        .ps-trophy.show { right: 24px; }
        
        .trophy-icon {
            width: 48px;
            height: 48px;
            background: radial-gradient(circle, rgba(64,188,244,0.2) 0%, transparent 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            border: 2px solid #40bcf4;
            box-shadow: 0 0 15px rgba(64,188,244,0.5);
            flex-shrink: 0;
            animation: pulseGlow 2s infinite;
        }
        @keyframes pulseGlow {
            0% { box-shadow: 0 0 10px rgba(64,188,244,0.3); }
            50% { box-shadow: 0 0 25px rgba(64,188,244,0.8); }
            100% { box-shadow: 0 0 10px rgba(64,188,244,0.3); }
        }
        @media (max-width: 640px) {
            .ps-trophy { width: 90%; top: auto; bottom: 24px; right: -100%; }
            .ps-trophy.show { right: 5%; }
        }
    </style>
</head>
<body class="text-white relative w-screen min-h-screen overflow-x-hidden overflow-y-auto pb-8">

<div id="custom-toast" class="fixed top-12 left-1/2 transform -translate-x-1/2 fluent-glass text-white px-6 py-3 rounded-full z-[100000] flex items-center gap-3 transition-all duration-500 opacity-0 pointer-events-none -translate-y-10 max-w-[90vw] shadow-2xl">
    <p id="custom-toast-msg" class="text-[10px] sm:text-xs font-bold uppercase tracking-widest text-center"></p>
</div>

<div id="ps-trophy" class="ps-trophy">
    <div class="trophy-icon">🏆</div>
    <div>
        <p class="text-[#40bcf4] text-[9px] font-black uppercase tracking-widest mb-0.5">Conquista Desbloqueada</p>
        <h4 class="text-white font-bold text-sm leading-tight mb-1">O Terror do Letterboxd 💀</h4>
        <p class="text-[#8c9bab] text-[10px] leading-snug">Você zerou o cinema! A IA esgotou suas recomendações e não consegue achar um filme que você não tenha visto.</p>
    </div>
</div>

<div class="fixed inset-0 w-full h-full z-0 bg-[#0f1115] pointer-events-none">
    <img id="hero-backdrop-img" src="" class="w-full h-full object-cover opacity-0 transition-opacity duration-1000 grayscale-[10%]" style="-webkit-mask-image: linear-gradient(to bottom, rgba(0,0,0,1) 0%, rgba(0,0,0,0.8) 50%, rgba(0,0,0,0) 100%); mask-image: linear-gradient(to bottom, rgba(0,0,0,1) 0%, rgba(0,0,0,0.8) 50%, rgba(0,0,0,0) 100%);">
    <div class="absolute inset-0 bg-gradient-to-b from-transparent via-[#0f1115]/10 to-[#0f1115] pointer-events-none"></div>
</div>

<header class="absolute top-6 left-6 md:top-8 md:left-8 flex items-start md:items-center gap-3 z-40 pointer-events-auto w-full justify-between pr-12 md:pr-16">
    <div class="flex items-center gap-1.5 cursor-pointer hover:scale-105 transition-transform" onclick="location.reload()">
        <div class="w-3 h-3 rounded-full bg-[#00e054]"></div>
        <div class="w-3 h-3 rounded-full bg-[#40bcf4]"></div>
        <div class="w-3 h-3 rounded-full bg-[#ff8000]"></div>
        <div class="flex flex-col ml-2">
            <h1 class="text-xl font-bold tracking-widest text-white uppercase leading-none shadow-black drop-shadow-md">Scanner<span class="text-[#40bcf4]">boxd</span></h1>
            <p class="text-[8px] text-[#8c9bab] font-bold tracking-[0.3em] uppercase drop-shadow-md mt-1">v1.0.0 Oficial</p>
        </div>
    </div>
    
    <div id="slideshow-info" class="transition-opacity duration-500 flex flex-col items-end text-right hidden sm:flex opacity-0">
        <h2 id="slide-title" class="text-sm md:text-lg font-black text-white tracking-tighter drop-shadow-md leading-tight mb-0.5 max-w-[200px] truncate">...</h2>
        <div class="flex items-center justify-end gap-2">
            <span id="slide-year" class="text-gray-300 font-bold text-[10px]"></span>
            <span id="slide-rating" class="text-[#00e054] text-[10px] tracking-widest drop-shadow-md hidden"></span>
        </div>
    </div>
</header>

<div id="main-content" class="relative w-full z-20 flex flex-col pt-[35vh] px-4 md:px-8 pb-32 transition-transform duration-700 ease-in-out">
    <div class="max-w-2xl mx-auto w-full">
        
        <div class="text-center space-y-2 mb-12">
            <h2 class="text-4xl md:text-6xl font-black text-white leading-tight tracking-tighter drop-shadow-2xl">
                QUAL É O SEU PERFIL <br>
                <span class="text-white italic pr-2 drop-shadow-[0_0_15px_rgba(255,255,255,0.15)]">CINEMATOGRÁFICO?</span>
            </h2>
            <p class="text-[#8c9bab] max-w-xl mx-auto text-sm md:text-base font-medium drop-shadow-md">Descubra a verdade sobre o seu gosto e encontre onde assistir a sua Watchlist.</p>
        </div>

        <div class="space-y-4 relative z-30">
            <a href="https://letterboxd.com/data/export/" target="_blank" class="fluent-glass flex items-center gap-4 px-6 py-4 w-full group hover:border-[#40bcf4]/50">
                <span class="bg-[#40bcf4]/20 text-[#40bcf4] w-7 h-7 rounded-full flex items-center justify-center text-xs font-black shrink-0 group-hover:bg-[#40bcf4] group-hover:text-[#0f1115] transition-colors">1</span>
                <div class="text-left">
                    <span class="font-bold text-sm tracking-wide block text-white drop-shadow-sm">Baixar arquivo .ZIP oficial</span>
                    <span class="text-[9px] uppercase tracking-widest text-[#8c9bab] group-hover:text-[#40bcf4] transition-colors">Abre o Letterboxd em nova aba</span>
                </div>
                <svg class="w-5 h-5 text-[#40bcf4] ml-auto opacity-70 group-hover:opacity-100" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
            </a>

            <div class="fluent-glass p-8 text-center hover:border-[#40bcf4]/50 transition-all group cursor-pointer relative overflow-hidden">
                <label for="csv-file" id="dropzone-label" class="cursor-pointer block w-full h-full">
                    <div class="w-16 h-16 bg-[#40bcf4]/10 rounded-full flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-all border border-[#40bcf4]/30 shadow-inner">
                        <svg class="w-8 h-8 text-[#40bcf4]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z"></path></svg>
                    </div>
                    <p class="text-xl md:text-2xl font-bold text-white mb-1 drop-shadow-sm">Arraste seu arquivo <span class="text-[#40bcf4]">.zip</span> aqui</p>
                    <p class="text-[9px] md:text-[10px] text-[#8c9bab] uppercase tracking-widest font-bold">Nenhum dado é salvo nos servidores</p>
                </label>
                <input type="file" id="csv-file" class="hidden" accept=".zip" onchange="fileSelected()">
                
                <div id="action-area" class="hidden mt-4 flex-col items-center gap-4 relative z-10">
                    <div class="flex items-center gap-2 bg-[#0f1115]/40 px-4 py-3 rounded-lg border border-[#40bcf4]/20 w-full justify-center shadow-inner">
                        <svg class="w-4 h-4 text-[#40bcf4]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                        <p id="file-name-display" class="text-[#40bcf4] font-mono text-sm truncate max-w-[250px] drop-shadow-md"></p>
                    </div>
                    <button id="btn-iniciar-real" onclick="handleFileUpload()" class="w-full bg-[#40bcf4] text-[#0f1115] font-black py-4 rounded-xl uppercase tracking-widest transition-all shadow-[0_0_20px_rgba(64,188,244,0.3)] hover:shadow-[0_0_35px_rgba(64,188,244,0.6)] flex items-center justify-center gap-2 hover:scale-[1.02]">
                        <span id="btn-text-real">Iniciar Análise</span>
                    </button>
                    <button onclick="resetUpload()" class="text-[10px] text-[#8c9bab] hover:text-white uppercase tracking-widest underline decoration-dashed">Escolher outro arquivo</button>
                </div>
            </div>

            <div class="text-center pt-6 pb-10">
                <button onclick="iniciarMockupTeste()" class="text-[10px] text-[#40bcf4] font-bold uppercase tracking-widest underline decoration-dashed hover:text-white transition-colors opacity-50 hover:opacity-100">
                    🧪 Testar Layout (Modo Mock)
                </button>
            </div>
        </div>
    </div>
</div>

<div id="global-loading-phrase" class="fixed top-10 left-1/2 -translate-x-1/2 z-[60] opacity-0 transition-opacity duration-500 pointer-events-none hidden">
    <p class="text-white text-[9px] font-bold uppercase tracking-widest text-center whitespace-nowrap drop-shadow-lg bg-[#0f1115]/50 px-4 py-1.5 rounded-full border border-white/10" id="phrase-text">Invocando o Oráculo...</p>
</div>

<div id="app-view" class="fixed inset-0 w-full h-full z-30 opacity-0 transition-opacity duration-700 hidden">
    
    <div id="carousel-wrapper" class="flex w-[300vw] h-full transition-transform duration-500 ease-in-out pointer-events-auto">
        
        <div class="w-[100vw] h-full overflow-y-auto pb-32 pt-28 px-4 sm:px-8 flex flex-col items-center">
            <div class="max-w-3xl w-full space-y-6">
                <!-- Perfil Card Ref (Moldura Retangular de Poster) -->
                <div class="fluent-glass relative overflow-hidden shadow-xl p-5 md:p-8 flex flex-col md:flex-row items-center md:items-start border-t-[#00e054]/50 shadow-[0_10px_40px_rgba(0,224,84,0.1)]">
                    
                    <div class="flex flex-col items-center shrink-0 mx-auto md:mx-0">
                        <p class="text-[#8c9bab] text-[8px] font-bold uppercase tracking-widest mb-2">Sua Vibe</p>
                        <div class="w-28 h-40 rounded-xl border-2 border-[#00e054] bg-[#0f1115] relative overflow-hidden shadow-[0_0_20px_rgba(0,224,84,0.3)] flex items-center justify-center">
                            <div id="profile-pulse-loader" class="w-full h-full bg-[#1c2228] animate-pulse absolute inset-0"></div>
                            <img id="profile-img-element" src="" loading="lazy" class="w-full h-full object-cover hidden transition-opacity duration-500 relative z-10">
                        </div>
                        <h4 id="char-name" class="text-white font-black text-[12px] uppercase tracking-tighter mt-3 drop-shadow-md text-center max-w-[140px] truncate">...</h4>
                        <p class="text-[#00e054] text-[9px] font-bold uppercase tracking-widest mt-0.5 text-center">DE <span id="char-movie" class="text-white">...</span></p>
                    </div>
                    
                    <div class="flex-1 space-y-3 min-w-0 mt-6 md:mt-0 md:ml-8 flex flex-col justify-center">
                        <h3 id="roast-title" class="text-2xl md:text-3xl font-black text-white tracking-tighter leading-tight text-center md:text-left">
                            Analisando o gosto... 
                            <svg class="animate-spin w-5 h-5 text-[#00e054] inline-block ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                        </h3>
                        <p id="roast-desc" class="text-gray-300 text-[12px] md:text-[13px] leading-loose font-light text-center md:text-left">Processando avaliações...</p>
                    </div>
                </div>

                <div class="grid grid-cols-2 gap-4">
                    <div class="fluent-glass p-6 text-center border-t-[#00e054]/30">
                        <span id="stat-total" class="space-font text-3xl font-black text-white block mb-1">0</span>
                        <p class="text-[#00e054] text-[9px] font-black uppercase tracking-widest">Avaliados</p>
                    </div>
                    <div class="fluent-glass p-6 text-center border-t-[#00e054]/30">
                        <span id="stat-avg" class="space-font text-3xl font-black text-white block mb-1">0.00</span>
                        <p class="text-[#00e054] text-[9px] font-black uppercase tracking-widest">Sua Média</p>
                    </div>
                </div>
            </div>
        </div>

        <div class="w-[100vw] h-full overflow-y-auto pb-32 pt-28 px-4 sm:px-8">
            <div class="max-w-5xl mx-auto">
                <div class="text-center mb-8">
                    <h2 class="text-3xl font-black text-white uppercase tracking-tighter">O Oráculo</h2>
                    <p class="text-[#40bcf4] text-[10px] font-bold tracking-widest uppercase">Escondidos no catálogo</p>
                </div>

                <div id="oracle-loading" class="flex flex-col items-center justify-center mt-20">
                    <div class="w-14 h-14 border-2 border-[#40bcf4]/20 border-t-[#40bcf4] rounded-full animate-spin"></div>
                    <p class="text-[#40bcf4] text-[10px] uppercase tracking-widest font-bold mt-6 animate-pulse">Escavando lado B...</p>
                </div>
                
                <div id="oracle-grid" class="hidden grid grid-cols-2 lg:grid-cols-4 gap-4 md:gap-6"></div>
                
                <div id="oracle-actions" class="hidden mt-10 flex-col sm:flex-row justify-center items-center gap-4">
                    <button onclick="abrirTutorial()" id="btn-export-desktop" class="fluent-glass px-6 py-4 text-[#40bcf4] text-[10px] md:text-[11px] font-black uppercase tracking-widest hover:bg-[#40bcf4]/10 transition-all border border-[#40bcf4]/30 w-full sm:w-auto shadow-lg">
                        EXPORTAR SELECIONADOS
                    </button>
                    <button id="btn-descobrir-mais" onclick="carregarMaisSugestoes()" class="fluent-glass px-6 py-4 text-white text-[10px] md:text-[11px] font-black uppercase tracking-widest hover:bg-white/10 transition-all w-full sm:w-auto shadow-lg flex items-center justify-center gap-2">
                        <svg id="load-more-spinner" class="w-4 h-4 animate-spin hidden" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                        Descobrir Mais
                    </button>
                </div>
            </div>
        </div>

        <div class="w-[100vw] h-full overflow-y-auto pb-32 pt-28 px-4 sm:px-8">
            <div class="max-w-5xl mx-auto h-full flex flex-col items-center">
                
                <div class="text-center mb-8 shrink-0">
                    <h2 class="text-3xl font-black text-white uppercase tracking-tighter">O Catálogo</h2>
                    <p class="text-[#ff8000] text-[10px] font-bold tracking-widest uppercase">Onde assistir sua Watchlist</p>
                </div>

                <div id="watchlist-loading" class="flex flex-col items-center justify-center mt-10">
                    <div class="w-20 h-20 rounded-full border-2 border-transparent border-t-[#ff8000] border-l-[#ff8000] animate-spin mb-8"></div>
                    <span id="load-percent" class="space-font text-6xl font-black text-white tracking-tighter mb-4 drop-shadow-lg">0%</span>
                </div>

                <div id="watchlist-content" class="hidden w-full space-y-6">
                    <div class="fluent-glass p-2 shrink-0 relative flex items-center z-[9999]">
                        <svg class="w-5 h-5 text-[#8c9bab] ml-3 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                        <input type="text" id="search-input" oninput="handleSearch()" placeholder="Procurar filme..." class="w-full bg-transparent border-none text-white px-4 py-2 focus:outline-none text-sm">
                        
                        <div class="relative shrink-0 z-[10000]">
                            <button onclick="toggleFilterDropdown(event)" class="text-[#ff8000] hover:text-white p-2 rounded transition-colors mr-1 bg-[#1c2228]/50 border border-[#ff8000]/30 hover:border-[#ff8000]/80">
                                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"></path></svg>
                            </button>

                            <div id="filter-dropdown" class="hidden absolute right-0 top-[120%] w-72 fluent-glass p-3 flex flex-col gap-1 max-h-80 overflow-y-auto no-scrollbar shadow-2xl border border-[#ff8000]/50" onclick="event.stopPropagation()">
                            </div>
                        </div>
                    </div>
                    
                    <ul id="results" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 relative z-10"></ul>
                </div>
            </div>
        </div>
    </div>

    <div class="absolute bottom-8 left-1/2 -translate-x-1/2 z-50 flex items-center justify-center gap-4 pointer-events-auto">
        <div class="bottom-nav-dot dot-green active" onclick="slideTo(0)" title="Perfil"></div>
        <div class="bottom-nav-dot dot-blue" id="tab-oracle" onclick="slideTo(1)" title="Oráculo"></div>
        <div class="bottom-nav-dot dot-orange" id="tab-watch" onclick="slideTo(2)" title="Watchlist"></div>
    </div>
</div>

<div id="tutorial-modal" class="fixed inset-0 bg-[#0f1115]/90 z-[10000] hidden items-center justify-center p-4 opacity-0 transition-opacity duration-300 pointer-events-auto">
    <div class="fluent-glass p-8 max-w-lg w-full relative flex flex-col border border-[#40bcf4]/30 shadow-2xl">
        <button onclick="fecharTutorial()" class="absolute top-4 right-5 text-[#8c9bab] hover:text-white text-3xl font-light">&times;</button>
        
        <div class="text-center mb-8">
            <h3 class="text-2xl font-black text-white uppercase tracking-tighter">Exportar para o Letterboxd</h3>
            <p class="text-[#8c9bab] text-sm mt-2">Adicione as obras inéditas à sua Watchlist oficial.</p>
        </div>

        <div class="space-y-4 mb-8">
            <div class="bg-[#14181c]/50 p-5 rounded-xl border border-white/5">
                <h5 class="text-white font-bold text-xs uppercase tracking-widest mb-3 flex items-center gap-2">
                    <span class="text-[#40bcf4]">1.</span> Baixe o Arquivo
                </h5>
                <button onclick="baixarWatchlistCompleta()" class="w-full bg-[#40bcf4] text-[#0f1115] font-black py-4 rounded-xl uppercase tracking-widest transition-all hover:bg-[#2ba8e0] text-xs shadow-lg">
                    Baixar .CSV
                </button>
            </div>

            <div class="bg-[#14181c]/50 p-5 rounded-xl border border-white/5 space-y-2">
                <h5 class="text-white font-bold text-xs uppercase tracking-widest flex items-center gap-2">
                    <span class="text-[#40bcf4]">2.</span> Importar no PC
                </h5>
                <p class="text-xs text-gray-300 leading-relaxed">Vá na sua <strong class="text-white">Watchlist</strong> no site do Letterboxd e clique em <strong class="text-white">Import films to watchlist</strong> (na barra lateral direita).</p>
            </div>
        </div>
    </div>
</div>

<script>
    let sessionId = localStorage.getItem('oraculo_session_id') || crypto.randomUUID();
    localStorage.setItem('oraculo_session_id', sessionId);
    
    let statsData = {};
    let rawDatabase = {};
    let oraculoBuffer = []; 
    let filmesSelecionados = new Set();
    let selectedPlatforms = new Set(); 
    let bgInterval;
    let fraseTimerInterval;
    let isCarouselBlocked = false;

    const frasesAleatorias = [
        "O Oráculo está assistindo a versão do diretor...",
        "Hackeando o banco de dados do Quentin Tarantino...",
        "O Neo demorou meses pra desviar daquelas balas, espere 5 segundos.",
        "Descobrindo filmes que nem o seu professor de cinema viu...",
        "Aguarde, o Letterboxd deitou o servidor.",
        "Passando um café com o David Lynch...",
        "Buscando as maiores pedradas cinematográficas..."
    ];

    const cinephileReleases = [
        { Name: "Project Hail Mary", Year: 2026 },
        { Name: "Marty Supreme", Year: 2026 },
        { Name: "Sinners", Year: 2025 },
        { Name: "The Drama", Year: 2026 },
        { Name: "Sentimental Value", Year: 2025 },
        { Name: "Hamnet", Year: 2025 },
        { Name: "O Agente Secreto", Year: 2025 }
    ];

    let currentBgList = [];
    let currentBgIdx = 0;

    function startInitialSlideshow() {
        const heroImg = document.getElementById('hero-backdrop-img');
        const slideInfo = document.getElementById('slideshow-info');
        if (!heroImg) return;

        const slideRating = document.getElementById('slide-rating');
        if(slideRating) slideRating.classList.add('hidden');

        const fetchPromises = cinephileReleases.map(async (film) => {
            try {
                let res = await fetch(`/api/tmdb/search?query=${encodeURIComponent(film.Name)}&year=${film.Year}`);
                let d = await res.json();
                if(d.results && d.results.length > 0 && d.results[0].backdrop_path) {
                    return {
                        Name: d.results[0].title, 
                        Year: film.Year,
                        backdrop: `https://image.tmdb.org/t/p/original${d.results[0].backdrop_path}`
                    };
                }
            } catch(e) {}
            return null;
        });

        Promise.all(fetchPromises).then(results => {
            currentBgList = results.filter(r => r !== null);
            if(currentBgList.length === 0) return;

            const startMovie = currentBgList[0];
            heroImg.src = startMovie.backdrop;
            if(document.getElementById('slide-title')) document.getElementById('slide-title').innerText = startMovie.Name;
            if(document.getElementById('slide-year')) document.getElementById('slide-year').innerText = startMovie.Year;
            
            heroImg.onload = () => {
                heroImg.style.opacity = '0.6'; 
                if(slideInfo) slideInfo.style.opacity = '1';
            };

            if(currentBgList.length > 1) {
                bgInterval = setInterval(() => {
                    currentBgIdx = (currentBgIdx + 1) % currentBgList.length;
                    const nextMovie = currentBgList[currentBgIdx];
                    const tempImg = new Image();
                    tempImg.onload = () => {
                        heroImg.style.opacity = '0';
                        if(slideInfo) slideInfo.style.opacity = '0';
                        setTimeout(() => {
                            heroImg.src = nextMovie.backdrop;
                            if(document.getElementById('slide-title')) document.getElementById('slide-title').innerText = nextMovie.Name;
                            if(document.getElementById('slide-year')) document.getElementById('slide-year').innerText = nextMovie.Year;
                            heroImg.style.opacity = '0.6'; 
                            if(slideInfo) slideInfo.style.opacity = '1';
                        }, 500);
                    };
                    tempImg.src = nextMovie.backdrop;
                }, 6000);
            }
        });
    }
    
    document.addEventListener('DOMContentLoaded', startInitialSlideshow);

    function iniciarCicloDeFrases() {
        const t = document.getElementById('phrase-text');
        const container = document.getElementById('global-loading-phrase');
        if(!t || !container) return;
        
        container.classList.remove('hidden');
        setTimeout(() => container.classList.remove('opacity-0'), 100);
        
        t.innerText = frasesAleatorias[Math.floor(Math.random() * frasesAleatorias.length)];
        
        if(fraseTimerInterval) clearInterval(fraseTimerInterval);
        fraseTimerInterval = setInterval(() => {
            t.style.opacity = '0';
            setTimeout(() => {
                t.innerText = frasesAleatorias[Math.floor(Math.random() * frasesAleatorias.length)];
                t.style.opacity = '1';
            }, 500);
        }, 5000);
    }

    function pararCicloDeFrases() {
        if(fraseTimerInterval) clearInterval(fraseTimerInterval);
        const container = document.getElementById('global-loading-phrase');
        if(container) {
            container.classList.add('opacity-0');
            setTimeout(() => container.classList.add('hidden'), 500);
        }
    }

    function mostrarErro(mensagem) {
        const toast = document.getElementById('custom-toast');
        const msgEl = document.getElementById('custom-toast-msg');
        msgEl.innerText = mensagem;
        toast.classList.remove('opacity-0', 'pointer-events-none', '-translate-y-10');
        setTimeout(() => {
            toast.classList.add('opacity-0', 'pointer-events-none', '-translate-y-10');
        }, 4000);
    }

    let currentSlide = 0;
    const totalSlides = 3;
    function slideTo(index) {
        if(isCarouselBlocked) return;
        const wrapper = document.getElementById('carousel-wrapper');
        const tabs = document.querySelectorAll('.bottom-nav-dot');
        if (!wrapper || tabs.length === 0) return;
        currentSlide = index;
        wrapper.style.transform = `translateX(-${index * 100}vw)`;
        tabs.forEach((t, i) => { t.classList.toggle('active', i === index); });
    }

    let startX = 0; let endX = 0;
    const wrapper = document.getElementById('carousel-wrapper');
    if (wrapper) {
        wrapper.addEventListener('touchstart', e => { startX = e.touches[0].clientX; }, {passive: true});
        wrapper.addEventListener('touchend', e => {
            endX = e.changedTouches[0].clientX;
            if(startX - endX > 50 && currentSlide < totalSlides - 1) slideTo(currentSlide + 1); 
            if(endX - startX > 50 && currentSlide > 0) slideTo(currentSlide - 1); 
        });
    }

    function fileSelected() {
        const file = document.getElementById('csv-file')?.files[0];
        if(file) {
            document.getElementById('file-name-display').innerText = file.name;
            document.getElementById('dropzone-label').classList.add('hidden');
            document.getElementById('action-area').classList.remove('hidden');
            document.getElementById('action-area').classList.add('flex');
        }
    }

    function resetUpload() {
        if(document.getElementById('csv-file')) document.getElementById('csv-file').value = '';
        document.getElementById('dropzone-label').classList.remove('hidden');
        document.getElementById('action-area').classList.add('hidden');
        document.getElementById('action-area').classList.remove('flex');
    }

    async function handleFileUpload() {
        const file = document.getElementById('csv-file')?.files[0];
        if(!file) return;

        const btn = document.getElementById('btn-iniciar-real');
        btn.innerHTML = `<svg class="animate-spin w-5 h-5 text-[#0f1115]" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Lendo...`;
        btn.disabled = true;

        const fd = new FormData();
        fd.append("file", file);
        fd.append("session_id", sessionId);

        try {
            const res = await fetch('/upload_profile', { method: 'POST', body: fd });
            if (!res.ok) throw new Error("Upload falhou");
            statsData = (await res.json()).stats;
            iniciarAppReal();
            iniciarFluxoWatchlist(); 
        } catch(e) {
            mostrarErro("Erro ao ler o ZIP. Tente de novo.");
            btn.innerHTML = `<span id="btn-text-real">Iniciar Análise</span>`;
            btn.disabled = false;
        }
    }

    async function loadUserBackgrounds() {
        if(!statsData || !statsData.favoritos || statsData.favoritos.length === 0) return;
        
        clearInterval(bgInterval); 
        const favs = statsData.favoritos.slice(0, 15);
        
        const fetchPromises = favs.map(async (f) => {
            try {
                let res = await fetch(`/api/tmdb/search?query=${encodeURIComponent(f.Name)}`);
                let d = await res.json();
                if(d.results && d.results.length > 0 && d.results[0].backdrop_path) {
                    return {
                        Name: f.Name,
                        Year: f.Year,
                        Rating: f.Rating,
                        backdrop: `https://image.tmdb.org/t/p/original${d.results[0].backdrop_path}`
                    };
                }
            } catch(e) {}
            return null;
        });

        const results = await Promise.all(fetchPromises);
        let newBgList = results.filter(r => r !== null);
        
        if(newBgList.length > 0) {
            let top4 = newBgList.slice(0, 4);
            let rest = newBgList.slice(4).sort(() => Math.random() - 0.5);
            currentBgList = [...top4, ...rest];
            currentBgIdx = 0;
            
            const heroImg = document.getElementById('hero-backdrop-img');
            const slideInfo = document.getElementById('slideshow-info');
            const slideRating = document.getElementById('slide-rating');

            const startMovie = currentBgList[0];
            heroImg.style.opacity = '0';
            
            setTimeout(() => {
                heroImg.src = startMovie.backdrop;
                document.getElementById('slide-title').innerText = startMovie.Name;
                document.getElementById('slide-year').innerText = startMovie.Year || '';
                
                if(startMovie.Rating) {
                    let stars = '';
                    let r = parseFloat(startMovie.Rating);
                    for(let i=0; i<Math.floor(r); i++) stars += '★';
                    if(r % 1 !== 0) stars += '½';
                    slideRating.innerText = stars;
                    slideRating.classList.remove('hidden');
                } else {
                    slideRating.classList.add('hidden');
                }

                heroImg.onload = () => {
                    heroImg.style.opacity = '0.7'; 
                    if(slideInfo) slideInfo.style.opacity = '1';
                }
            }, 300);

            bgInterval = setInterval(() => {
                currentBgIdx = (currentBgIdx + 1) % currentBgList.length;
                const nextMovie = currentBgList[currentBgIdx];
                const tempImg = new Image();
                tempImg.onload = () => {
                    heroImg.style.opacity = '0';
                    if(slideInfo) slideInfo.style.opacity = '0';
                    setTimeout(() => {
                        heroImg.src = nextMovie.backdrop;
                        document.getElementById('slide-title').innerText = nextMovie.Name;
                        document.getElementById('slide-year').innerText = nextMovie.Year || '';
                        
                        if(nextMovie.Rating) {
                            let stars = '';
                            let r = parseFloat(nextMovie.Rating);
                            for(let i=0; i<Math.floor(r); i++) stars += '★';
                            if(r % 1 !== 0) stars += '½';
                            slideRating.innerText = stars;
                            slideRating.classList.remove('hidden');
                        } else {
                            slideRating.classList.add('hidden');
                        }

                        heroImg.style.opacity = '0.7'; 
                        if(slideInfo) slideInfo.style.opacity = '1';
                    }, 500);
                };
                tempImg.src = nextMovie.backdrop;
            }, 6000);
        }
    }

    function criarPosterTipografico(title) {
        return `data:image/svg+xml;charset=UTF-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='400' height='600' viewBox='0 0 400 600'%3E%3Crect width='100%25' height='100%25' fill='%23111417'/%3E%3Ctext x='50%25' y='50%25' fill='%238c9bab' font-family='sans-serif' font-size='24' font-weight='bold' text-anchor='middle' dominant-baseline='middle' opacity='0.5'%3E${encodeURIComponent(title)}%3C/text%3E%3C/svg%3E`;
    }

    function iniciarAppReal() {
        document.getElementById('main-content').style.transform = 'translateY(-100vh)';
        
        setTimeout(() => {
            document.getElementById('main-content').classList.add('hidden');
            const appView = document.getElementById('app-view');
            appView.classList.remove('hidden');
            void appView.offsetWidth;
            appView.classList.remove('opacity-0');
            
            document.getElementById('stat-total').innerText = statsData.total_avaliados || 0;
            document.getElementById('stat-avg').innerText = (statsData.media_notas || 0).toFixed(2);

            loadUserBackgrounds();
            iniciarCicloDeFrases();

            gerarPerfilIA();
            setTimeout(() => { carregarOraculoInicial(); }, 3000); 
            
        }, 700);
    }

    async function gerarPerfilIA() {
        const tt = document.getElementById('roast-title');
        const td = document.getElementById('roast-desc');
        const ti = document.getElementById('profile-img-element');
        const pl = document.getElementById('profile-pulse-loader');

        try {
            const res = await fetch('/gerar_perfil', {
                method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({stats: statsData})
            });
            const data = await res.json();
            
            if(!data.erro && data.titulo) {
                if(tt) tt.innerHTML = data.titulo; 
                if(td) td.innerHTML = data.descricao.replace(/\n/g, '<br><br>'); 
                
                const charName = document.getElementById('char-name');
                const charMovie = document.getElementById('char-movie');
                if(charName) charName.innerText = data.personagem_referencia;
                if(charMovie) charMovie.innerText = data.filme_referencia;
                
                // Pôster direto na velocidade da luz (sem passar pelo elenco)
                fetch(`/api/tmdb/search?query=${encodeURIComponent(data.filme_referencia)}`)
                .then(r=>r.json())
                .then(d=>{
                    if(d.results && d.results.length > 0 && d.results[0].poster_path){ 
                        ti.src=`https://image.tmdb.org/t/p/w500${d.results[0].poster_path}`; 
                        ti.onload = () => {
                            ti.classList.remove('hidden'); 
                            pl.classList.add('hidden'); 
                        };
                    } else {
                        ti.src = criarPosterTipografico(data.filme_referencia);
                        ti.classList.remove('hidden'); 
                        pl.classList.add('hidden');
                    }
                }).catch(e => {
                    ti.src = criarPosterTipografico(data.filme_referencia);
                    ti.classList.remove('hidden'); 
                    pl.classList.add('hidden');
                });

            } else {
                throw new Error("Limites");
            }
        } catch(e) {
            if(tt) tt.innerHTML = "O Explorador Silencioso 🧘‍♂️";
            if(td) td.innerHTML = "Opa, desculpa pae! A Inteligência Artificial fritou os circuitos com tanta informação.<br><br>Mas ó, deslize pra aba do lado e aproveite pra ver onde assistir sua Watchlist ali na última aba! 🍿";
            pl.classList.add('hidden');
        }
    }

    async function carregarOraculoInicial() {
        try {
            const res = await fetch(`/oraculo?session_id=${sessionId}`, {
                method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ favorites: statsData.profile_favorites || [], exclude: [] })
            });
            const data = await res.json();
            
            document.getElementById('oracle-loading').classList.add('hidden');
            
            if(data.erro === "RATE_LIMIT" || data.erro === "Falha") {
                document.getElementById('oracle-grid').innerHTML = `
                    <div class="col-span-full text-center p-8 fluent-glass border border-[#40bcf4]/30 rounded-xl shadow-lg mt-4 w-full">
                        <div class="w-12 h-12 bg-[#40bcf4]/10 rounded-full flex items-center justify-center mx-auto mb-4 border border-[#40bcf4]/30">
                            <span class="text-xl">🛠️</span>
                        </div>
                        <h4 class="text-white font-black text-sm uppercase tracking-widest mb-3">Servidores Sobrecarregados</h4>
                        <p class="text-[#8c9bab] text-xs leading-relaxed">
                            Opa, desculpa pae! A IA gaguejou com o limite de acesso ou o JSON quebrou. 💀<br><br>
                            Mas não perde a viagem: <strong class="text-[#40bcf4]">deslize a tela pro lado e aproveite para ver onde assistir a sua Watchlist!</strong> 🍿
                        </p>
                    </div>
                `;
                document.getElementById('oracle-grid').classList.remove('hidden', 'grid-cols-2', 'lg:grid-cols-4');
                document.getElementById('oracle-grid').classList.add('flex', 'w-full');
                return;
            }

            document.getElementById('oracle-grid').classList.remove('hidden');
            document.getElementById('oracle-actions').classList.remove('hidden');
            document.getElementById('oracle-actions').classList.add('flex');

            if(data.terror_mode) {
                const trophy = document.getElementById('ps-trophy');
                if (trophy) {
                    trophy.classList.add('show');
                    setTimeout(() => trophy.classList.remove('show'), 6000); 
                }
                document.getElementById('btn-descobrir-mais').classList.add('hidden');
            }

            if(data.recomendacoes && data.recomendacoes.length > 0) {
                oraculoBuffer = data.recomendacoes; 
                let batch = oraculoBuffer.splice(0, Math.min(4, oraculoBuffer.length)); 
                renderizarOraculoCards(batch, 0);
            }
        } catch(e) {}
    }

    async function carregarMaisSugestoes() {
        const btnSpinner = document.getElementById('load-more-spinner');
        const btnText = document.getElementById('btn-descobrir-mais');

        if(oraculoBuffer.length >= 4) {
            let batch = oraculoBuffer.splice(0, 4);
            const startIdx = document.querySelectorAll('.movie-card').length;
            renderizarOraculoCards(batch, startIdx);
            return;
        }

        btnSpinner.classList.remove('hidden');
        btnText.disabled = true;
        
        try {
            const excl = Array.from(document.querySelectorAll('.movie-card h5')).map(el => el.innerText);
            const res = await fetch(`/oraculo?session_id=${sessionId}`, { 
                method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ favorites: statsData.profile_favorites || [], exclude: excl }) 
            });
            const data = await res.json();
            
            if(data.erro === "RATE_LIMIT" || data.erro === "Falha") {
                mostrarErro("O Oráculo falhou ou atingiu o limite. Tente de novo em instantes!");
            } else if(data.recomendacoes && data.recomendacoes.length > 0) {
                data.recomendacoes.forEach(novo_rec => {
                    const tituloLimpo = novo_rec.rec.toLowerCase().replace(/[^a-z0-9]/g, '');
                    let jaExiste = false;
                    document.querySelectorAll('.movie-card h5').forEach(el => {
                        if (el.innerText.toLowerCase().replace(/[^a-z0-9]/g, '') === tituloLimpo) jaExiste = true;
                    });
                    if (!jaExiste) oraculoBuffer.push(novo_rec);
                });

                let batch = oraculoBuffer.splice(0, Math.min(4, oraculoBuffer.length));
                renderizarOraculoCards(batch, document.querySelectorAll('.movie-card').length);
            } else if (data.terror_mode) {
                if (oraculoBuffer.length > 0) {
                    let batch = oraculoBuffer.splice(0, oraculoBuffer.length);
                    renderizarOraculoCards(batch, document.querySelectorAll('.movie-card').length);
                }
                const trophy = document.getElementById('ps-trophy');
                if (trophy) {
                    trophy.classList.add('show');
                    setTimeout(() => trophy.classList.remove('show'), 6000); 
                }
                btnText.classList.add('hidden'); 
            }
        } catch(e) {}
        
        btnSpinner.classList.add('hidden');
        btnText.disabled = false;
    }

    async function buscarPosterInteligente(title, year, cardId) {
        let imgUrl = null;
        try {
            let res = await fetch(`/api/tmdb/search?query=${encodeURIComponent(title)}&year=${year}`);
            let d = await res.json();
            
            if(d.results && d.results.length > 0 && d.results[0].poster_path) {
                imgUrl = `https://image.tmdb.org/t/p/w500${d.results[0].poster_path}`;
            } else {
                let res2 = await fetch(`/api/tmdb/search?query=${encodeURIComponent(title)}`);
                let d2 = await res2.json();
                if(d2.results && d2.results.length > 0 && d2.results[0].poster_path) {
                    imgUrl = `https://image.tmdb.org/t/p/w500${d2.results[0].poster_path}`;
                }
            }
        } catch(e) {}

        const card = document.getElementById(cardId);
        if(!card) return;

        const imgEl = card.querySelector('img.fav-poster');
        if(imgUrl) {
            imgEl.src = imgUrl;
            imgEl.onload = () => imgEl.style.opacity = '1';
        } else {
            imgEl.src = criarPosterTipografico(title);
            imgEl.style.opacity = '1';
        }
    }

    function renderizarOraculoCards(recs, startIdx) {
        const g = document.getElementById('oracle-grid');
        recs.forEach((r,i) => {
            const idx = startIdx+i, id=`oracle-card-${idx}`;
            
            g.insertAdjacentHTML('beforeend', `
                <div id="${id}" class="fluent-glass movie-card group opacity-0 translate-y-4 transition-all duration-700 cursor-pointer border-transparent hover:scale-[1.02] hover:border-[#40bcf4] border-2 aspect-[2/3]" onclick="toggleSelecao(${idx}, '${r.rec.replace(/'/g, "\\'")}', ${r.ano})">
                    <div id="check-${idx}" class="absolute top-2 right-2 z-40 bg-[#40bcf4] text-[#14181c] rounded-full p-1 transition-all scale-0 shadow-lg"><svg class="w-3 h-3 sm:w-4 sm:h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path></svg></div>
                    <img class="fav-poster absolute inset-0 w-full h-full object-cover z-10" src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" alt="Poster">
                    
                    <div class="card-info z-20 pb-2 px-2 sm:pb-3 sm:px-3 text-center absolute bottom-0 left-0 w-full bg-gradient-to-t from-[#0f1115] via-[#0f1115]/80 to-transparent">
                        <span class="text-[#40bcf4] text-[7px] sm:text-[8px] font-black uppercase bg-[#14181c]/90 px-1 py-0.5 rounded inline-block truncate max-w-full mb-1 border border-[#40bcf4]/30">${r.base}</span>
                        <h5 class="text-white font-bold text-[10px] sm:text-xs line-clamp-2 leading-tight drop-shadow-md">${r.rec}</h5>
                    </div>

                    <div class="absolute inset-0 bg-[#14181c]/95 z-30 opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col p-3 sm:p-4 text-center justify-center items-center"> 
                        <svg class="w-6 h-6 sm:w-8 sm:h-8 mb-1.5 sm:mb-2 text-[#40bcf4] shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path></svg>
                        <div class="w-full flex-1 overflow-y-auto no-scrollbar flex flex-col justify-center items-center mb-1">
                            <p class="text-[9px] sm:text-[11px] text-gray-300 leading-snug sm:leading-relaxed line-clamp-6">"${r.desc}"</p>
                        </div>
                        <span class="text-[7px] sm:text-[9px] text-[#40bcf4] font-black uppercase tracking-widest mt-auto shrink-0">CLIQUE P/ SELECIONAR</span>
                    </div>
                </div>
            `);
            
            buscarPosterInteligente(r.rec, r.ano, id);
            setTimeout(()=>document.getElementById(id)?.classList.remove('opacity-0','translate-y-4'), 100+(i*150));
        });
    }

    function toggleSelecao(idx, nome, ano) {
        const card = document.getElementById(`oracle-card-${idx}`);
        const check = document.getElementById(`check-${idx}`);
        
        let found = false;
        filmesSelecionados.forEach(f => { if(f.nome === nome) { filmesSelecionados.delete(f); found = true; } });

        if(found) { 
            card.classList.remove('border-[#40bcf4]'); 
            card.classList.add('border-transparent');
            check.classList.add('scale-0'); 
        } else { 
            filmesSelecionados.add({nome: nome, ano: ano}); 
            card.classList.add('border-[#40bcf4]'); 
            card.classList.remove('border-transparent');
            check.classList.remove('scale-0'); 
        }
        
        const txt = filmesSelecionados.size > 0 ? `EXPORTAR SELECIONADOS (${filmesSelecionados.size})` : "EXPORTAR SELECIONADOS";
        document.getElementById('btn-export-desktop').innerText = txt;
    }

    function abrirTutorial() {
        if(filmesSelecionados.size === 0) { mostrarErro("Toque nos cartazes para selecionar os filmes!"); return; }
        const modal = document.getElementById('tutorial-modal');
        modal.classList.remove('hidden');
        modal.classList.add('flex');
        setTimeout(() => modal.classList.remove('opacity-0'), 50);
    }
    
    function fecharTutorial() {
        const modal = document.getElementById('tutorial-modal');
        modal.classList.add('opacity-0');
        setTimeout(() => { modal.classList.add('hidden'); modal.classList.remove('flex'); }, 300);
    }
    
    function baixarWatchlistCompleta() {
        let c = "Title,Year\n"; 
        filmesSelecionados.forEach(f => { c += `"${f.nome.replace(/"/g,'""')}",${f.ano}\n`; });
        const a = document.createElement('a'); 
        a.href = window.URL.createObjectURL(new Blob([c], {type:'text/csv'})); 
        a.download = "scannerboxd-recs.csv"; 
        a.click(); 
        fecharTutorial();
        mostrarErro("CSV Baixado! Importe no Letterboxd.");
    }

    async function iniciarFluxoWatchlist() {
        try {
            await fetch('/process_watchlist', {
                method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({session_id: sessionId})
            });

            const iv = setInterval(async () => {
                const res = await fetch(`/progress?session_id=${sessionId}`);
                const p = await res.json();
                
                if(p.total > 0) {
                    const pct = Math.floor((p.atual / p.total) * 100);
                    document.getElementById('load-percent').innerText = pct + '%';
                    
                    if(p.finalizado) {
                        clearInterval(iv);
                        pararCicloDeFrases();
                        document.getElementById('watchlist-loading').classList.add('hidden');
                        document.getElementById('watchlist-content').classList.remove('hidden');

                        const finalRes = await fetch(`/dados?session_id=${sessionId}`);
                        const finalData = await finalRes.json();
                        rawDatabase = finalData.watchlist;
                        gerarFiltrosEWatchlist(rawDatabase);
                    }
                }
            }, 1000); 
        } catch(e) {}
    }

    function toggleFilterDropdown(event) {
        if(event) event.stopPropagation();
        document.getElementById('filter-dropdown').classList.toggle('hidden');
    }

    document.addEventListener('click', function(event) {
        const dropdown = document.getElementById('filter-dropdown');
        if(!dropdown) return;
        const btn = dropdown.previousElementSibling;
        if (!dropdown.classList.contains('hidden') && !dropdown.contains(event.target) && !btn.contains(event.target)) {
            dropdown.classList.add('hidden');
        }
    });

    function aplicarFiltros(platStr) {
        if(platStr === 'ALL') {
            selectedPlatforms.clear();
            document.querySelectorAll('.plat-checkbox').forEach(cb => cb.checked = false);
        } else {
            if(selectedPlatforms.has(platStr)) selectedPlatforms.delete(platStr);
            else selectedPlatforms.add(platStr);
        }
        handleSearch(); 
    }

    function gerarFiltrosEWatchlist(db) {
        const counts = {};
        for(const [filme, streamings] of Object.entries(db)) {
            streamings.forEach(s => { if(s !== 'Não disponível') counts[s] = (counts[s] || 0) + 1; });
        }

        const drop = document.getElementById('filter-dropdown');
        
        let html = `<button onclick="aplicarFiltros('ALL')" class="w-full text-left px-3 py-2 text-xs font-bold text-white hover:bg-white/10 rounded transition border-b border-[#ff8000]/20 mb-2">Limpar Filtros</button>`;
        
        Object.entries(counts).sort((a,b)=>b[1]-a[1]).forEach(([n, count]) => {
            const isChecked = selectedPlatforms.has(n) ? 'checked' : '';
            html += `
                <label class="w-full flex items-center justify-between px-3 py-2 hover:bg-white/10 rounded transition cursor-pointer group">
                    <div class="flex items-center gap-2 overflow-hidden">
                        <input type="checkbox" class="plat-checkbox accent-[#ff8000] w-4 h-4 rounded border-gray-600" onchange="aplicarFiltros('${n}')" ${isChecked}>
                        <span class="text-xs font-bold text-white truncate group-hover:text-[#ff8000] transition-colors">${n}</span>
                    </div>
                    <span class="text-[10px] text-[#ff8000] font-black bg-[#ff8000]/10 px-1.5 py-0.5 rounded shrink-0">${count}</span>
                </label>
            `;
        });
        
        drop.innerHTML = html;
        handleSearch(); 
    }

    function handleSearch() {
        const q = document.getElementById('search-input').value.toLowerCase();
        const res = document.getElementById('results');
        
        let html = '';
        let matchCount = 0;

        for(const [filme, streamings] of Object.entries(rawDatabase)) {
            const match = filme.match(/(.*)\s\((\d{4})\)$/);
            const titulo = match ? match[1] : filme;
            const ano = match ? match[2] : "";

            if (selectedPlatforms.size > 0 && !streamings.some(s => selectedPlatforms.has(s))) continue;
            if (q && !titulo.toLowerCase().includes(q)) continue;
            if (selectedPlatforms.size === 0 && !q && streamings[0] === "Não disponível") continue;

            matchCount++;

            const plats = streamings.map(s => {
                const isActive = selectedPlatforms.has(s);
                const style = isActive ? 'bg-[#ff8000]/20 border-[#ff8000] text-[#ff8000]' : 'bg-[#1c2228] border-[#2c3440] text-[#8c9bab]';
                return `<span class="border text-[8px] px-2 py-1 rounded font-black uppercase whitespace-nowrap shadow-sm transition-colors ${style}">${s}</span>`;
            }).join(' ');

            html += `
                <li class="fluent-glass p-4 md:p-5 border-l-4 border-l-[#ff8000] flex flex-col justify-between gap-3 transition-all hover:scale-[1.02] hover:border-l-[#ffb366]">
                    <div>
                        <span class="text-white font-bold text-sm md:text-base block leading-tight truncate">${titulo}</span>
                        <span class="text-[#8c9bab] text-[10px] block mt-1">${ano}</span>
                    </div>
                    <div class="flex gap-1.5 flex-wrap mt-2">${plats}</div>
                </li>
            `;
        }

        if(matchCount === 0) {
            html = `<li class="col-span-full text-center p-8 text-[#8c9bab] text-xs uppercase tracking-widest font-bold">Nenhum filme encontrado nos filtros atuais.</li>`;
        }
        res.innerHTML = html;
    }
</script>
</body>
</html>
