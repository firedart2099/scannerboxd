# ... existing code ...
def gerar_resposta_ia(prompt, max_tokens=800):
    # 1. TENTA NVIDIA
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
            # TIMEOUT AUMENTADO PARA 28s PARA ELA CONSEGUIR PENSAR
            res_nv = requests.post(url_nv, headers=headers_nv, json=payload_nv, timeout=28)
            if res_nv.status_code == 200:
                return limpar_e_parsear_json(res_nv.json()['choices'][0]['message']['content'])
            else: print(f"⚠️ NVIDIA falhou (Status {res_nv.status_code})")
        except Exception as e: print(f"Erro NVIDIA: {e}")

    # 2. TENTA GROQ
# ... existing code ...
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

        while len(recs_finais) < 4 and tentativas_ia < 2:
            favoritos = request.json.get('favorites', [])
            blacklist_amostra = random.sample(list(blacklist_total), min(25, len(blacklist_total)))

            prompt = f"""Atue como curador obscuro. Favoritos do usuário: {favoritos}.
            Recomende EXATAMENTE 15 filmes Lado B, Cults, estrangeiros ou esquecidos.
            
            ESQUEÇA ESTES: {', '.join(blacklist_amostra)}
            Responda APENAS JSON:
            {{ "recomendacoes": [ {{"rec_original": "TITULO ORIGINAL", "rec": "TITULO EM PT", "ano": 2000, "base": "GENERO", "desc": "Pequena sinopse."}} ] }}"""

            try:
                dados_json = gerar_resposta_ia(prompt, max_tokens=1000)
                recs_ia = dados_json.get("recomendacoes", []) if dados_json else []
                
                for r in recs_ia:
                    nome = r.get('rec', '').strip().lower()
                    orig = r.get('rec_original', '').strip().lower()
                    if nome not in blacklist_total and orig not in blacklist_total:
                        if nome not in [rf['rec'].lower() for rf in recs_finais]:
                            recs_finais.append(r)
                            if len(recs_finais) >= 8: break 
            except Exception as e:
                pass
            
            tentativas_ia += 1
            if len(recs_finais) < 4: time.sleep(0.5)

        res_payload = {"recomendacoes": recs_finais[:4]} 
# ... existing code ...
```

**DICA DE OURO PRO RENDER:**
Se você quiser garantir que o Render **NUNCA MAIS** mate seu servidor por causa de tempo, vai lá no painel de controle do Render, nas configurações do seu Web Service.
Onde tá escrito **Start Command** (Comando de inicialização), se tiver algo como `gunicorn app:app`, muda pra isso aqui:
`gunicorn app:app --timeout 120`

Isso vai dar 2 minutos de respiro pro seu servidor pensar com calma sem tomar um tiro na nuca do sistema! Com o código otimizado e esse comando, as recomendações vão vir rasgando.
