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
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
DB_NAME = "oraculo.db"

# ==========================================
# GATILHO DE ANIVERSÁRIO DA LAURA
# (Mude para False amanhã para desativar!)
# ==========================================
IS_LAURA_BIRTHDAY_ACTIVE = True

# ==========================================
# CONFIGURAÇÃO DO BANCO DE DADOS SQLITE
# ==========================================
def get_db():
    conn = sqlite3.connect(DB_NAME, timeout=15)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
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

init_db()

# ==========================================
# FUNÇÕES DE ESTADO (BANCO DE DADOS)
# ==========================================
def set_progresso(session_id, atual, total, finalizado, filme_atual):
    with get_db() as conn:
        conn.execute('''INSERT OR REPLACE INTO progress (session_id, atual, total, finalizado, filme_atual)
                        VALUES (?, ?, ?, ?, ?)''', (session_id, atual, total, int(finalizado), filme_atual))

def get_progresso(session_id):
    with get_db() as conn:
        row = conn.execute('SELECT * FROM progress WHERE session_id = ?', (session_id,)).fetchone()
        if row:
            return {"atual": row['atual'], "total": row['total'], "finalizado": bool(row['finalizado']), "filme_atual": row['filme_atual']}
        return {"atual": 0, "total": 0, "finalizado": False, "filme_atual": "Aguardando..."}

def salvar_sessao(session_id, vistos, amados, odiados, watchlist):
    with get_db() as conn:
        conn.execute('''INSERT OR REPLACE INTO sessions (session_id, vistos, amados, odiados, watchlist)
                        VALUES (?, ?, ?, ?, ?)''', 
                        (session_id, json.dumps(vistos), json.dumps(amados), json.dumps(odiados), json.dumps(watchlist)))

def carregar_sessao(session_id):
    with get_db() as conn:
        row = conn.execute('SELECT * FROM sessions WHERE session_id = ?', (session_id,)).fetchone()
        if row:
            return {
                'vistos': json.loads(row['vistos']),
                'amados': json.loads(row['amados']),
                'odiados': json.loads(row['odiados']),
                'watchlist': json.loads(row['watchlist'])
            }
        return None

def get_cache_streamings(chave):
    with get_db() as conn:
        row = conn.execute('SELECT streamings FROM global_cache WHERE chave = ?', (chave,)).fetchone()
        if row:
            return json.loads(row['streamings'])
        return None

def set_cache_streamings(chave, streamings):
    with get_db() as conn:
        conn.execute('INSERT OR REPLACE INTO global_cache (chave, streamings) VALUES (?, ?)', (chave, json.dumps(streamings)))

def salvar_dados_finais(session_id, dados):
    with get_db() as conn:
        conn.execute('INSERT OR REPLACE INTO dados_finais (session_id, dados) VALUES (?, ?)', (session_id, json.dumps(dados)))

def get_dados_finais(session_id):
    with get_db() as conn:
        row = conn.execute('SELECT dados FROM dados_finais WHERE session_id = ?', (session_id,)).fetchone()
        if row:
            return json.loads(row['dados'])
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
    # Modo ilimitado ativado temporariamente para amigos
    return jsonify({"creditos": 999})

@app.route('/api/consumir_credito', methods=['POST'])
def consume_credito():
    # Modo ilimitado ativado temporariamente para amigos
    return jsonify({"sucesso": True, "creditos": 999})

@app.route('/api/adicionar_credito', methods=['POST'])
def add_credito():
    ip = get_ip()
    with get_db() as conn:
        row = conn.execute('SELECT creditos FROM credits WHERE ip = ?', (ip,)).fetchone()
        if row:
            conn.execute('UPDATE credits SET creditos = creditos + 1 WHERE ip = ?', (ip,))
        else:
            conn.execute('INSERT INTO credits (ip, creditos) VALUES (?, ?)', (ip, 1))
        conn.commit()
        novo_saldo = conn.execute('SELECT creditos FROM credits WHERE ip = ?', (ip,)).fetchone()['creditos']
    return jsonify({"sucesso": True, "creditos": novo_saldo})

