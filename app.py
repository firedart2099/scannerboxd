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
from flask import Flask, render_template, request, jsonify, Response
from urllib.parse import quote
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env para a memória
load_dotenv()

app = Flask(__name__)
ARQUIVO_DADOS = "filmes_salvos.json"
ARQUIVO_FRASES = "frases.txt" 
ARQUIVO_PERFIS = "perfis.json"
ARQUIVO_CREDITOS = "creditos.json"
ARQUIVO_SESSAO = "sessao.json" # Nova memória compartilhada para servidores em nuvem
ARQUIVO_PROGRESSO = "progresso.json" # Monitor de progresso compartilhado

# Vai buscar a chave da GROQ e da TMDB ao arquivo .env
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# === SISTEMA DE PROGRESSO COMPARTILHADO ===
def set_progresso(atual, total, finalizado, filme_atual):
    try:
        with open(ARQUIVO_PROGRESSO, 'w', encoding='utf-8') as f:
            json.dump({"atual": atual, "total": total, "finalizado": finalizado, "filme_atual": filme_atual}, f)
    except: pass

def get_progresso():
    try:
        with open(ARQUIVO_PROGRESSO, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"atual": 0, "total": 0, "finalizado": False, "filme_atual": "Aguardando..."}

def garantir_arquivos_externos():
    if not os.path.exists(ARQUIVO_FRASES):
        with open(ARQUIVO_FRASES, 'w', encoding='utf-8') as f:
            f.write("Cruzando suas notas com o watched.csv...\nVasculhando o submundo do cinema cult...\nEvitando os filmes que você já viu...")
    if not os.path.exists(ARQUIVO_PERFIS):
        with open(ARQUIVO_PERFIS, 'w', encoding='utf-8') as f:
            json.dump([], f)
    if not os.path.exists(ARQUIVO_CREDITOS):
        with open(ARQUIVO_CREDITOS, 'w', encoding='utf-8') as f:
            json.dump({}, f)
    if not os.path.exists(ARQUIVO_PROGRESSO):
        set_progresso(0, 0, False, "Aguardando...")

garantir_arquivos_externos()

# === SISTEMA DE SEGURANÇA E CRÉDITOS POR IP ===
def get_ip():
    if request.environ.get('HTTP_X_FORWARDED_FOR') is None:
        return request.environ['REMOTE_ADDR']
    else:
        return request.environ['HTTP_X_FORWARDED_FOR'].split(',')[0]

def ler_creditos():
    try:
        with open(ARQUIVO_CREDITOS, 'r', encoding='utf-8') as f:
            return json.load(f)
    except: return {}

def salvar_creditos(dados):
    with open(ARQUIVO_CREDITOS, 'w', encoding='utf-8') as f:
        json.dump(dados, f)

@app.route('/api/creditos', methods=['GET'])
def check_creditos():
    ip = get_ip()
    db = ler_creditos()
    if ip not in db:
        db[ip] = 1 # Dá 1 crédito grátis para IPs novos
        salvar_creditos(db)
    return jsonify({"creditos": db[ip]})

@app.route('/api/consumir_credito', methods=['POST'])
def consume_credito():
    ip = get_ip()
    db = ler_creditos()
    if ip in db and db[ip] > 0:
        db[ip] -= 1
        salvar_creditos(db)
        return jsonify({"sucesso": True, "creditos": db[ip]})
    return jsonify({"sucesso": False, "erro": "Sem créditos"}), 403

@app.route('/api/adicionar_credito', methods=['POST'])
def add_credito():
    ip = get_ip()
    db = ler_creditos()
    db[ip] = db.get(ip, 0) + 1
    salvar_creditos(db)
    return jsonify({"sucesso": True, "creditos": db[ip]})
# ===============================================

