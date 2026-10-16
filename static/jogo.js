
let salaAtual = "";
let jogadorAtual = "";
let nomeAtual = "";
let estadoAnterior = null;
let rodadaAnterior = null;
let atualizando = false;
let intervalo = null;

const CATEGORIAS_PADRAO = [
    "Nome",
    "Objeto",
    "Cor",
    "Animal",
    "Comida",
    "Cidade",
    "Profissão",
    "Minha sogra",
    "Palavra difícil"
];

async function api(url, dados = null, metodo = "POST") {
    const opcoes = {
        method: metodo,
        headers: {}
    };

    if (dados !== null) {
        opcoes.headers["Content-Type"] = "application/json";
        opcoes.body = JSON.stringify(dados);
    }

    const resposta = await fetch(url, opcoes);

    let resultado;
    try {
        resultado = await resposta.json();
    } catch {
        throw new Error("O servidor retornou uma resposta inválida.");
    }

    if (!resposta.ok || resultado.ok === false || resultado.erro) {
        throw new Error(resultado.erro || "Ocorreu um erro.");
    }

    return resultado;
}

function mostrarTela(id) {
    document.querySelectorAll(".tela").forEach(tela => {
        tela.classList.remove("ativa");
    });

    const tela = document.getElementById(id);

    if (tela) {
        tela.classList.add("ativa");
    }
}

function mensagem(id, texto) {
    const elemento = document.getElementById(id);

    if (elemento) {
        elemento.textContent = texto;
    }
}

function mostrarBotao(id, mostrar) {
    const elemento = document.getElementById(id);

    if (elemento) {
        elemento.classList.toggle("escondido", !mostrar);
    }
}

function iniciarAtualizacao() {
    if (intervalo) {
        clearInterval(intervalo);
    }

    atualizarEstado();
    intervalo = setInterval(atualizarEstado, 900);
}

async function criarSala() {
    try {
        const nome = document.getElementById("nomeMenu").value.trim();

        if (!nome) {
            mensagem("mensagemMenu", "Digite seu nome.");
            return;
        }

        const dados = await api("/api/criar", { nome });

        configurarJogador(dados);
        mostrarTela("lobby");
        iniciarAtualizacao();
    } catch (erro) {
        mensagem("mensagemMenu", erro.message);
    }
}

async function entrarSala() {
    try {
        const nome = document.getElementById("nomeMenu").value.trim();
        const codigo = document.getElementById("codigoMenu").value.trim();

        if (!nome || !codigo) {
            mensagem("mensagemMenu", "Digite seu nome e o código da sala.");
            return;
        }

        const dados = await api("/api/entrar", {
            nome,
            sala: codigo
        });

        configurarJogador(dados);
        mostrarTela("lobby");
        iniciarAtualizacao();
    } catch (erro) {
        mensagem("mensagemMenu", erro.message);
    }
}

function configurarJogador(dados) {
    salaAtual = dados.sala;
    jogadorAtual = dados.jogador;
    nomeAtual = dados.nome;

    estadoAnterior = null;
    rodadaAnterior = null;

    const codigoSala = document.getElementById("codigoSala");

    if (codigoSala) {
        codigoSala.textContent = salaAtual;
    }

    const opcoesHost = document.getElementById("opcoesHost");

    if (opcoesHost) {
        opcoesHost.style.display =
            jogadorAtual === "p1" ? "block" : "none";
    }

    criarCategorias();
}

function criarCategorias() {
    const container = document.getElementById("categorias");

    if (!container) {
        return;
    }

    container.innerHTML = "";

    CATEGORIAS_PADRAO.forEach((categoria, indice) => {
        const label = document.createElement("label");
        const checkbox = document.createElement("input");

        checkbox.type = "checkbox";
        checkbox.value = categoria;
        checkbox.checked = true;
        checkbox.id = `categoria${indice}`;

        label.appendChild(checkbox);
        label.appendChild(document.createTextNode(" " + categoria));

        container.appendChild(label);
    });
}

async function iniciarJogo() {
    try {
        const categorias = Array.from(
            document.querySelectorAll("#categorias input:checked")
        ).map(input => input.value);

        const campoRodadas = document.getElementById("rodadas");
        const rodadas = campoRodadas
            ? Number(campoRodadas.value)
            : 5;

        await api("/api/iniciar", {
            sala: salaAtual,
            jogador: jogadorAtual,
            categorias,
            rodadas
        });

        mensagem("mensagemLobby", "");
        await atualizarEstado();
    } catch (erro) {
        mensagem("mensagemLobby", erro.message);
    }
}