@app.route('/api/tmdb/search', methods=['GET'])
def tmdb_search():
    q = request.args.get('query', '')
    y = request.args.get('year', '')
    if not TMDB_API_KEY: return jsonify({"erro": "Chave TMDB ausente"}), 500
    url = f'https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={quote(q)}&language=pt-BR'
    if y: url += f'&year={y}'
    try: return jsonify(requests.get(url, timeout=5).json())
    except Exception as e: return jsonify({"erro": str(e)}), 500

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
        stats_usuario = {
            "total_avaliados": 0, 
            "media_notas": 0, 
            "favoritos": [], 
            "username": "", 
            "bio": "", 
            "profile_favorites": [],
            "is_laura_birthday": False
        }
        vistos_temp = set()
        amados_temp = []
        odiados_temp = []
        watchlist_temp = []
        
        if file.filename.lower().endswith('.zip'):
            with zipfile.ZipFile(file, 'r') as z:
                if 'profile.csv' in z.namelist():
                    with z.open('profile.csv') as f_profile:
                        df_p = pd.read_csv(f_profile)
                        if not df_p.empty:
                            row = df_p.iloc[0]
                            stats_usuario["username"] = str(row.get("Username", ""))
                            bio_raw = str(row.get("Bio", ""))
                            stats_usuario["bio"] = re.sub(r'<[^>]+>', '', bio_raw) if bio_raw != 'nan' else ""
                            fav_links = str(row.get("Favorite Films", ""))
                            stats_usuario["profile_favorites"] = resolve_boxd_links(fav_links)
                            
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
                        
                        df_5_estrelas = df_r[df_r['Rating'] >= 4.5]
                        amados_temp = df_5_estrelas['Name'].fillna("").tolist()
                        odiados_temp = df_r[df_r['Rating'] <= 2.5]['Name'].fillna("").tolist()
                        
                        if len(df_5_estrelas) >= 20: favs = df_5_estrelas.sample(n=20)
                        elif len(df_5_estrelas) > 0:
                            faltam = 20 - len(df_5_estrelas)
                            df_resto = df_r[df_r['Rating'] < 4.5].sort_values(by='Rating', ascending=False).head(faltam)
                            favs = pd.concat([df_5_estrelas, df_resto])
                        else: favs = df_r.sort_values(by=['Rating'], ascending=False).head(20)
                            
                        stats_usuario["favoritos"] = favs[['Name', 'Year', 'Rating']].fillna("").to_dict('records')
                
                if 'watchlist.csv' in z.namelist():
                    with z.open('watchlist.csv') as f_watch: 
                        df_watch = pd.read_csv(f_watch)
                        vistos_temp.update(df_watch['Name'].fillna("").str.lower().tolist())
                        watchlist_temp = df_watch[['Name', 'Year']].fillna("").to_dict('records')

        salvar_sessao(session_id, list(vistos_temp), amados_temp, odiados_temp, watchlist_temp)
        set_progresso(session_id, 0, 0, False, "Aguardando...")
                        
        return jsonify({'stats': stats_usuario})
    except Exception as e: 
        return jsonify({'erro': str(e)}), 500