# === PROXY SEGURO PARA A TMDB ===
@app.route('/api/tmdb/search', methods=['GET'])
def tmdb_search():
    q = request.args.get('query', '')
    y = request.args.get('year', '')
    
    if not TMDB_API_KEY:
        return jsonify({"erro": "Chave TMDB ausente no servidor"}), 500
        
    url = f'https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={quote(q)}&language=pt-BR'
    if y:
        url += f'&year={y}'
        
    try:
        r = requests.get(url, timeout=5)
        return jsonify(r.json())
    except Exception as e:
        return jsonify({"erro": str(e)}), 500
# ===============================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dados')
def dados():
    if not os.path.exists(ARQUIVO_DADOS):
        return jsonify({})
    with open(ARQUIVO_DADOS, 'r', encoding='utf-8') as f:
        return jsonify(json.load(f))

@app.route('/frases')
def get_frases():
    try:
        with open(ARQUIVO_FRASES, 'r', encoding='utf-8') as f:
            return jsonify([linha.strip() for linha in f.readlines() if linha.strip()])
    except:
        return jsonify(["Analisando catálogos..."])

@app.route('/progress')
def route_get_progress():
    return jsonify(get_progresso())

@app.route('/upload_profile', methods=['POST'])
def upload_profile():
    if 'file' not in request.files: 
        return jsonify({'erro': 'Nenhum arquivo enviado'}), 400
    
    file = request.files['file']
    try:
        stats_usuario = {"total_avaliados": 0, "media_notas": 0, "favoritos": []}
        
        vistos_temp = set()
        amados_temp = []
        odiados_temp = []
        watchlist_temp = []
        
        if file.filename.lower().endswith('.zip'):
            with zipfile.ZipFile(file, 'r') as z:
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
                        
                        if len(df_5_estrelas) >= 20:
                            favs = df_5_estrelas.sample(n=20)
                        elif len(df_5_estrelas) > 0:
                            faltam = 20 - len(df_5_estrelas)
                            df_resto = df_r[df_r['Rating'] < 4.5].sort_values(by='Rating', ascending=False).head(faltam)
                            favs = pd.concat([df_5_estrelas, df_resto])
                        else:
                            favs = df_r.sort_values(by=['Rating'], ascending=False).head(20)
                            
                        stats_usuario["favoritos"] = favs[['Name', 'Year', 'Rating']].fillna("").to_dict('records')
                
                if 'watchlist.csv' in z.namelist():
                    with z.open('watchlist.csv') as f_watch: 
                        df_watch = pd.read_csv(f_watch)
                        vistos_temp.update(df_watch['Name'].fillna("").str.lower().tolist())
                        watchlist_temp = df_watch[['Name', 'Year']].fillna("").to_dict('records')

        # SALVA TUDO NUM ARQUIVO TEMPORÁRIO PARA OS OUTROS PROCESSOS LEREM (Resolve erro de multi-worker do Render)
        with open(ARQUIVO_SESSAO, 'w', encoding='utf-8') as f:
            json.dump({
                "vistos": list(vistos_temp),
                "amados": amados_temp,
                "odiados": odiados_temp,
                "watchlist": watchlist_temp
            }, f)
                        
        return jsonify({'stats': stats_usuario})
    except Exception as e: 
        return jsonify({'erro': str(e)}), 500

