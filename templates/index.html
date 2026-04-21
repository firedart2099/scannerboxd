<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Scannerboxd</title>
    <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><circle cx=%2220%22 cy=%2250%22 r=%2215%22 fill=%22%2300e054%22/><circle cx=%2250%22 cy=%2250%22 r=%2215%22 fill=%22%2340bcf4%22/><circle cx=%2280%22 cy=%2250%22 r=%2215%22 fill=%22%23ff8000%22/></svg>">
    
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;700;900&family=Space+Grotesk:wght@300;700&display=swap" rel="stylesheet">
    
    <style>
        body { 
            font-family: 'Inter', sans-serif;
            background-color: #0f1115;
            color: #ffffff;
            margin: 0; padding: 0;
            overflow-x: hidden;
        }

        h1, h2, h3, .space-font { font-family: 'Space Grotesk', sans-serif; }

        /* O GLASSMORPHISM PERFEITO (Estilo Tidal / Fluent Design Premium) */
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
            background: rgba(30, 35, 42, 0.65) !important;
            border-color: rgba(64, 188, 244, 0.2) !important;
        }

        .no-scrollbar::-webkit-scrollbar { display: none; }
        .no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }

        /* Custom Scrollbar Elegante */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: #0f1115; }
        ::-webkit-scrollbar-thumb { background: rgba(64, 188, 244, 0.3); border-radius: 10px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(64, 188, 244, 0.6); }
        
        /* As 3 Bolinhas da Bottom Nav Flutuante */
        .bottom-nav-dot {
            width: 14px; height: 14px;
            border-radius: 50%;
            cursor: pointer;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            box-shadow: 0 4px 10px rgba(0,0,0,0.8);
            position: relative;
            user-select: none; /* Tira o "risquinho" do cursor */
            -webkit-user-select: none;
        }
        .bottom-nav-dot.active { transform: scale(1.5); z-index: 10; box-shadow: 0 0 15px currentColor; }
        
        .dot-green { background-color: #00e054; color: #00e054; }
        .dot-blue { background-color: #40bcf4; color: #40bcf4; }
        .dot-orange { background-color: #ff8000; color: #ff8000; }

        .movie-card { aspect-ratio: 2/3; position: relative; border-radius: 12px; overflow: hidden; background: transparent; }
        .movie-card img { width: 100%; height: 100%; object-fit: cover; }
    </style>
</head>
<body class="text-white relative w-screen h-screen overflow-hidden">

<!-- Fundo com Imagem Escurecida -->
<div class="fixed inset-0 w-full h-full z-0 bg-[#0f1115] pointer-events-none">
    <img id="hero-backdrop-img" src="https://image.tmdb.org/t/p/original/nMKdUUepR0i5zn0y1T4CsSB5chy.jpg" class="w-full h-full object-cover opacity-20 transition-opacity duration-1000 grayscale-[40%]">
    <div class="absolute inset-0 bg-gradient-to-b from-[#0f1115]/60 via-[#0f1115]/40 to-[#0f1115] pointer-events-none"></div>
</div>

<header class="absolute top-6 left-6 md:top-8 md:left-8 flex items-center gap-3 z-40 pointer-events-auto">
    <div class="flex items-center gap-1.5 cursor-pointer hover:scale-105 transition-transform" onclick="location.reload()">
        <div class="w-3 h-3 rounded-full bg-[#00e054]"></div>
        <div class="w-3 h-3 rounded-full bg-[#40bcf4]"></div>
        <div class="w-3 h-3 rounded-full bg-[#ff8000]"></div>
    </div>
    <div class="flex flex-col">
        <h1 class="text-xl font-bold tracking-widest text-white uppercase leading-none shadow-black drop-shadow-md">Scanner<span class="text-[#40bcf4]">boxd</span></h1>
        <p class="text-[8px] text-[#8c9bab] font-bold tracking-[0.3em] uppercase drop-shadow-md mt-1">v1.0.0 Oficial</p>
    </div>
</header>

<!-- TELA INICIAL -->
<div id="main-content" class="absolute inset-0 w-full h-full z-20 flex flex-col pt-[35vh] px-4 md:px-8 overflow-y-auto pb-32 transition-transform duration-700 ease-in-out">
    <div class="max-w-2xl mx-auto w-full">
        
        <div class="text-center space-y-2 mb-12">
            <h2 class="text-4xl md:text-6xl font-black text-white leading-tight tracking-tighter drop-shadow-[0_0_20px_rgba(255,255,255,0.15)]">
                QUAL É O SEU PERFIL <br>
                <span class="italic pr-2">CINEMATOGRÁFICO?</span>
            </h2>
            <p class="text-[#8c9bab] max-w-xl mx-auto text-sm md:text-base font-medium drop-shadow-md">Descubra a verdade sobre o seu gosto e encontre onde assistir a sua Watchlist.</p>
        </div>

        <div class="space-y-4 relative z-30">
            <!-- Passo 1 -->
            <a href="https://letterboxd.com/data/export/" target="_blank" class="fluent-glass flex items-center gap-4 px-6 py-4 w-full group hover:border-[#40bcf4]/50 pointer-events-auto">
                <span class="bg-[#40bcf4]/20 text-[#40bcf4] w-7 h-7 rounded-full flex items-center justify-center text-xs font-black shrink-0 group-hover:bg-[#40bcf4] group-hover:text-[#0f1115] transition-colors">1</span>
                <div class="text-left">
                    <span class="font-bold text-sm tracking-wide block text-white drop-shadow-sm">Baixar arquivo .ZIP oficial</span>
                    <span class="text-[9px] uppercase tracking-widest text-[#8c9bab] group-hover:text-[#40bcf4] transition-colors">Abre o Letterboxd em nova aba</span>
                </div>
                <svg class="w-5 h-5 text-[#40bcf4] ml-auto opacity-70 group-hover:opacity-100" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
            </a>

            <!-- Passo 2 -->
            <div class="fluent-glass p-8 text-center border-dashed border-2 border-[#40bcf4]/30 hover:border-[#40bcf4]/60 transition-all group cursor-pointer relative overflow-hidden pointer-events-auto">
                <label for="csv-file" id="dropzone-label" class="cursor-pointer block w-full h-full">
                    <div class="w-16 h-16 bg-[#40bcf4]/10 rounded-full flex items-center justify-center mx-auto mb-4 group-hover:scale-110 transition-all border border-[#40bcf4]/30 shadow-inner">
                        <svg class="w-8 h-8 text-[#40bcf4]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z"></path></svg>
                    </div>
                    <p class="text-xl md:text-2xl font-bold text-white mb-1 drop-shadow-sm">Arraste seu arquivo <span class="text-[#40bcf4]">.zip</span> aqui</p>
                    <p class="text-[9px] md:text-[10px] text-[#8c9bab] uppercase tracking-widest font-bold">Nenhum dado é salvo nos servidores</p>
                </label>
                <input type="file" id="csv-file" class="hidden" accept=".zip" onchange="fileSelected()">
                
                <div id="action-area" class="hidden mt-4 flex-col items-center gap-4 relative z-10 animate-fade-in">
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

            <!-- Botão Mock -->
            <div class="text-center pt-6 pb-10 pointer-events-auto">
                <button onclick="iniciarMockupTeste()" class="text-[10px] text-[#40bcf4] font-bold uppercase tracking-widest underline decoration-dashed hover:text-white transition-colors opacity-50 hover:opacity-100">
                    🧪 Testar Layout (Modo Mock)
                </button>
            </div>
        </div>
    </div>
</div>

<!-- TELA DO APP (CARROSSEL) -->
<div id="app-view" class="fixed inset-0 w-full h-full z-30 hidden opacity-0 transition-opacity duration-700 pointer-events-none">
    
    <!-- Pílula de Loading Topo -->
    <div id="top-pill" class="absolute top-6 md:top-8 left-1/2 -translate-x-1/2 z-50 fluent-glass px-6 py-3 rounded-full flex items-center gap-3 transition-all duration-500 opacity-0 -translate-y-4 pointer-events-auto">
        <svg class="animate-spin w-4 h-4 text-[#40bcf4]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
        <p id="pill-text" class="text-white text-[9px] font-bold uppercase tracking-widest whitespace-nowrap">Invocando o Oráculo...</p>
    </div>

    <!-- 3 Telas -->
    <div id="carousel-wrapper" class="flex w-[300vw] h-full transition-transform duration-500 ease-in-out pointer-events-auto">
        
        <!-- TELA 1: PERFIL -->
        <div class="w-[100vw] h-full overflow-y-auto pb-32 pt-28 px-4 sm:px-8 flex flex-col items-center">
            <div class="max-w-2xl w-full space-y-6">
                <h2 class="text-2xl md:text-3xl font-black text-white text-center tracking-tighter drop-shadow-md mb-2" id="roast-title">
                    Analisando gosto... <svg class="animate-spin w-5 h-5 ml-2 text-[#00e054] inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                </h2>

                <div class="fluent-glass p-8 relative flex flex-col items-center text-center border-t-[#00e054]/30">
                    <div id="profile-avatar" class="w-20 h-20 rounded-full border-2 border-[#00e054] bg-[#0f1115] mb-6 flex items-center justify-center overflow-hidden shadow-[0_0_20px_rgba(0,224,84,0.3)]">
                        <svg class="w-8 h-8 text-[#2c3440]" fill="currentColor" viewBox="0 0 24 24"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>
                    </div>
                    <p class="text-gray-300 text-[11px] md:text-[12px] leading-loose px-2 md:px-6" id="roast-desc">
                        Aguarde. Cruzando dados na matriz para identificar seu arquétipo.
                    </p>
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

        <!-- TELA 2: ORÁCULO -->
        <div class="w-[100vw] h-full overflow-y-auto pb-32 pt-28 px-4 sm:px-8">
            <div class="max-w-4xl mx-auto">
                <div class="text-center mb-8">
                    <h2 class="text-3xl font-black text-white uppercase tracking-tighter">O Oráculo</h2>
                    <p class="text-[#40bcf4] text-[10px] font-bold tracking-widest uppercase">Escondidos no catálogo</p>
                </div>

                <div id="oracle-loading" class="flex flex-col items-center justify-center mt-20">
                    <div class="w-14 h-14 border-2 border-[#40bcf4]/20 border-t-[#40bcf4] rounded-full animate-spin"></div>
                    <p class="text-[#40bcf4] text-[10px] uppercase tracking-widest font-bold mt-6 animate-pulse">Escavando lado B...</p>
                </div>

                <div id="oracle-grid" class="hidden grid grid-cols-2 md:grid-cols-4 gap-4"></div>
                
                <!-- Botões do Oráculo -->
                <div id="oracle-actions" class="hidden mt-8 flex-col sm:flex-row justify-center items-center gap-4">
                    <button onclick="alert('Exportar clicado! Função real no backend.')" id="btn-export-oracle" class="fluent-glass px-6 py-3 text-[#40bcf4] text-[10px] font-black uppercase tracking-widest hover:bg-[#40bcf4]/20 transition-all border border-[#40bcf4]/30 w-full sm:w-auto">
                        Exportar Selecionados
                    </button>
                    <button onclick="carregarMaisSugestoes()" class="fluent-glass px-6 py-3 text-white text-[10px] font-black uppercase tracking-widest hover:bg-white/10 transition-all w-full sm:w-auto">
                        Descobrir Mais
                    </button>
                </div>
            </div>
        </div>

        <!-- TELA 3: WATCHLIST -->
        <div class="w-[100vw] h-full overflow-y-auto pb-32 pt-28 px-4 sm:px-8">
            <div class="max-w-4xl mx-auto h-full flex flex-col items-center">
                <div class="text-center mb-8 shrink-0">
                    <h2 class="text-3xl font-black text-white uppercase tracking-tighter">O Catálogo</h2>
                    <p class="text-[#ff8000] text-[10px] font-bold tracking-widest uppercase">Onde assistir sua Watchlist</p>
                </div>

                <div id="watchlist-loading" class="flex flex-col items-center justify-center mt-10">
                    <div class="w-16 h-16 rounded-full border-2 border-transparent border-t-[#ff8000] border-l-[#ff8000] animate-spin mb-6"></div>
                    <span id="load-percent" class="space-font text-5xl font-black text-white tracking-tighter mb-2">0%</span>
                    <p class="text-[#ff8000] text-[9px] uppercase tracking-widest font-bold">Verificando streamings</p>
                </div>

                <div id="watchlist-content" class="hidden w-full space-y-4">
                    <!-- Search & Filter Area Minimalista -->
                    <div class="fluent-glass p-2 shrink-0 relative flex items-center">
                        <svg class="w-4 h-4 text-[#8c9bab] ml-3 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                        <input type="text" id="search-input" oninput="handleSearch()" placeholder="Procurar filme..." class="w-full bg-transparent border-none text-white px-3 py-2 focus:outline-none text-sm">
                        
                        <!-- Filter Button -->
                        <button onclick="toggleFilterDropdown()" class="text-[#ff8000] hover:text-white p-2 rounded transition-colors">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"></path></svg>
                        </button>

                        <!-- Dropdown de Streamings -->
                        <div id="filter-dropdown" class="hidden absolute right-2 top-[110%] w-56 fluent-glass p-2 z-50 flex flex-col gap-1 max-h-64 overflow-y-auto no-scrollbar shadow-2xl border border-[#ff8000]/30">
                            <!-- Injetado via JS -->
                        </div>
                    </div>
                    
                    <ul id="results" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mt-4"></ul>
                </div>
            </div>
        </div>
    </div>

    <!-- Navegação Flutuante Rodapé (As 3 Bolinhas) -->
    <div class="absolute bottom-8 left-1/2 -translate-x-1/2 z-50 flex items-center justify-center gap-2.5 pointer-events-auto">
        <div class="bottom-nav-dot dot-green active" onclick="slideTo(0)" title="Perfil"></div>
        <div class="bottom-nav-dot dot-blue" id="tab-oracle" onclick="slideTo(1)" title="Oráculo"></div>
        <div class="bottom-nav-dot dot-orange" id="tab-watch" onclick="slideTo(2)" title="Watchlist"></div>
    </div>
</div>

<script>
    let sessionId = localStorage.getItem('oraculo_session_id') || crypto.randomUUID();
    localStorage.setItem('oraculo_session_id', sessionId);
    let statsData = {};
    let oraculoDb = [];

    const iconicMovies = [
        "https://image.tmdb.org/t/p/original/nMKdUUepR0i5zn0y1T4CsSB5chy.jpg", 
        "https://image.tmdb.org/t/p/original/rAiYTfKGqDCRIIqo664sY9XZIvQ.jpg", 
        "https://image.tmdb.org/t/p/original/8ZTVqvKDQ8emSGUEMjsS4yHAwrp.jpg"  
    ];
    let currentBgIdx = 0;
    let bgInterval;

    function startBgSlideshow() {
        const heroImg = document.getElementById('hero-backdrop-img');
        if (!heroImg) return;
        bgInterval = setInterval(() => {
            currentBgIdx = (currentBgIdx + 1) % iconicMovies.length;
            heroImg.style.opacity = '0'; 
            setTimeout(() => { heroImg.src = iconicMovies[currentBgIdx]; heroImg.style.opacity = '0.2'; }, 1000);
        }, 6000);
    }
    document.addEventListener('DOMContentLoaded', startBgSlideshow);

    let currentSlide = 0;
    function slideTo(index) {
        const wrapper = document.getElementById('carousel-wrapper');
        const tabs = document.querySelectorAll('.bottom-nav-dot');
        if (!wrapper || tabs.length === 0) return;
        currentSlide = index;
        wrapper.style.transform = `translateX(-${index * 100}vw)`;
        tabs.forEach((t, i) => { t.classList.toggle('active', i === index); });
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
        } catch(e) {
            alert("Erro ao ler o ZIP. Tente de novo.");
            btn.innerHTML = `Iniciar Análise`;
            btn.disabled = false;
        }
    }

    function iniciarAppReal() {
        clearInterval(bgInterval);
        document.getElementById('main-content').style.transform = 'translateY(-100vh)';
        
        setTimeout(() => {
            document.getElementById('main-content').classList.add('hidden');
            const appView = document.getElementById('app-view');
            appView.classList.remove('hidden');
            void appView.offsetWidth;
            appView.classList.remove('opacity-0');
            appView.classList.remove('pointer-events-none');
            
            document.getElementById('top-pill').classList.remove('opacity-0', '-translate-y-4');
            document.getElementById('stat-total').innerText = statsData.total_avaliados || 0;
            document.getElementById('stat-avg').innerText = (statsData.media_notas || 0).toFixed(2);

            gerarPerfilIA();
            iniciarFluxoWatchlist();
            setTimeout(() => carregarOraculo(), 6000); 
        }, 700);
    }

    async function gerarPerfilIA() {
        try {
            const res = await fetch('/gerar_perfil', {
                method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({stats: statsData})
            });
            const data = await res.json();
            if(!data.erro && data.titulo) {
                document.getElementById('roast-title').innerText = data.titulo;
                document.getElementById('roast-desc').innerHTML = data.descricao.replace(/\n/g, '<br><br>');
                if(data.filme_referencia) fetchPosterAvatar(data.filme_referencia);
            }
        } catch(e) {
            document.getElementById('roast-title').innerText = "Perfil Indisponível";
            document.getElementById('roast-desc').innerText = "A IA falhou. Leia suas recomendações nas outras abas.";
        }
    }

    async function fetchPosterAvatar(title) {
        try {
            const r = await fetch(`/api/tmdb/search?query=${encodeURIComponent(title)}`);
            const d = await r.json();
            if(d.results?.[0]?.poster_path) {
                document.getElementById('profile-avatar').innerHTML = `<img src="https://image.tmdb.org/t/p/w500${d.results[0].poster_path}" class="w-full h-full object-cover">`;
            }
        } catch(e){}
    }

    // NOVA FUNÇÃO COM FALLBACK DE ANO PARA NÃO FICAR POSTER PRETO
    async function fetchPosterFallback(title, year, imgElementId) {
        try {
            let res = await fetch(`/api/tmdb/search?query=${encodeURIComponent(title)}&year=${year}`);
            let d = await res.json();
            
            // Se não achar com o ano exato, tenta só com o nome (Plano B do TMDB)
            if(!d.results || d.results.length === 0) {
                res = await fetch(`/api/tmdb/search?query=${encodeURIComponent(title)}`);
                d = await res.json();
            }

            if(d.results?.[0]?.poster_path) {
                const img = document.querySelector(`#${imgElementId} img`);
                if(img) {
                    img.src = `https://image.tmdb.org/t/p/w500${d.results[0].poster_path}`;
                    img.onload = () => img.style.opacity = '1';
                }
            }
        } catch(e) {}
    }

    async function carregarOraculo() {
        try {
            const res = await fetch(`/oraculo?session_id=${sessionId}`, {
                method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({ favorites: statsData.profile_favorites || [], exclude: [] })
            });
            const data = await res.json();
            
            document.getElementById('oracle-loading').classList.add('hidden');
            document.getElementById('oracle-grid').classList.remove('hidden');
            document.getElementById('oracle-actions').classList.remove('hidden');
            document.getElementById('oracle-actions').classList.add('flex');

            if(data.recomendacoes && data.recomendacoes.length > 0) {
                renderizarOraculoCards(data.recomendacoes);
                document.getElementById('tab-oracle').innerHTML = ''; // Limpa bolinha
            }
        } catch(e) {}
    }

    function renderizarOraculoCards(recs) {
        const grid = document.getElementById('oracle-grid');
        recs.forEach(r => {
            const id = 'movie-' + Math.random().toString(36).substr(2, 9);
            grid.innerHTML += `
                <div id="${id}" class="fluent-glass movie-card p-2 flex flex-col justify-center items-center border-transparent border-2 hover:border-[#40bcf4] transition-all group overflow-hidden">
                    <img src="" class="rounded w-full h-full object-cover absolute inset-0 opacity-0 transition-opacity z-0">
                    <div class="absolute inset-0 bg-gradient-to-t from-[#0f1115] via-[#0f1115]/80 to-transparent opacity-0 group-hover:opacity-100 transition-opacity z-10 flex flex-col justify-end p-3 text-center">
                        <span class="text-[8px] text-[#40bcf4] font-black uppercase tracking-widest">${r.base}</span>
                        <p class="text-[10px] font-bold text-white mt-1 leading-tight">${r.rec}</p>
                    </div>
                </div>
            `;
            // Chama a função parruda que tem o plano B
            fetchPosterFallback(r.rec, r.ano, id);
        });
    }

    function carregarMaisSugestoes() {
        alert("Buscando mais clássicos obscuros... (Integração na próxima versão)");
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
                        document.getElementById('watchlist-loading').classList.add('hidden');
                        document.getElementById('watchlist-content').classList.remove('hidden');
                        document.getElementById('top-pill').classList.add('opacity-0', '-translate-y-4');

                        const finalRes = await fetch(`/dados?session_id=${sessionId}`);
                        const finalData = await finalRes.json();
                        rawDatabase = finalData.watchlist;
                        gerarFiltrosEWatchlist(rawDatabase);
                    }
                }
            }, 2500); 
        } catch(e) {}
    }

    // SISTEMA DE FILTRO DROPDOWN
    let activeFilter = 'Todos';

    function toggleFilterDropdown() {
        document.getElementById('filter-dropdown').classList.toggle('hidden');
    }

    function aplicarFiltro(plataforma) {
        activeFilter = plataforma;
        toggleFilterDropdown();
        handleSearch(); // Re-renderiza a lista
    }

    function gerarFiltrosEWatchlist(db) {
        const counts = {};
        for(const [filme, streamings] of Object.entries(db)) {
            streamings.forEach(s => { if(s !== 'Não disponível') counts[s] = (counts[s] || 0) + 1; });
        }

        const drop = document.getElementById('filter-dropdown');
        drop.innerHTML = `<button onclick="aplicarFiltro('Todos')" class="w-full text-left px-3 py-2 text-xs font-bold text-white hover:bg-white/10 rounded transition">Todas as Plataformas</button>`;
        
        Object.entries(counts).sort((a,b)=>b[1]-a[1]).forEach(([n, count]) => {
            drop.innerHTML += `
                <button onclick="aplicarFiltro('${n}')" class="w-full flex items-center justify-between px-3 py-2 hover:bg-white/10 rounded transition text-left">
                    <span class="text-xs font-bold text-white truncate pr-2">${n}</span>
                    <span class="text-[10px] text-[#ff8000] font-black bg-[#ff8000]/10 px-1.5 py-0.5 rounded">${count}</span>
                </button>
            `;
        });

        handleSearch(); // Renderiza a primeira vez (Todos)
    }

    function handleSearch() {
        const q = document.getElementById('search-input').value.toLowerCase();
        const res = document.getElementById('results');
        res.innerHTML = '';
        
        for(const [filme, streamings] of Object.entries(rawDatabase)) {
            const match = filme.match(/(.*)\s\((\d{4})\)$/);
            const titulo = match ? match[1] : filme;
            const ano = match ? match[2] : "";

            // Lógica do Filtro Dropdown e da Pesquisa Textual
            if (activeFilter !== 'Todos' && !streamings.includes(activeFilter)) continue;
            if (q && !titulo.toLowerCase().includes(q)) continue;
            if (activeFilter === 'Todos' && !q && streamings[0] === "Não disponível") continue;

            const plats = streamings.map(s => `<span class="bg-[#14181c] border border-[#ff8000]/30 text-[#ff8000] text-[8px] px-2 py-1 rounded font-black uppercase whitespace-nowrap">${s}</span>`).join(' ');

            res.innerHTML += `
                <li class="fluent-glass p-4 border-l-4 border-l-[#ff8000] flex flex-col justify-between gap-3">
                    <div>
                        <span class="text-white font-bold text-sm block leading-tight">${titulo}</span>
                        <span class="text-[#8c9bab] text-[10px] block mt-0.5">${ano}</span>
                    </div>
                    <div class="flex gap-1.5 flex-wrap">${plats}</div>
                </li>
            `;
        }
    }

    // MOCKUP TESTE 🧪
    function iniciarMockupTeste() {
        clearInterval(bgInterval);
        document.getElementById('main-content').style.transform = 'translateY(-100vh)';
        setTimeout(() => {
            document.getElementById('main-content').classList.add('hidden');
            const appView = document.getElementById('app-view');
            appView.classList.remove('hidden'); 
            void appView.offsetWidth; 
            appView.classList.remove('opacity-0', 'pointer-events-none');
            
            document.getElementById('top-pill').classList.remove('opacity-0', '-translate-y-4');
            document.getElementById('stat-total').innerText = "487";
            document.getElementById('stat-avg').innerText = "4.09";
            document.getElementById('roast-title').innerText = "O Explorador";
            document.getElementById('roast-desc').innerHTML = "Você é um verdadeiro cinéfilo. 🤓🍿";
            
            setTimeout(() => {
                document.getElementById('oracle-loading').classList.add('hidden');
                document.getElementById('oracle-grid').classList.remove('hidden');
                document.getElementById('oracle-actions').classList.remove('hidden');
                document.getElementById('oracle-actions').classList.add('flex');
                
                const grid = document.getElementById('oracle-grid');
                for(let i=0; i<4; i++) {
                    grid.innerHTML += `
                        <div class="fluent-glass movie-card p-2 flex flex-col border-transparent border-2 relative group overflow-hidden">
                            <img src="https://image.tmdb.org/t/p/w500/rAiYTfKGqDCRIIqo664sY9XZIvQ.jpg" class="rounded w-full h-full object-cover absolute inset-0 z-0">
                            <div class="absolute inset-0 bg-[#0f1115]/80 opacity-0 group-hover:opacity-100 transition-opacity z-10 flex flex-col justify-end p-3 text-center">
                                <span class="text-[#40bcf4] text-[8px] font-bold uppercase mb-1">Clássico</span>
                                <p class="text-white text-[10px] font-bold">Interstellar</p>
                            </div>
                        </div>
                    `;
                }
            }, 2000);

            let pct = 0;
            const watchInt = setInterval(() => {
                pct += 25;
                document.getElementById('load-percent').innerText = pct + '%';
                if(pct >= 100) {
                    clearInterval(watchInt);
                    document.getElementById('watchlist-loading').classList.add('hidden');
                    document.getElementById('watchlist-content').classList.remove('hidden');
                    
                    rawDatabase = {
                        "Clube da Luta (1999)": ["Max", "Prime Video"],
                        "O Poderoso Chefão (1972)": ["Paramount+", "Netflix"],
                        "Interstellar (2014)": ["Max"]
                    };
                    gerarFiltrosEWatchlist(rawDatabase);
                    document.getElementById('top-pill').classList.add('opacity-0', '-translate-y-4');
                }
            }, 800);
        }, 700);
    }
</script>
</body>
</html>