@app.route('/gerar_perfil', methods=['POST'])
def gerar_perfil():
    dados = request.json
    stats = dados.get('stats', {})
    
    if not GROQ_API_KEY: return jsonify({"erro": "Sem chave da Groq"}), 400

    favoritos_nomes = [f['Name'] for f in stats.get('favoritos', [])]
    is_laura = stats.get('is_laura_birthday', False)
    
    if is_laura:
        # PROMPT EXCLUSIVO DO ANIVERSÁRIO DA LAURA
        prompt = f"""Atue como um melhor amigo dando um presente mágico de aniversário. A usuária se chama Laura (username: lauraamora) e HOJE É O ANIVERSÁRIO DELA!
        
        DADOS DELA:
        - Bio: "{stats.get('bio', '')}"
        - Os 4 Filmes Favoritos: {', '.join(stats.get('profile_favorites', ['Nenhum']))}
        
        Sua missão é escrever uma mensagem de FELIZ ANIVERSÁRIO incrivelmente linda, poética e afetuosa. 
        Use os filmes favoritos dela como metáfora para elogiar a pessoa maravilhosa que ela é.
        Crie "DOIS PARÁGRAFOS" (separados por \\n\\n). 
        - Parágrafo 1: Deseje feliz aniversário, celebre o dia dela e cite como o gosto dela por esses filmes mostra uma alma gigante.
        - Parágrafo 2: Continue elogiando a sensibilidade dela e deixe claro que esse site é um presente especial só para ela hoje.
        
        REGRA: ZERO DEBOCHE, ZERO SARCASMO! Apenas carinho puro. Use emojis comemorativos (🎂, ✨, 💖, 🎈, 🎬, 🌟).
        
        REGRA DE GRAMÁTICA E COESÃO: Cheque rigorosamente a gramática e a legibilidade do texto. Não invente palavras.
        
        REGRA CRÍTICA 1: "personagem_referencia" DEVE SER a protagonista do filme favorito dela.
        REGRA CRÍTICA 2: "filme_referencia" DEVE SER O TÍTULO ORIGINAL EM INGLÊS.
        
        É OBRIGATÓRIO responder APENAS em JSON estruturado:
        {{
          "titulo": "✨ Feliz Aniversário, Laura! 🎂",
          "personagem_referencia": "A Protagonista (Você)",
          "filme_referencia": "Amelie",
          "descricao": "Texto gerado aqui..."
        }}"""
    else:
        # PROMPT NORMAL PARA OS OUTROS USUÁRIOS
        prompt = f"""Atue como um crítico de cinema gen-z cronicamente online.
        DADOS PESSOAIS DO USUÁRIO:
        - Username: {stats.get('username', 'Cinéfilo')}
        - Bio do perfil: "{stats.get('bio', 'Sem bio')}"
        - Os 4 Filmes Favoritos: {', '.join(stats.get('profile_favorites', ['Nenhum']))}
        
        ESTATÍSTICAS GERAIS:
        - Total de filmes vistos: {stats.get('total_avaliados', 0)}
        - Média de notas (de 0 a 5): {stats.get('media_notas', 0)}
        - Outros filmes que amou: {', '.join(favoritos_nomes[:10])}

        Crie um "Perfil Psicológico" na chave "descricao" com EXATAMENTE DOIS PARÁGRAFOS (separe-os usando \\n\\n):
        
        PARÁGRAFO 1 (O Deboche Cronicamente Online): Fale DIRETAMENTE com o usuário (use sempre a palavra "você"). Faça um "roast" sarcástico e letal. Aponte o contraste absurdo entre o que a pessoa escreveu na Bio ou os favoritos que escolheu para "parecer cult" versus as outras notas que ela tem.
        PARÁGRAFO 2 (A Análise Romântica e Sensível): Mude completamente o TOM DAS PALAVRAS. Sem usar ironia nas palavras, faça uma análise poética, madura e profunda. Continue falando diretamente com o usuário ("você"). Elogie a forma como o usuário usa o cinema como catarse, buscando beleza e significado. 
        
        REGRA DE GÊNERO: NUNCA assuma o gênero do usuário baseado no nome. Trate o usuário de forma neutra ou diretamente por "você". É ESTRITAMENTE PROIBIDO usar palavras como "rainha", "rei", "ela" ou "ele" para se referir ao usuário.
        
        REGRA DE GRAMÁTICA E COESÃO: Cheque rigorosamente a gramática, a coesão e a legibilidade do texto. Mantenha um português impecável. NUNCA invente palavras ou gírias que não existem.
        
        REGRA DE EMOJIS: Em AMBOS OS PARÁGRAFOS tempere o texto usando EXCLUSIVAMENTE ALGUNS destes emojis específicos: 🙄🤤😔😓😞😭😢🥺💀☠️👍🤌💅🫦💋🔥😻😿🥺😼🤓🙈. A graça é falar coisas lindíssimas no segundo parágrafo, mas continuar a pontuar com emojis de deboche (ex: "...sua busca genuína por beleza 😭💅").

        REGRA CRÍTICA 1: "personagem_referencia" DEVE SER um personagem fictício real.
        REGRA CRÍTICA 2: "filme_referencia" DEVE SER O TÍTULO ORIGINAL EM INGLÊS.

        É OBRIGATÓRIO responder APENAS em JSON estruturado:
        {{
          "titulo": "A Farsa do Cinema Cult 💅",
          "personagem_referencia": "Kendall Roy",
          "filme_referencia": "Drive",
          "descricao": "Texto gerado aqui..."
        }}"""

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7, 
        "response_format": {"type": "json_object"} 
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=20)
        if res.status_code == 200:
            return jsonify(json.loads(res.json()['choices'][0]['message']['content']))
        raise Exception("Falha na API da Groq")
    except Exception as e:
        if is_laura:
            return jsonify({
                "titulo": "✨ Feliz Aniversário, Laura! 🎂",
                "personagem_referencia": "A Protagonista da Própria Vida",
                "filme_referencia": "La La Land",
                "descricao": "Opa Laura! Hoje o dia é todo seu! ✨ Até o servidor ficou tão emocionado com a sua presença que decidiu pular a análise fria só para te desejar o melhor dia de todos. Que a sua vida continue sendo um roteiro lindo, cheio de amor e trilhas sonoras inesquecíveis. Aproveite o seu presente! 🎈💖"
            })
            
        return jsonify({
            "titulo": "O Erro 404 da Estética 🤓",
            "personagem_referencia": "HAL 9000",
            "filme_referencia": "2001: A Space Odyssey",
            "descricao": "A sua lista de filmes exala tanta contradição que o algoritmo simplesmente recusou-se a processar e pediu demissão 💀. É muito delírio achar que essa curadoria genérica faz sentido. Vai ler um livro 🙄.\n\nMas brincadeiras à parte, algo na sua conexão com o cinema quebrou nossos circuitos 😭💅. Continue sentindo tudo de forma inexplicável 🥺🤌."
        })