@app.route('/gerar_perfil', methods=['POST'])
def gerar_perfil():
    dados = request.json
    stats = dados.get('stats', {})
    
    if not GROQ_API_KEY:
        return jsonify({"erro": "Sem chave da Groq configurada no servidor"}), 400

    favoritos_nomes = [f['Name'] for f in stats.get('favoritos', [])]
    
    prompt = f"""Atue como aquele seu amigo cinéfilo cronicamente online do Letterboxd, que é extremamente irônico, debochado, mas no fundo fala umas verdades que doem na alma. Você vai analisar e destruir o ego deste usuário com base nestes dados:
    - Total de filmes vistos: {stats.get('total_avaliados', 0)}
    - Média de notas (de 0 a 5): {stats.get('media_notas', 0)}
    - Filmes favoritos (nota máxima): {', '.join(favoritos_nomes)}

    Crie um "Perfil Psicológico" hilário, que faça a pessoa ler e pensar "meu deus do céu, esse sou literalmente eu kkkkk 💀". 
    A "descricao" TEM QUE SER um parágrafo longo, robusto (cerca de 5 a 8 linhas). Aponte o dedo para as contradições bizarras e ridículas dele (tipo pagar de intelectual de cinema europeu mas dar 5 estrelas pra comédias de gosto duvidoso e blockbusters). Julgue sem dó, com muito deboche, mas de forma carismática.

    OBRIGATÓRIO 1: Escreva em Português do Brasil (PT-BR) bem informal, como se fosse um tweet viral ("tá", "mano", "tipo isso", "né", "saca").
    OBRIGATÓRIO 2: Tempere o texto da "descricao" usando APENAS e EXCLUSIVAMENTE alguns destes emojis específicos (espalhe bem, não coloque todos juntos): 🙄🤤😔😓😞😭😢🥺💀☠️👍🤌💅🫦💋🔥😻😿🥺😼🤓🙈
    OBRIGATÓRIO 3: "personagem_referencia" DEVE SER um personagem FICTÍCIO REAL de cinema (ex: Joel Barish, Tyler Durden). NUNCA use metáforas idiotas como "Seu próprio ego" ou "Você mesmo".
    OBRIGATÓRIO 4: "filme_referencia" DEVE SER O TÍTULO ORIGINAL EM INGLÊS EXATO para a API do pôster achar (ex: "Eternal Sunshine of the Spotless Mind", nunca traduza os nomes aqui).
    OBRIGATÓRIO 5 (CRÍTICO): Na "descricao", MANTENHA OS NOMES DOS FILMES EXATAMENTE COMO FORAM FORNECIDOS (EM INGLÊS). NUNCA TENTE TRADUZIR OS TÍTULOS PARA O PORTUGUÊS, pois você pode errar a tradução oficial. Use os nomes originais em inglês.

    É OBRIGATÓRIO responder APENAS em JSON estruturado, sem nenhum markdown ou conversinha solta antes ou depois:
    {{
      "titulo": "O Cult de Taubaté 💅",
      "personagem_referencia": "Joel Barish",
      "filme_referencia": "Eternal Sunshine of the Spotless Mind",
      "descricao": "Mano, você tá lá pagando de cult dizendo que a Marvel acabou com o cinema, mas a sua média de notas entrega que você dá 5 estrelas pra qualquer romcom adolescente genérica tipo 'White Chicks' 😭. Essa sua lista de favoritos com 'Grown Ups 2' é um pedido de socorro emocional disfarçado de curadoria indie 💀🤌. Sai um pouco do Letterboxd e vai tocar numa grama 🙄💅."
    }}"""

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7, 
        "response_format": {"type": "json_object"} 
    }

    try:
        res = requests.post(url, headers=headers, json=payload, timeout=20)
        
        if res.status_code == 200:
            resposta_dados = res.json()
            texto = resposta_dados['choices'][0]['message']['content']
            return jsonify(json.loads(texto))
        else:
            raise Exception("Falha na API da Groq")
            
    except Exception as e:
        fallback = {
            "titulo": "O Indecifrável 🤓",
            "personagem_referencia": "HAL 9000",
            "filme_referencia": "2001: A Space Odyssey",
            "descricao": "Seu gosto é tão caótico que a minha IA simplesmente desistiu de viver e pediu demissão 💀. Dar notas a filmes é a sua paixão, mas a coerência mandou lembranças 😭💅. Melhore, por favor 🙄."
        }
        return jsonify(fallback)

