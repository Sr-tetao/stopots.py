let salaAtual = "";
let jogadorAtual = "";
let nomeAtual = "";

let intervalo = null;

let ultimaRodada = 0;


const CATEGORIAS = [
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


function mostrarTela(id) {

    document
        .querySelectorAll(".tela")
        .forEach(tela => {
            tela.classList.remove("ativa");
        });

    document
        .getElementById(id)
        .classList.add("ativa");
}


function mensagem(id, texto) {

    const elemento =
        document.getElementById(id);

    if (elemento) {
        elemento.textContent = texto;
    }
}


function carregarCategorias() {

    const container =
        document.getElementById("categorias");

    container.innerHTML = "";

    CATEGORIAS.forEach(
        (categoria, index) => {

            const div =
                document.createElement("div");

            div.className =
                "categoria-check";

            div.innerHTML = `
                <label>
                    <input
                        type="checkbox"
                        value="${categoria}"
                        checked
                    >
                    ${categoria}
                </label>
            `;

            container.appendChild(div);
        }
    );
}


async function criarSala() {

    const nome =
        document
            .getElementById("nomeMenu")
            .value
            .trim();

    if (!nome) {

        mensagem(
            "mensagemMenu",
            "Digite seu nome primeiro."
        );

        return;
    }


    try {

        const resposta =
            await fetch(
                "/api/criar",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        nome: nome
                    })
                }
            );


        const dados =
            await resposta.json();


        if (!dados.ok) {

            mensagem(
                "mensagemMenu",
                dados.erro
            );

            return;
        }


        salaAtual = dados.sala;
        jogadorAtual = dados.jogador;
        nomeAtual = dados.nome;


        document
            .getElementById("codigoSala")
            .textContent = salaAtual;


        carregarCategorias();

        document
            .getElementById("opcoesHost")
            .style.display = "block";


        mensagem(
            "mensagemLobby",
            "Aguardando o segundo jogador..."
        );


        mostrarTela("lobby");

        iniciarAtualizacao();

    } catch (erro) {

        mensagem(
            "mensagemMenu",
            "Erro ao conectar ao servidor."
        );
    }
}


async function entrarSala() {

    const nome =
        document
            .getElementById("nomeMenu")
            .value
            .trim();

    const codigo =
        document
            .getElementById("codigoMenu")
            .value
            .trim()
            .toUpperCase();


    if (!nome) {

        mensagem(
            "mensagemMenu",
            "Digite seu nome."
        );

        return;
    }


    if (!codigo) {

        mensagem(
            "mensagemMenu",
            "Digite o código da sala."
        );

        return;
    }


    try {

        const resposta =
            await fetch(
                "/api/entrar",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({
                        nome: nome,
                        sala: codigo
                    })
                }
            );


        const dados =
            await resposta.json();


        if (!dados.ok) {

            mensagem(
                "mensagemMenu",
                dados.erro
            );

            return;
        }


        salaAtual = dados.sala;
        jogadorAtual = dados.jogador;
        nomeAtual = dados.nome;


        document
            .getElementById("codigoSala")
            .textContent = salaAtual;


        document
            .getElementById("opcoesHost")
            .style.display = "none";


        mostrarTela("lobby");

        iniciarAtualizacao();

    } catch (erro) {

        mensagem(
            "mensagemMenu",
            "Erro ao conectar ao servidor."
        );
    }
}


function iniciarAtualizacao() {

    if (intervalo) {
        clearInterval(intervalo);
    }


    atualizarEstado();

    intervalo =
        setInterval(
            atualizarEstado,
            900
        );
}


async function atualizarEstado() {

    if (!salaAtual) {
        return;
    }


    try {

        const resposta =
            await fetch(
                `/api/estado/${salaAtual}?jogador=${jogadorAtual}`
            );


        const dados =
            await resposta.json();


        if (!dados.ok) {
            return;
        }


        atualizarJogadores(
            dados.jogadores
        );


        atualizarPlacar(
            dados.jogadores
        );


        document
            .getElementById(
                "respostasRecebidas"
            )
            .textContent =
                dados.respostas_recebidas;


        if (
            dados.status === "lobby"
        ) {

            mostrarTela("lobby");

            return;
        }


        if (
            dados.status === "jogando"
        ) {

            mostrarTela("jogo");

            atualizarJogo(dados);

            return;
        }


        if (
            dados.status === "finalizada"
        ) {

            mostrarTela("final");

            atualizarFinal(dados);

            return;
        }

    } catch (erro) {

        console.log(
            "Erro ao atualizar:",
            erro
        );
    }
}