@app.route('/oraculo', methods=['GET', 'POST'])
def oraculo():
    session_id = request.args.get('session_id', 'default')
    sessao = carregar_sessao(session_id)
    
    if not sessao:
        return jsonify({"erro": "Dados da sessão não encontrados"}), 400
        
    try:
        amados = sessao.get('amados', [])
        odiados = sessao.get('odiados', [])
        vistos_globais = sessao.get('vistos', [])
        
        amados_amostra = random.sample(amados, min(8, len(amados))) if amados else ["Bons filmes"]
        odiados_amostra = random.sample(odiados, min(4, len(odiados))) if odiados else ["Filmes maus"]

        top_4_favorites = request.json.get('favorites', []) if request.is_json else []
        filmes_ja_recomendados = request.json.get('exclude', []) if request.is_json else []
        
        top_4_texto = f"- TOP 4 FAVORITOS ABSOLUTOS DO PERFIL: {', '.join(top_4_favorites)}" if top_4_favorites else ""
        texto_exclusao = f"REGRA CRÍTICA (IGNORAR ESTES): É PROIBIDO recomendar os seguintes filmes, pois você JÁ os recomendou nesta sessão: {', '.join(filmes_ja_recomendados)}" if filmes_ja_recomendados else ""

        if GROQ_API_KEY:
            temas_aleatorios = [
                "Favoritos do público e da crítica (nota 3.8+ no Letterboxd).",
                "Grandes filmes de estúdios aclamados como A24, Neon, ou clássicos modernos.",
                "Thrillers famosos, suspenses e filmes que prendem do início ao fim.",
                "Comédias, romances ou dramas muito bem avaliados e populares.",
                "Filmes com elencos estelares e diretores renomados que o usuário pode ter deixado passar.",
                "Obras que foram um sucesso cultural e pop nos últimos 20 anos."
            ]
            tema_escolhido = random.choice(temas_aleatorios)

            prompt = f"""Atue como um curador de cinema profissional, focado em entender a vibe exata do usuário. 
            
            DADOS DE GOSTO DO USUÁRIO:
            {top_4_texto}
            - Outros filmes que amou (nota máxima): {amados_amostra}
            - Filmes que odiou (nota baixa): {odiados_amostra}

            Recomende EXATAMENTE 15 filmes MUITO BONS (Nota média > 3.6) que o usuário provavelmente ainda não viu, MAS QUE COMBINEM COM O GOSTO DELE.
            
            DIRETRIZ DE CURADORIA MESTRE: Analise os TOP 4 FAVORITOS do usuário. Extraia a essência, os gêneros (ex: comédia, terror, romance, ficção) e a atmosfera deles e use isso como base principal. Cruze essa essência com: {tema_escolhido}
            
            REGRA CRÍTICA 1 - PERSONALIZAÇÃO EXTREMA: O perfil do usuário dita as regras. Não empurre filmes obscuros iranianos se ele gosta de comédia romântica ou ação. 
            
            REGRA CRÍTICA 2 - FILMES FAMOSOS LIBERADOS: VOCÊ DEVE recomendar filmes populares, aclamados e "famosinhos" do Letterboxd. Pode recomendar grandes sucessos de Hollywood, filmes cult muito conhecidos, sucessos recentes ou clássicos muito amados. Apenas EVITE mega-franquias óbvias (Marvel, DC, Star Wars, Harry Potter, Velozes e Furiosos).
            
            {texto_exclusao}

            REGRAS DE FORMATO (OBRIGATÓRIO):
            1. "rec_original": Título original do filme em INGLÊS.
            2. "rec": MESMO TÍTULO EM INGLÊS.
            3. "base": Uma definição de gênero curta (ex: "Thriller Psicológico", "Comédia Romântica"). (Máximo 4 palavras).
            4. "desc": Uma sinopse chamativa e bem escrita que venda o filme, PT-BR. (Aproximadamente 15 a 25 palavras).

            É OBRIGATÓRIO responder APENAS em JSON estruturado:
            {{
              "recomendacoes": [
                {{"rec_original": "Gone Girl", "rec": "Gone Girl", "ano": 2014, "base": "Suspense Psicológico Intenso", "desc": "Um homem vê sua vida desmoronar e se torna o principal suspeito quando sua esposa desaparece misteriosamente no dia do aniversário de casamento."}}
              ]
            }}"""
            
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.8, 
                "response_format": {"type": "json_object"} 
            }
            
            res = requests.post(url, headers=headers, json=payload, timeout=20)
            if res.status_code == 200:
                dados_json = json.loads(res.json()['choices'][0]['message']['content'])
                recs_ia = dados_json.get("recomendacoes", [])
                if len(recs_ia) > 0:
                    recs_ineditas = []
                    filmes_ja_recomendados_lower = [f.lower() for f in filmes_ja_recomendados]
                    for r in recs_ia:
                        n_orig = r.get('rec_original', '').lower()
                        n_pt = r.get('rec', '').lower()
                        n_rec = r.get('rec', '').lower()
                        
                        if n_orig not in vistos_globais and n_pt not in vistos_globais and n_rec not in filmes_ja_recomendados_lower:
                            recs_ineditas.append(r)
                    return jsonify({"recomendacoes": recs_ineditas})

        return jsonify({"recomendacoes": []})
    except Exception as e: return jsonify({"erro": "Falha", "recomendacoes": []})