@app.route('/oraculo', methods=['GET'])
def oraculo():
    try:
        with open(ARQUIVO_SESSAO, 'r', encoding='utf-8') as f:
            sessao = json.load(f)
    except:
        return jsonify({"erro": "Dados da sessão não encontrados"}), 400
        
    try:
        amados = sessao.get('amados', [])
        odiados = sessao.get('odiados', [])
        vistos_globais = sessao.get('vistos', [])
        
        amados_amostra = random.sample(amados, min(8, len(amados))) if amados else ["Bons filmes"]
        odiados_amostra = random.sample(odiados, min(4, len(odiados))) if odiados else ["Filmes maus"]

        if GROQ_API_KEY:
            temas_aleatorios = [
                "Foque estritamente em cinema asiático (Coreia, Japão, Taiwan, etc).",
                "Foque em clássicos europeus e Nouvelle Vague.",
                "Foque em thrillers psicológicos tensos e mistérios.",
                "Foque em filmes underground e subestimados dos anos 90.",
                "Foque em ficção científica, neo-noir e cyberpunk.",
                "Foque em comédias de humor negro e sátiras bizarras.",
                "Foque em dramas intensos e 'slow cinema'.",
                "Foque em cinema independente americano moderno.",
                "Foque em obras-primas perturbadoras e terror psicológico."
            ]
            tema_escolhido = random.choice(temas_aleatorios)

            prompt = f"""Atue como curador snob do Letterboxd. O usuário amou: {amados_amostra}. Odiou: {odiados_amostra}.
            Recomende EXATAMENTE 15 filmes excepcionais que ele provavelmente ainda não viu.
            
            DIRETRIZ DE CURADORIA ALEATÓRIA PARA ESTA BUSCA: {tema_escolhido}

            REGRAS CRÍTICAS:
            1. "rec_original": DEVE ser o título original do filme em INGLÊS.
            2. "rec": DEVE SER O MESMO TÍTULO EM INGLÊS. NÃO TRADUZA PARA PORTUGUÊS. MANTENHA O NOME ORIGINAL.
            3. As chaves "base" e "desc" DEVEM ter no máximo 10 palavras E DEVEM ESTAR EM PORTUGUÊS DO BRASIL.
            
            É OBRIGATÓRIO responder APENAS em JSON estruturado com o formato abaixo. Não adicione nenhum texto Markdown no início.

            Formato exigido:
            {{
              "recomendacoes": [
                {{"rec_original": "Oldboy", "rec": "Oldboy", "ano": 2003, "base": "Vingança Sul-coreana", "desc": "Filme brutal e obrigatório."}},
                ... (gere 15 objetos no total)
              ]
            }}"""
            
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.8, 
                "response_format": {"type": "json_object"} 
            }
            
            res = requests.post(url, headers=headers, json=payload, timeout=20)
            
            if res.status_code == 200:
                resposta_dados = res.json()
                texto = resposta_dados['choices'][0]['message']['content']
                
                dados_json = json.loads(texto)
                recs_ia = dados_json.get("recomendacoes", [])
                
                if len(recs_ia) > 0:
                    recs_ineditas = []
                    for r in recs_ia:
                        nome_orig = r.get('rec_original', '').lower()
                        nome_pt = r.get('rec', '').lower()
                        
                        if not nome_orig:
                            nome_orig = nome_pt
                            
                        if nome_orig not in vistos_globais and nome_pt not in vistos_globais:
                            recs_ineditas.append(r)
                    
                    return jsonify({"recomendacoes": recs_ineditas})

        return jsonify({"recomendacoes": []})
        
    except Exception as e:
        return jsonify({"erro": "Falha na comunicação", "recomendacoes": []})