async function atualizarEstado() {
    if (!salaAtual || atualizando) {
        return;
    }

    atualizando = true;

    try {
        const estado = await api(
            `/api/estado/${encodeURIComponent(salaAtual)}?jogador=${encodeURIComponent(jogadorAtual)}`,
            null,
            "GET"
        );

        if (
            rodadaAnterior !== null &&
            estado.rodada !== rodadaAnterior
        ) {
            const campoResposta = document.getElementById("resposta");

            if (campoResposta) {
                campoResposta.value = "";
            }

            mensagem("mensagemJogo", "");
        }

        rodadaAnterior = estado.rodada;
        estadoAnterior = estado;

        if (estado.status === "lobby") {
            mostrarTela("lobby");
            renderizarLobby(estado);
        } else if (estado.status === "jogando") {
            mostrarTela("jogo");
            renderizarJogo(estado);
        } else if (estado.status === "finalizada") {
            mostrarTela("final");
            renderizarFinal(estado);
        }
    } catch (erro) {
        console.error("Erro ao atualizar:", erro);
    } finally {
        atualizando = false;
    }
}

function renderizarLobby(estado) {
    const lista = document.getElementById("listaLobby");

    if (lista) {
        lista.innerHTML = "";

        estado.jogadores.forEach(jogador => {
            const item = document.createElement("p");
            item.textContent = `👤 ${jogador.nome}`;
            lista.appendChild(item);
        });
    }

    if (estado.jogadores.length < 2) {
        mensagem("mensagemLobby", "Aguardando o segundo jogador...");
    } else {
        mensagem("mensagemLobby", "Os dois jogadores estão na sala!");
    }

    const opcoesHost = document.getElementById("opcoesHost");

    if (opcoesHost) {
        opcoesHost.style.display =
            estado.sou_host ? "block" : "none";
    }
}

function renderizarJogo(estado) {
    const rodadaAtual = document.getElementById("rodadaAtual");
    const totalRodadas = document.getElementById("totalRodadas");
    const respostasRecebidas = document.getElementById("respostasRecebidas");
    const categoriaAtual = document.getElementById("categoriaAtual");
    const letraAtual = document.getElementById("letraAtual");
    const campoResposta = document.getElementById("resposta");

    if (rodadaAtual) rodadaAtual.textContent = estado.rodada;
    if (totalRodadas) totalRodadas.textContent = estado.total_rodadas;
    if (respostasRecebidas) {
        respostasRecebidas.textContent = estado.respostas_recebidas;
    }
    if (categoriaAtual) categoriaAtual.textContent = estado.categoria;
    if (letraAtual) letraAtual.textContent = estado.letra;

    const minhaResposta = estado.minha_resposta || "";
    const respondi = minhaResposta !== "" || estado.desisti;
    const fechado = estado.rodada_fechada;

    if (campoResposta) {
        if (minhaResposta) {
            campoResposta.value = minhaResposta;
        }

        campoResposta.disabled = fechado || estado.desisti;
    }

    mostrarBotao("botaoResponder", !fechado && !respondi);
    mostrarBotao(
        "botaoCorrigir",
        !fechado && respondi && !estado.desisti
    );
    mostrarBotao("botaoDesistir", !fechado && !respondi);
    mostrarBotao(
        "botaoProxima",
        fechado && estado.sou_host && estado.status === "jogando"
    );

    if (estado.desisti) {
        mensagem(
            "mensagemJogo",
            "Você desistiu desta rodada. Na próxima, joga normalmente!"
        );
    } else if (respondi && !fechado) {
        mensagem(
            "mensagemJogo",
            "Resposta enviada. Aguardando o outro jogador..."
        );
    } else if (!respondi) {
        mensagem("mensagemJogo", "");
    }

    renderizarPlacar(estado.jogadores);
    renderizarResultadoRodada(estado);
}

function renderizarPlacar(jogadores) {
    const placar = document.getElementById("placar");

    if (!placar) {
        return;
    }

    placar.innerHTML = "";

    const titulo = document.createElement("h3");
    titulo.textContent = "🏆 Placar";
    placar.appendChild(titulo);

    jogadores
        .slice()
        .sort((a, b) => b.pontos - a.pontos)
        .forEach(jogador => {
            const linha = document.createElement("p");
            linha.textContent =
                `${jogador.nome}: ${jogador.pontos} pontos`;

            placar.appendChild(linha);
        });
}