def processar_em_segundo_plano(watchlist_data, session_id):
    dados_filmes = {}
    total = len(watchlist_data)
    atual = 0
    
    def fetch_movie(row):
        filme = row.get('Name', '')
        ano = row.get('Year', '')
        chave = f"{filme} ({ano})"
        
        cached_streamings = get_cache_streamings(chave)
        if cached_streamings: return chave, cached_streamings
        
        streamings = []
        try:
            search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={quote(filme)}&language=pt-BR"
            if ano and str(ano).isdigit(): search_url += f"&year={int(float(ano))}"
            
            res_search = requests.get(search_url, timeout=5).json()
            if res_search.get('results'):
                movie_id = res_search['results'][0]['id']
                prov_url = f"https://api.themoviedb.org/3/movie/{movie_id}/watch/providers?api_key={TMDB_API_KEY}"
                prov_res = requests.get(prov_url, timeout=5).json()
                br_data = prov_res.get('results', {}).get('BR', {})
                
                for cat in ['flatrate', 'free', 'ads']:
                    if cat in br_data:
                        for provider in br_data[cat]:
                            nome = provider.get('provider_name')
                            if nome and nome not in streamings:
                                streamings.append(nome)
        except Exception as e: pass
        
        if not streamings: streamings.append("Não disponível")
        set_cache_streamings(chave, streamings)
        return chave, streamings
        
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_movie, row): row for row in watchlist_data}
            for future in concurrent.futures.as_completed(futures):
                chave, streamings = future.result()
                dados_filmes[chave] = streamings
                atual += 1
                set_progresso(session_id, atual, total, False, chave)
        
        dados_finais = {"stats": {}, "watchlist": dados_filmes}
        salvar_dados_finais(session_id, dados_finais)
        set_progresso(session_id, total, total, True, "Finalizado!")
        
    except Exception as e:
        set_progresso(session_id, total, total, True, "Finalizado com erros.")

@app.route('/process_watchlist', methods=['POST'])
def process_watchlist():
    req_data = request.json or {}
    session_id = req_data.get('session_id', 'default')
    sessao = carregar_sessao(session_id)
    
    if not sessao or not sessao.get('watchlist'):
        return jsonify({'erro': 'A Watchlist não foi carregada ou está vazia.'}), 400

    watchlist_data = sessao.get('watchlist')
    set_progresso(session_id, 0, len(watchlist_data), False, "Ligando os motores...")
    threading.Thread(target=processar_em_segundo_plano, args=(watchlist_data, session_id)).start()
    return jsonify({'mensagem': 'Iniciado'})

def liberar_porta(porta):
    try:
        sistema = platform.system()
        if sistema == 'Windows':
            comando = f'netstat -ano | findstr :{porta}'
            resultado = subprocess.run(comando, shell=True, capture_output=True, text=True)
            for linha in resultado.stdout.splitlines():
                if 'LISTENING' in linha:
                    pid = linha.strip().split()[-1]
                    if pid != '0':
                        subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
        else:
            comando = f'lsof -t -i:{porta}'
            resultado = subprocess.run(comando, shell=True, capture_output=True, text=True)
            for pid in resultado.stdout.strip().split('\n'):
                if pid: os.system(f'kill -9 {pid}')
    except Exception as e: pass

if __name__ == '__main__':
    PORTA = 5000
    liberar_porta(PORTA)
    def abrir_navegador(): webbrowser.open(f'http://127.0.0.1:{PORTA}')
    threading.Timer(1.5, abrir_navegador).start()
    app.run(port=PORTA, debug=False, threaded=True)