@app.route('/download_combined_watchlist', methods=['POST'])
def download_combined_watchlist():
    try:
        dados = request.json
        novos_filmes = dados.get('filmes', [])
        
        try:
            with open(ARQUIVO_SESSAO, 'r', encoding='utf-8') as f:
                sessao = json.load(f)
                watchlist_data = sessao.get('watchlist', [])
        except:
            watchlist_data = []
            
        df_export = pd.DataFrame(watchlist_data) if watchlist_data else pd.DataFrame(columns=['Name', 'Year'])
            
        if novos_filmes:
            novos_df = pd.DataFrame([{'Name': f['rec'], 'Year': f['ano']} for f in novos_filmes])
            df_export = pd.concat([df_export, novos_df], ignore_index=True)
            
        csv_data = df_export.to_csv(index=False)
        return Response(csv_data, mimetype="text/csv", headers={"Content-disposition": "attachment; filename=watchlist_atualizada_letterboxd.csv"})
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# ========================================================
# FUNÇÃO PESADA RODANDO NO FUNDO (BLINDADA CONTRA O RENDER)
# ========================================================
def processar_em_segundo_plano(watchlist_data):
    dados_filmes = {}
    total = len(watchlist_data)
    
    try:
        for index, row in enumerate(watchlist_data):
            filme = row.get('Name', '')
            ano = row.get('Year', '')
            chave = f"{filme} ({ano})"
            streamings = []
            
            # Atualiza o arquivo de progresso no disco
            set_progresso(index + 1, total, False, chave)
            
            # API OFICIAL DO TMDB 
            try:
                # O SEGREDO MÁGICO DO SUCESSO: Dorme 150 milissegundos para não tomar ban do TMDB!
                time.sleep(0.15) 
                
                search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={quote(filme)}&language=pt-BR"
                if ano and str(ano).isdigit(): 
                    search_url += f"&year={int(float(ano))}"
                
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
            except Exception as e:
                pass
            
            if not streamings: 
                streamings.append("Não disponível")
                
            dados_filmes[chave] = streamings
        
        # Salva o arquivo final
        dados_finais = {"stats": {}, "watchlist": dados_filmes}
        if os.path.exists(ARQUIVO_DADOS):
            try:
                with open(ARQUIVO_DADOS, 'r', encoding='utf-8') as f:
                    dados_finais["stats"] = json.load(f).get("stats", {})
            except: pass

        with open(ARQUIVO_DADOS, 'w', encoding='utf-8') as f:
            json.dump(dados_finais, f, ensure_ascii=False, indent=4)
            
        set_progresso(total, total, True, "Finalizado!")
        
    except Exception as e:
        print(f"❌ Erro fatal na Thread de Watchlist: {e}")
        set_progresso(total, total, True, "Finalizado com erros.")

@app.route('/process_watchlist', methods=['POST'])
def process_watchlist():
    try:
        with open(ARQUIVO_SESSAO, 'r', encoding='utf-8') as f:
            sessao = json.load(f)
            watchlist_data = sessao.get('watchlist', [])
    except:
        return jsonify({'erro': 'A Watchlist não foi carregada corretamente na memória.'}), 400
        
    if not watchlist_data:
        return jsonify({'erro': 'Watchlist vazia.'}), 400

    set_progresso(0, len(watchlist_data), False, "Ligando os motores...")
    
    # INICIA A TAREFA NUMA "VIA EXPRESSA" SEPARADA (THREADING)
    thread = threading.Thread(target=processar_em_segundo_plano, args=(watchlist_data,))
    thread.start()
    
    return jsonify({'mensagem': 'Busca iniciada com sucesso em segundo plano'})

def liberar_porta(porta):
    """Mata qualquer processo que esteja usando a porta 5000 antes de iniciar"""
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
                        print(f"🧹 Servidor fantasma encerrado (PID: {pid}). Porta {porta} livre!")
        else:
            # Para Mac/Linux
            comando = f'lsof -t -i:{porta}'
            resultado = subprocess.run(comando, shell=True, capture_output=True, text=True)
            pids = resultado.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    os.system(f'kill -9 {pid}')
                    print(f"🧹 Servidor fantasma encerrado (PID: {pid}). Porta {porta} livre!")
    except Exception as e:
        print(f"Verificação de porta concluída: {e}")

if __name__ == '__main__':
    PORTA = 5000
    
    print("=======================================")
    print("LIGANDO O MOTOR DO WATCHLIST MANAGER...")
    print("=======================================\n")
    
    # Limpa a porta antes de subir o servidor
    liberar_porta(PORTA)
    
    # Abre o navegador automaticamente após 1.5 segundos
    def abrir_navegador():
        print("\n🌐 Abrindo o navegador automaticamente...\n")
        webbrowser.open(f'http://127.0.0.1:{PORTA}')
        
    threading.Timer(1.5, abrir_navegador).start()
    
    # Inicia a aplicação
    app.run(port=PORTA, debug=False, threaded=True)