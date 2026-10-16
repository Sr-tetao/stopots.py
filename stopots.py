
from flask import Flask, render_template, request, jsonify
import random
import string
import unicodedata
from threading import RLock

app = Flask(__name__)

salas = {}
trava = RLock()

CATEGORIAS_PADRAO = [
    "Nome", "Objeto", "Cor", "Animal", "Comida",
    "Cidade", "Profissão", "Minha sogra", "Palavra difícil"
]

LETRAS = list("ABCDEFGHIJKLMNOPRSTUV")


def normalizar(texto):
    texto = str(texto).strip().lower()
    texto = unicodedata.normalize("NFD", texto)
    return "".join(
        c for c in texto
        if unicodedata.category(c) != "Mn"
    )


def gerar_codigo():
    while True:
        codigo = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=5)
        )
        if codigo not in salas:
            return codigo


def obter_jogadores(sala):
    return [
        {
            "id": jogador_id,
            "nome": jogador["nome"],
            "pontos": jogador["pontos"]
        }
        for jogador_id, jogador in sala["jogadores"].items()
    ]


def rodada_fechada(sala):
    return len(sala["respostas"]) >= len(sala["jogadores"])


def fechar_rodada(sala):
    if not rodada_fechada(sala) or sala["resultado"]:
        return

    validas = [
        item for item in sala["respostas"].values()
        if item["correta"] and not item["desistiu"]
    ]

    iguais = (
        len(validas) == 2
        and normalizar(validas[0]["resposta"])
        == normalizar(validas[1]["resposta"])
    )

    sala["resultado"] = {}

    for jogador_id, item in sala["respostas"].items():
        pontos = 0

        if item["correta"] and not item["desistiu"]:
            pontos = 5 if iguais else 10
            sala["jogadores"][jogador_id]["pontos"] += pontos

        sala["resultado"][jogador_id] = {
            "resposta": item["resposta"],
            "correta": item["correta"],
            "desistiu": item["desistiu"],
            "pontos_ganhos": pontos
        }

    if sala["numero_rodada"] >= sala["total_rodadas"]:
        sala["status"] = "finalizada"


def montar_estado(sala, jogador_id):
    minha = sala["respostas"].get(jogador_id, {})
    return {
        "codigo": sala["codigo"],
        "status": sala["status"],
        "jogadores": obter_jogadores(sala),
        "rodada": sala["numero_rodada"],
        "total_rodadas": sala["total_rodadas"],
        "letra": sala["letra"],
        "categoria": sala["categoria"],
        "minha_resposta": minha.get("resposta", ""),
        "desisti": minha.get("desistiu", False),
        "respostas_recebidas": len(sala["respostas"]),
        "rodada_fechada": rodada_fechada(sala),
        "resultado": sala["resultado"],
        "sou_host": jogador_id == sala["host"]
    }


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/api/criar", methods=["POST"])
def criar_sala():
    dados = request.get_json(silent=True) or {}
    nome = str(dados.get("nome", "")).strip()

    if not nome:
        return jsonify({"erro": "Digite seu nome."}), 400

    with trava:
        codigo = gerar_codigo()
        jogador_id = "p1"

        salas[codigo] = {
            "codigo": codigo,
            "host": jogador_id,
            "jogadores": {
                jogador_id: {"nome": nome, "pontos": 0}
            },
            "status": "lobby",
            "numero_rodada": 0,
            "total_rodadas": 5,
            "categorias": CATEGORIAS_PADRAO.copy(),
            "categoria": "",
            "letra": "",
            "respostas": {},
            "resultado": {}
        }

    return jsonify({
        "sala": codigo,
        "jogador": jogador_id,
        "nome": nome
    })


@app.route("/api/entrar", methods=["POST"])
def entrar_sala():
    dados = request.get_json(silent=True) or {}
    codigo = str(dados.get("sala", "")).strip().upper()
    nome = str(dados.get("nome", "")).strip()

    if not codigo or not nome:
        return jsonify({"erro": "Informe o código e seu nome."}), 400

    with trava:
        sala = salas.get(codigo)

        if sala is None:
            return jsonify({"erro": "Sala não encontrada."}), 404

        if sala["status"] != "lobby":
            return jsonify({"erro": "A partida já começou."}), 400

        if len(sala["jogadores"]) >= 2:
            return jsonify({"erro": "A sala está cheia."}), 400

        sala["jogadores"]["p2"] = {
            "nome": nome,
            "pontos": 0
        }

    return jsonify({
        "sala": codigo,
        "jogador": "p2",
        "nome": nome
    })


@app.route("/api/estado/<codigo>", methods=["GET"])
def estado(codigo):
    jogador_id = request.args.get("jogador")

    with trava:
        sala = salas.get(codigo.upper())

        if sala is None:
            return jsonify({"erro": "Sala não encontrada."}), 404

        if jogador_id not in sala["jogadores"]:
            return jsonify({"erro": "Jogador inválido."}), 400

        return jsonify(montar_estado(sala, jogador_id))


