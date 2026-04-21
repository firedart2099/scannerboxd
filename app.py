# ... existing code ...
@app.route('/gerar_perfil', methods=['POST'])
def gerar_perfil():
# ... existing code ...
    amados_recentes = stats.get('amados_recentes', [])
    odiados_recentes = stats.get('odiados_recentes', [])
    
    prompt = f"""Atue como um curador de cinema experiente, analítico, sincero e 100% IMPARCIAL. Você observa os padrões de gosto do usuário com precisão, mas de forma respeitosa, inteligente e elegante. Sem toxidade, sem ser grosseiro ou rabugento.
    
    DADOS DO USUÁRIO:
    - Nome: {username}
    - Bio do Perfil: "{bio}"
    - Filmes que a pessoa mais ama: {', '.join(filmes_amados) if filmes_amados else 'Nenhum'}
    - Outros filmes que avaliou com 5 estrelas: {', '.join(amados_recentes) if amados_recentes else 'Nenhum'}
    - Filmes com notas baixas (não gostou): {', '.join(odiados_recentes) if odiados_recentes else 'Nenhum'}
    - Média de Notas: {stats.get('media_notas', 0)}
    - Total de Filmes Avaliados: {stats.get('total_avaliados', 0)}
    
    REGRAS DA MISSÃO:
    1. Escreva uma análise sincera em EXATAMENTE 2 PARÁGRAFOS. Foque na verdadeira identidade cinematográfica do usuário.
    2. OBRIGATÓRIO: USE OS DADOS ACIMA! Aponte os contrastes nas escolhas (ex: se gosta de blockbusters, valide o entretenimento; se gosta de cults obscuros, reconheça a busca por estética/profundidade). Trate as escolhas de quem não gostou como uma divergência de estilo, não como um erro.
    3. O TÍTULO DA RESPOSTA: Invente um arquétipo lisonjeiro, intrigante ou reflexivo (ex: "O Eclético Contemplativo", "O Sommelier de Épicos", "A Bússola do Cinema Indie"). NUNCA ofenda no título.
    4. EMOJIS: Use emojis sofisticados e sutis (ex: 🎬✨🍷👁️🎞️🧭🎭).
    5. "personagem_referencia": ESCOLHA COM INTELIGÊNCIA! Escolha um personagem de cinema que represente a "vibe" dessa pessoa.
    6. EXPLICAÇÃO DO PERSONAGEM: No FINAL do seu segundo parágrafo, explique de forma envolvente o porquê de ter escolhido esse personagem para representar a personalidade cinematográfica do usuário.
    7. ZERO asteriscos (*) ou formatação Markdown.
    
    Responda OBRIGATORIAMENTE em formato json estruturado exatamente assim:
    {{ 
        "titulo": "SEU RÓTULO AQUI", 
        "personagem_referencia": "NOME DO PERSONAGEM", 
        "filme_referencia": "NOME DO FILME", 
        "descricao": [
            "PRIMEIRO PARÁGRAFO",
            "SEGUNDO PARÁGRAFO COM A EXPLICAÇÃO DO PERSONAGEM"
        ]
    }}"""
    
    try: 
# ... existing code ...
@app.route('/oraculo', methods=['GET', 'POST'])
def oraculo():
# ... existing code ...
            for r in recs_ia:
                nome = r.get('rec', '').strip().lower()
                orig = r.get('rec_original', '').strip().lower()
                
                if nome not in blacklist_total and orig not in blacklist_total:
                    # Trava forte de duplicatas: Cruza Título Traduzido com Título Original
                    ja_tem = False
                    for rf in recs_finais:
                        rf_nome = rf.get('rec', '').strip().lower()
                        rf_orig = rf.get('rec_original', '').strip().lower()
                        if nome == rf_nome or orig == rf_orig or nome == rf_orig or orig == rf_nome:
                            ja_tem = True
                            break
                            
                    if not ja_tem:
                        recs_finais.append(r)
                        if len(recs_finais) >= 8: break 
            
            tentativas_ia += 1
# ... existing code ...
```

### 2. Atualizar o Frontend (Lógica de Resgate de Imagens)
No seu arquivo **`index (1).html`**, desça até a função `renderizarOraculoCards(recs, start)`. Vamos substituir a chamada do TMDB que era só 1 linha por uma função inteligente que tenta caçar a imagem pelo Título Original caso o português falhe.

```html:Scannerbox Frontend:index (1).html
<!-- ... existing code ... -->
                        <div class="w-full flex-1 overflow-y-auto no-scrollbar flex flex-col justify-center items-center mb-1">
                            <p class="text-[9px] sm:text-[11px] text-gray-300 leading-snug sm:leading-relaxed line-clamp-6">"${r.desc}"</p>
                        </div>
                        <span class="text-[7px] sm:text-[9px] text-[#40bcf4] font-black uppercase tracking-widest mt-auto shrink-0">CLIQUE P/ SELECIONAR</span> 
                    </div>
                </div>
            `);
            
            // Sistema de Fallback Inteligente para Imagens Obscuras
            const fetchPoster = async (title, year, originalTitle) => {
                // Tentativa 1: Título Português + Ano
                let url = `/api/tmdb/search?query=${encodeURIComponent(title)}&year=${year}`;
                let res = await fetch(url);
                let data = await res.json();
                if (data.results?.[0]?.poster_path) return data.results[0].poster_path;

                // Tentativa 2: Só Título Português (O ano no TMDB pode estar +1 ou -1)
                url = `/api/tmdb/search?query=${encodeURIComponent(title)}`;
                res = await fetch(url);
                data = await res.json();
                if (data.results?.[0]?.poster_path) return data.results[0].poster_path;

                // Tentativa 3: Título Original (Garante que filmes cult/internacionais sejam achados)
                if (originalTitle && originalTitle.toLowerCase() !== title.toLowerCase()) {
                    url = `/api/tmdb/search?query=${encodeURIComponent(originalTitle)}`;
                    res = await fetch(url);
                    data = await res.json();
                    if (data.results?.[0]?.poster_path) return data.results[0].poster_path;
                }
                return null;
            };

            fetchPoster(r.rec, r.ano, r.rec_original).then(path => {
                if(path) { 
                    const img = document.querySelector(`#${id} img`); 
                    img.src = `https://image.tmdb.org/t/p/w500${path}`; 
                    img.onload = () => img.style.opacity = '1'; 
                }
            });
            
            setTimeout(()=>document.getElementById(id)?.classList.remove('opacity-0','translate-y-4'), 100+(i*200));
        });
    }

    function abrirTutorial() { document.getElementById('tutorial-modal').classList.remove('hidden'); document.getElementById('tutorial-modal').classList.add('flex'); }
<!-- ... existing code ... -->
```

Com isso aí:
* Seus amigos vão parar de tomar esculacho e vão ler uma análise cirúrgica e classuda.
* Cartazes de pérolas do cinema iraniano, russo e alemão vão carregar direitinho.
* Clones e duplicatas de filmes japoneses vão ser barrados na porta do Python. 

Aplica e sobe pro ar!