function atualizarJogadores(
    jogadores
) {

    const container =
        document.getElementById(
            "listaLobby"
        );

    container.innerHTML = "";


    jogadores.forEach(
        jogador => {

            const div =
                document.createElement("div");

            div.className =
                "jogador";


            div.innerHTML = `
                <strong>
                    ${escapeHtml(jogador.nome)}
                </strong>

                <span>
                    ${jogador.id === "p1"
                        ? "👑 Criador"
                        : "🎮 Jogador"
                    }
                </span>
            `;


            container.appendChild(div);
        }
    );


    if (
        jogadores.length < 2
    ) {

        mensagem(
            "mensagemLobby",
            "Aguardando o segundo jogador..."
        );

    } else {

        mensagem(
            "mensagemLobby",
            "Os dois jogadores estão na sala!"
        );
    }
}


function atualizarJogo(dados) {

    document
        .getElementById("rodadaAtual")
        .textContent =
            dados.rodada;


    document
        .getElementById("totalRodadas")
        .textContent =
            dados.total_rodadas;


    document
        .getElementById("categoriaAtual")
        .textContent =
            dados.categoria;


    document
        .getElementById("letraAtual")
        .textContent =
            dados.letra;


    if (
        ultimaRodada !== dados.rodada
    ) {

        ultimaRodada =
            dados.rodada;

        const resposta =
            document.getElementById(
                "resposta"
            );

        resposta.value = "";

        resposta.disabled = false;


        document
            .getElementById(
                "botaoResponder"
            )
            .disabled = false;


        document
            .getElementById(
                "botaoProxima"
            )
            .classList.add(
                "escondido"
            );


        mensagem(
            "mensagemJogo",
            ""
        );


        document
            .getElementById(
                "resultadoRodada"
            )
            .innerHTML = "";
    }


    if (
        dados.minha_resposta
    ) {

        document
            .getElementById(
                "resposta"
            )
            .disabled = true;


        document
            .getElementById(
                "botaoResponder"
            )
            .disabled = true;


        if (
            dados.minha_resposta_ok
        ) {

            mensagem(
                "mensagemJogo",
                "✅ Resposta correta! +10 pontos."
            );

        } else {

            mensagem(
                "mensagemJogo",
                "❌ A resposta não começa com a letra correta."
            );
        }
    }


    if (
        Object.keys(
            dados.resultado || {}
        ).length > 0
    ) {

        mostrarResultadoRodada(
            dados.resultado,
            dados.jogadores
        );


        if (
            jogadorAtual === "p1"
        ) {

            document
                .getElementById(
                    "botaoProxima"
                )
                .classList.remove(
                    "escondido"
                );
        }
    }
}


function atualizarPlacar(
    jogadores
) {

    const container =
        document.getElementById(
            "placar"
        );

    container.innerHTML = "";


    jogadores.forEach(
        jogador => {

            const div =
                document.createElement("div");

            div.className =
                "placar-item";


            div.innerHTML = `
                <div>
                    ${escapeHtml(jogador.nome)}
                </div>

                <strong>
                    ${jogador.pontos}
                </strong>

                <small>
                    pontos
                </small>
            `;


            container.appendChild(div);
        }
    );
}


function mostrarResultadoRodada(
    resultado,
    jogadores
) {

    const container =
        document.getElementById(
            "resultadoRodada"
        );

    container.innerHTML =
        "<h3>Resultado da rodada</h3>";


    jogadores.forEach(
        jogador => {

            const resultadoJogador =
                resultado[jogador.id];


            if (!resultadoJogador) {
                return;
            }


            const div =
                document.createElement("div");


            div.className =
                "resultado-item " +
                (
                    resultadoJogador.correta
                        ? "correta"
                        : "incorreta"
                );


            div.innerHTML = `
                <strong>
                    ${escapeHtml(jogador.nome)}
                </strong>

                <br>

                Resposta:
                ${escapeHtml(
                    resultadoJogador.resposta
                    || "(vazio)"
                )}

                <br>

                ${
                    resultadoJogador.correta
                        ? "✅ Correta"
                        : "❌ Incorreta"
                }
            `;


            container.appendChild(div);
        }
    );
}


