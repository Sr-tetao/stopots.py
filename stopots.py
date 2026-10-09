
from flask import Flask, render_template, request, jsonify
import random
import string
import threading
import unicodedata

app = Flask(__name__)

# Salas guardadas na memória do servidor.
# Atenção: as salas são reiniciadas quando o serviço reinicia.
salas = {}
trava = threading.RLock()

LETRAS = "ABCDEFGHIJKLMNOPRSTUV"
CATEGORIAS_PADRAO = [
    "Nome", "Objeto", "Cor", "Animal", "Comida",
    "Cidade", "Profissão", "Minha sogra", "Palavra difícil"
]


def normalizar(texto):
    texto = unicodedata.normalize("NFD", texto.strip().lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def gerar_codigo():
    while True:
        codigo = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
        if codigo not in salas:
            return codigo


def procurar_sala(codigo):
    return salas.get(str(codigo).upper())


def procurar_jogador(sala, jogador_id):
    if jogador_id not in ("p1", "p2"):
        return None
    return sala["jogadores"].get(jogador_id)


def dados_jogadores(sala):
    return [
        {
            "id": jogador_id,
            "nome": jogador["nome"],
            "pontos": jogador["pontos"]
        }
        for jogador_id, jogador in sala["jogadores"].items()
    ]


def preparar_rodada(sala):
    sala["respostas"] = {}
    sala["resultado"] = {}
    sala["categoria"] = random.choice(sala["categorias"])
    sala["letra"] = random.choice(LETRAS)


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/api/criar", methods=["POST"])
def criar_sala():
    dados = request.get_json(silent=True) or {}
    nome = str(dados.get("nome", "")).strip()[:20]

    if not nome:
        return jsonify(ok=False, erro="Digite seu nome."), 400

    with trava:
        codigo = gerar_codigo()
        salas[codigo] = {
            "status": "lobby",
            "jogadores": {
                "p1": {"nome": nome, "pontos": 0}
            },
            "categorias": CATEGORIAS_PADRAO.copy(),
            "rodada": 0,
            "total_rodadas": 5,
            "categoria": "",
            "letra": "",
            "respostas": {},
            "resultado": {}
        }

    return jsonify(ok=True, sala=codigo, jogador="p1", nome=nome)


@app.route("/api/entrar", methods=["POST"])
def entrar_sala():
    dados = request.get_json(silent=True) or {}
    nome = str(dados.get("nome", "")).strip()[:20]
    codigo = str(dados.get("sala", "")).strip().upper()

    if not nome:
        return jsonify(ok=False, erro="Digite seu nome."), 400

    with trava:
        sala = procurar_sala(codigo)

        if sala is None:
            return jsonify(ok=False, erro="Sala não encontrada."), 404

        if sala["status"] != "lobby":
            return jsonify(ok=False, erro="Esta partida já começou."), 400

        if len(sala["jogadores"]) >= 2:
            return jsonify(ok=False, erro="A sala já está cheia."), 400

        sala["jogadores"]["p2"] = {"nome": nome, "pontos": 0}

    return jsonify(ok=True, sala=codigo, jogador="p2", nome=nome)


@app.route("/api/estado/<codigo>", methods=["GET"])
def estado(codigo):
    jogador_id = request.args.get("jogador", "")
    with trava:
        sala = procurar_sala(codigo)

        if sala is None:
            return jsonify(ok=False, erro="Sala não encontrada."), 404

        jogador = procurar_jogador(sala, jogador_id)
        if jogador is None:
            return jsonify(ok=False, erro="Jogador inválido."), 400

        minha_resposta = sala["respostas"].get(jogador_id)
        minha_resposta_ok = (
            minha_resposta is not None
            and minha_resposta["correta"]
        )

        return jsonify(
            ok=True,
            status=sala["status"],
            jogadores=dados_jogadores(sala),
            respostas_recebidas=len(sala["respostas"]),
            rodada=sala["rodada"],
            total_rodadas=sala["total_rodadas"],
            categoria=sala["categoria"],
            letra=sala["letra"],
            minha_resposta=minha_resposta["resposta"] if minha_resposta else "",
            minha_resposta_ok=minha_resposta_ok,
            resultado=sala["resultado"]
        )


@app.route("/api/iniciar", methods=["POST"])
def iniciar():
    dados = request.get_json(silent=True) or {}
    codigo = str(dados.get("sala", "")).upper()
    jogador_id = str(dados.get("jogador", ""))
    categorias = dados.get("categorias", [])
    rodadas = dados.get("rodadas", 5)

    if not isinstance(categorias, list):
        return jsonify(ok=False, erro="Lista de categorias inválida."), 400

    categorias = [
        str(c).strip()[:40]
        for c in categorias
        if str(c).strip()
    ][:20]

    if not categorias:
        return jsonify(ok=False, erro="Escolha pelo menos uma categoria."), 400

    try:
        rodadas = int(rodadas)
    except (ValueError, TypeError):
        rodadas = 5

    rodadas = max(1, min(rodadas, 20))

    with trava:
        sala = procurar_sala(codigo)
        if sala is None:
            return jsonify(ok=False, erro="Sala não encontrada."), 404

        if jogador_id != "p1":
            return jsonify(ok=False, erro="Somente quem criou a sala pode iniciar."), 403

        if len(sala["jogadores"]) != 2:
            return jsonify(ok=False, erro="Aguarde o segundo jogador."), 400

        if sala["status"] != "lobby":
            return jsonify(ok=False, erro="A partida já começou."), 400

        sala["categorias"] = categorias
        sala["total_rodadas"] = rodadas
        sala["rodada"] = 1
        sala["status"] = "jogando"
        preparar_rodada(sala)

    return jsonify(ok=True)


@app.route("/api/responder", methods=["POST"])
def responder():
    dados = request.get_json(silent=True) or {}
    codigo = str(dados.get("sala", "")).upper()
    jogador_id = str(dados.get("jogador", ""))
    resposta = str(dados.get("resposta", "")).strip()[:100]

    if not resposta:
        return jsonify(ok=False, erro="Digite uma resposta."), 400

    with trava:
        sala = procurar_sala(codigo)
        if sala is None:
            return jsonify(ok=False, erro="Sala não encontrada."), 404

        if procurar_jogador(sala, jogador_id) is None:
            return jsonify(ok=False, erro="Jogador inválido."), 400

        if sala["status"] != "jogando":
            return jsonify(ok=False, erro="A partida não está em andamento."), 400

        if jogador_id in sala["respostas"]:
            return jsonify(ok=False, erro="Você já respondeu nesta rodada."), 400

        correta = normalizar(resposta).startswith(normalizar(sala["letra"]))
        sala["respostas"][jogador_id] = {
            "resposta": resposta,
            "correta": correta
        }

        if correta:
            sala["jogadores"][jogador_id]["pontos"] += 10

        # Quando os dois respondem, preparar o resultado da rodada.
        if len(sala["respostas"]) == 2:
            sala["resultado"] = {
                pid: {
                    "resposta": item["resposta"],
                    "correta": item["correta"]
                }
                for pid, item in sala["respostas"].items()
            }

    return jsonify(ok=True, correta=correta)


@app.route("/api/proxima", methods=["POST"])
def proxima():
    dados = request.get_json(silent=True) or {}
    codigo = str(dados.get("sala", "")).upper()
    jogador_id = str(dados.get("jogador", ""))

    with trava:
        sala = procurar_sala(codigo)
        if sala is None:
            return jsonify(ok=False, erro="Sala não encontrada."), 404

        if jogador_id != "p1":
            return jsonify(ok=False, erro="Somente quem criou a sala pode avançar."), 403

        if sala["status"] != "jogando":
            return jsonify(ok=False, erro="Não há rodada em andamento."), 400

        if len(sala["respostas"]) < 2:
            return jsonify(ok=False, erro="Espere os dois jogadores responderem."), 400

        if sala["rodada"] >= sala["total_rodadas"]:
            sala["status"] = "finalizada"
            return jsonify(ok=True, fim=True)

        sala["rodada"] += 1
        preparar_rodada(sala)
        if respostas == respostas:
            resultado = + 5
    return jsonify(ok=True, fim=False)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