@app.route("/api/iniciar", methods=["POST"])
def iniciar():
    dados = request.get_json(silent=True) or {}
    codigo = str(dados.get("sala", "")).upper()
    jogador_id = dados.get("jogador")
    categorias = dados.get("categorias", CATEGORIAS_PADRAO)
    rodadas = dados.get("rodadas", 5)

    with trava:
        sala = salas.get(codigo)

        if sala is None:
            return jsonify({"erro": "Sala não encontrada."}), 404

        if jogador_id != sala["host"]:
            return jsonify({"erro": "Somente o anfitrião pode iniciar."}), 403

        if len(sala["jogadores"]) < 2:
            return jsonify({"erro": "Aguarde o segundo jogador."}), 400

        if sala["status"] != "lobby":
            return jsonify({"erro": "A partida já começou."}), 400

        try:
            rodadas = int(rodadas)
        except (TypeError, ValueError):
            rodadas = 5

        if not 1 <= rodadas <= 20:
            return jsonify({"erro": "Escolha de 1 a 20 rodadas."}), 400

        if not isinstance(categorias, list):
            return jsonify({"erro": "Categorias inválidas."}), 400

        categorias = [
            str(c).strip() for c in categorias
            if str(c).strip()
        ]

        if not categorias:
            return jsonify({"erro": "Selecione pelo menos uma categoria."}), 400

        sala["categorias"] = categorias
        sala["total_rodadas"] = rodadas
        sala["numero_rodada"] = 1
        sala["letra"] = random.choice(LETRAS)
        sala["categoria"] = random.choice(categorias)
        sala["respostas"] = {}
        sala["resultado"] = {}
        sala["status"] = "jogando"

    return jsonify({"ok": True})


@app.route("/api/responder", methods=["POST"])
def responder():
    dados = request.get_json(silent=True) or {}
    codigo = str(dados.get("sala", "")).upper()
    jogador_id = dados.get("jogador")
    resposta = str(dados.get("resposta", "")).strip()

    if not resposta:
        return jsonify({"erro": "Digite uma resposta."}), 400

    with trava:
        sala = salas.get(codigo)

        if sala is None:
            return jsonify({"erro": "Sala não encontrada."}), 404

        if sala["status"] != "jogando":
            return jsonify({"erro": "A rodada não está em andamento."}), 400

        if jogador_id not in sala["jogadores"]:
            return jsonify({"erro": "Jogador inválido."}), 400

        if jogador_id in sala["respostas"]:
            return jsonify({"erro": "Você já respondeu nesta rodada."}), 400

        correta = normalizar(resposta).startswith(normalizar(sala["letra"]))

        sala["respostas"][jogador_id] = {
            "resposta": resposta,
            "correta": correta,
            "desistiu": False
        }

        fechar_rodada(sala)

    return jsonify({"ok": True, "correta": correta})


@app.route("/api/corrigir", methods=["POST"])
def corrigir():
    dados = request.get_json(silent=True) or {}
    codigo = str(dados.get("sala", "")).upper()
    jogador_id = dados.get("jogador")
    resposta = str(dados.get("resposta", "")).strip()

    if not resposta:
        return jsonify({"erro": "Digite a palavra corrigida."}), 400

    with trava:
        sala = salas.get(codigo)

        if sala is None:
            return jsonify({"erro": "Sala não encontrada."}), 404

        if sala["status"] != "jogando":
            return jsonify({"erro": "A rodada não está em andamento."}), 400

        item = sala["respostas"].get(jogador_id)

        if item is None:
            return jsonify({"erro": "Responda primeiro para corrigir."}), 400

        if rodada_fechada(sala) or item["desistiu"]:
            return jsonify({"erro": "Não é possível corrigir agora."}), 400

        item["resposta"] = resposta
        item["correta"] = normalizar(resposta).startswith(
            normalizar(sala["letra"])
        )

        fechar_rodada(sala)

    return jsonify({"ok": True})


@app.route("/api/desistir", methods=["POST"])
def desistir():
    dados = request.get_json(silent=True) or {}
    codigo = str(dados.get("sala", "")).upper()
    jogador_id = dados.get("jogador")

    with trava:
        sala = salas.get(codigo)

        if sala is None:
            return jsonify({"erro": "Sala não encontrada."}), 404

        if sala["status"] != "jogando":
            return jsonify({"erro": "A rodada não está em andamento."}), 400

        if jogador_id not in sala["jogadores"]:
            return jsonify({"erro": "Jogador inválido."}), 400

        if jogador_id in sala["respostas"]:
            return jsonify({"erro": "Você já respondeu ou desistiu."}), 400

        sala["respostas"][jogador_id] = {
            "resposta": "",
            "correta": False,
            "desistiu": True
        }

        fechar_rodada(sala)

    return jsonify({"ok": True})


@app.route("/api/proxima", methods=["POST"])
def proxima():
    dados = request.get_json(silent=True) or {}
    codigo = str(dados.get("sala", "")).upper()
    jogador_id = dados.get("jogador")

    with trava:
        sala = salas.get(codigo)

        if sala is None:
            return jsonify({"erro": "Sala não encontrada."}), 404

        if jogador_id != sala["host"]:
            return jsonify({"erro": "Somente o anfitrião pode avançar."}), 403

        if sala["status"] != "jogando" or not sala["resultado"]:
            return jsonify({"erro": "A rodada ainda não terminou."}), 400

        if sala["numero_rodada"] >= sala["total_rodadas"]:
            sala["status"] = "finalizada"
            return jsonify({"ok": True, "fim": True})

        sala["numero_rodada"] += 1
        sala["letra"] = random.choice(LETRAS)
        sala["categoria"] = random.choice(sala["categorias"])
        sala["respostas"] = {}
        sala["resultado"] = {}

    return jsonify({"ok": True, "fim": False})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