async function iniciarJogo() {

    const checkboxes =
        document.querySelectorAll(
            "#categorias input[type=checkbox]"
        );


    const categorias = [];


    checkboxes.forEach(
        checkbox => {

            if (checkbox.checked) {
                categorias.push(
                    checkbox.value
                );
            }
        }
    );


    if (categorias.length === 0) {

        mensagem(
            "mensagemLobby",
            "Escolha pelo menos uma categoria."
        );

        return;
    }


    const rodadas =
        Number(
            document
                .getElementById("rodadas")
                .value
        );


    try {

        const resposta =
            await fetch(
                "/api/iniciar",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        sala: salaAtual,

                        jogador:
                            jogadorAtual,

                        categorias:
                            categorias,

                        rodadas:
                            rodadas
                    })
                }
            );


        const dados =
            await resposta.json();


        if (!dados.ok) {

            mensagem(
                "mensagemLobby",
                dados.erro
            );

            return;
        }


        mensagem(
            "mensagemLobby",
            "Jogo iniciado!"
        );

        ultimaRodada = 0;

        atualizarEstado();

    } catch (erro) {

        mensagem(
            "mensagemLobby",
            "Erro ao iniciar o jogo."
        );
    }
}


async function responder() {

    const campo =
        document.getElementById(
            "resposta"
        );


    const resposta =
        campo.value.trim();


    if (!resposta) {

        mensagem(
            "mensagemJogo",
            "Digite uma resposta."
        );

        return;
    }


    try {

        const resultado =
            await fetch(
                "/api/responder",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        sala:
                            salaAtual,

                        jogador:
                            jogadorAtual,

                        resposta:
                            resposta
                    })
                }
            );


        const dados =
            await resultado.json();


        if (!dados.ok) {

            mensagem(
                "mensagemJogo",
                dados.erro
            );

            return;
        }


        campo.disabled = true;


        document
            .getElementById(
                "botaoResponder"
            )
            .disabled = true;


        if (dados.correta) {

            mensagem(
                "mensagemJogo",
                "✅ Resposta correta! +10 pontos."
            );

        } else {

            mensagem(
                "mensagemJogo",
                "❌ Resposta incorreta."
            );
        }


        atualizarEstado();

    } catch (erro) {

        mensagem(
            "mensagemJogo",
            "Erro ao enviar resposta."
        );
    }
}


async function proximaRodada() {

    try {

        const resposta =
            await fetch(
                "/api/proxima",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        sala:
                            salaAtual,

                        jogador:
                            jogadorAtual
                    })
                }
            );


        const dados =
            await resposta.json();


        if (!dados.ok) {

            mensagem(
                "mensagemJogo",
                dados.erro
            );

            return;
        }


        if (dados.fim) {

            atualizarEstado();

            return;
        }


        ultimaRodada = 0;

        atualizarEstado();

    } catch (erro) {

        mensagem(
            "mensagemJogo",
            "Erro ao avançar a rodada."
        );
    }
}


function atualizarFinal(
    dados
) {

    const container =
        document.getElementById(
            "resultadoFinal"
        );


    container.innerHTML =
        "<h3>🏆 Placar final</h3>";


    const jogadores =
        [...dados.jogadores];


    jogadores.sort(
        (a, b) =>
            b.pontos - a.pontos
    );


    jogadores.forEach(
        (jogador, index) => {

            const div =
                document.createElement("div");


            div.className =
                "resultado-item";


            if (index === 0) {
                div.classList.add(
                    "vencedor"
                );
            }


            div.innerHTML = `
                <strong>
                    ${index + 1}º —
                    ${escapeHtml(jogador.nome)}
                </strong>

                <br>

                ${jogador.pontos} pontos
            `;


            container.appendChild(div);
        }
    );
}


function voltarMenu() {

    if (intervalo) {

        clearInterval(intervalo);

        intervalo = null;
    }


    salaAtual = "";
    jogadorAtual = "";
    nomeAtual = "";

    ultimaRodada = 0;


    document
        .getElementById("nomeMenu")
        .value = "";


    document
        .getElementById("codigoMenu")
        .value = "";


    mensagem(
        "mensagemMenu",
        ""
    );


    mostrarTela("menu");
}


function escapeHtml(texto) {

    const div =
        document.createElement(
            "div"
        );

    div.textContent =
        texto;

    return div.innerHTML;
}


document.addEventListener(
    "keydown",
    function(event) {

        if (
            event.key === "Enter" &&
            document
                .getElementById("jogo")
                .classList
                .contains("ativa")
        ) {

            const botao =
                document.getElementById(
                    "botaoResponder"
                );

            if (
                !botao.disabled
            ) {

                responder();
            }
        }
    }
);


document.addEventListener(
    "DOMContentLoaded",
    function() {

        carregarCategorias();

    }
);