function renderizarResultadoRodada(estado) {
    const resultado = document.getElementById("resultadoRodada");

    if (!resultado) {
        return;
    }

    resultado.innerHTML = "";

    if (!estado.rodada_fechada) {
        return;
    }

    Object.entries(estado.resultado || {}).forEach(([id, item]) => {
        const linha = document.createElement("p");

        const jogador = estado.jogadores.find(p => p.id === id);
        const nome = jogador ? jogador.nome : id;

        if (item.desistiu) {
            linha.textContent =
                `${nome}: desistiu da rodada (0 pontos)`;
        } else {
            linha.textContent =
                `${nome}: ${item.resposta} — ` +
                `${item.correta ? "válida" : "inválida"} ` +
                `(+${item.pontos_ganhos || 0} pontos)`;
        }

        resultado.appendChild(linha);
    });

    if (!estado.sou_host && estado.status !== "finalizada") {
        const aviso = document.createElement("p");
        aviso.textContent =
            "Aguardando o anfitrião iniciar a próxima rodada...";
        resultado.appendChild(aviso);
    }
}

async function responder() {
    try {
        const campo = document.getElementById("resposta");
        const resposta = campo.value.trim();

        if (!resposta) {
            mensagem("mensagemJogo", "Digite uma resposta.");
            return;
        }

        const resultado = await api("/api/responder", {
            sala: salaAtual,
            jogador: jogadorAtual,
            resposta
        });

        mensagem(
            "mensagemJogo",
            resultado.correta
                ? "Resposta enviada! A palavra começa com a letra certa."
                : "Resposta enviada, mas a palavra não começa com a letra indicada."
        );

        await atualizarEstado();
    } catch (erro) {
        mensagem("mensagemJogo", erro.message);
    }
}

async function corrigirPalavra() {
    try {
        const resposta = document.getElementById("resposta").value.trim();

        if (!resposta) {
            mensagem("mensagemJogo", "Digite a palavra corrigida.");
            return;
        }

        await api("/api/corrigir", {
            sala: salaAtual,
            jogador: jogadorAtual,
            resposta
        });

        mensagem("mensagemJogo", "Palavra corrigida!");
        await atualizarEstado();
    } catch (erro) {
        mensagem("mensagemJogo", erro.message);
    }
}

async function desistirRodada() {
    if (
        !window.confirm(
            "Deseja desistir somente desta rodada? Você continuará na próxima."
        )
    ) {
        return;
    }

    try {
        await api("/api/desistir", {
            sala: salaAtual,
            jogador: jogadorAtual
        });

        const campo = document.getElementById("resposta");

        if (campo) {
            campo.value = "";
        }

        mensagem(
            "mensagemJogo",
            "Você desistiu desta rodada. Continuará jogando na próxima!"
        );

        await atualizarEstado();
    } catch (erro) {
        mensagem("mensagemJogo", erro.message);
    }
}

async function proximaRodada() {
    try {
        const resultado = await api("/api/proxima", {
            sala: salaAtual,
            jogador: jogadorAtual
        });

        if (resultado.fim) {
            await atualizarEstado();
            return;
        }

        const campo = document.getElementById("resposta");

        if (campo) {
            campo.value = "";
        }

        mensagem("mensagemJogo", "");
        await atualizarEstado();
    } catch (erro) {
        mensagem("mensagemJogo", erro.message);
    }
}

function renderizarFinal(estado) {
    renderizarPlacar(estado.jogadores);

    const container = document.getElementById("resultadoFinal");

    if (!container) {
        return;
    }

    container.innerHTML = "";

    const jogadores = estado.jogadores
        .slice()
        .sort((a, b) => b.pontos - a.pontos);

    jogadores.forEach((jogador, indice) => {
        const linha = document.createElement("p");
        linha.textContent =
            `${indice + 1}º — ${jogador.nome}: ${jogador.pontos} pontos`;
        container.appendChild(linha);
    });

    if (
        jogadores.length >= 2 &&
        jogadores[0].pontos === jogadores[1].pontos
    ) {
        const empate = document.createElement("h3");
        empate.textContent = "🤝 Empate!";
        container.appendChild(empate);
    } else if (jogadores.length > 0) {
        const vencedor = document.createElement("h3");
        vencedor.textContent = `🏆 Vencedor: ${jogadores[0].nome}`;
        container.appendChild(vencedor);
    }
}

function voltarMenu() {
    if (intervalo) {
        clearInterval(intervalo);
    }

    intervalo = null;
    salaAtual = "";
    jogadorAtual = "";
    nomeAtual = "";
    estadoAnterior = null;
    rodadaAnterior = null;

    const nome = document.getElementById("nomeMenu");
    const codigo = document.getElementById("codigoMenu");

    if (nome) nome.value = "";
    if (codigo) codigo.value = "";

    mensagem("mensagemMenu", "");
    mostrarTela("menu");
}
