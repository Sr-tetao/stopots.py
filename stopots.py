
from flask import Flask, render_template, request, jsonify
import random
import string
import unicodedata
from threading import RLock

app = Flask(__name__)

salas = {}
trava = RLock()

LETRAS = list("ABCDEFGHIJKLMNOPRST")


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


def rodada_fechada(sala):
    return len(sala["respostas"]) >= 2


def fechar_rodada(sala):
    if not rodada_fechada(sala) or sala["resultado"]:
        return

    validas = [
        item for item in sala["respostas"].values()
        if item["correta"] and not item.get("desistiu", False)
    ]

    iguais = (
        len(validas) == 2
        and normalizar(validas[0]["resposta"])
        == normalizar(validas[1]["resposta"])
    )

    sala["resultado"] = {}

    for jogador_id, item in sala["respostas"].items():
        pontos = 0

        if item["correta"] and not item.get("desistiu", False):
            pontos = 5 if iguais else 10
            sala["jogadores"][jogador_id]["pontos"] += pontos

        sala["resultado"][jogador_id] = {
            "resposta": item["resposta"],
            "correta": item["correta"],
            "desistiu": item.get("desistiu", False),
            "pontos_ganhos": pontos
        }


def obter_jogador(sala, jogador_id):
    if not jogador_id or jogador_id not in sala["jogadores"]:
        return None
    return sala["jogadores"][jogador_id]


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
            "jogadores": {
                jogador_id: {
                    "nome": nome,
                    "pontos": 0
                }
            },
            "host": jogador_id,
            "iniciada": False,
            "letra": "",
            "numero_rodada": 0,
            "respostas": {},
            "resultado": {}
        }

    return jsonify({
        "codigo": codigo,
        "jogador_id": jogador_id,
        "mensagem": "Sala criada!"
    })


@app.route("/api/entrar", methods=["POST"])
def entrar_sala():
    dados = request.get_json(silent=True) or {}
    codigo = str(dados.get("codigo", "")).strip().upper()
    nome = str(dados.get("nome", "")).strip()

    if not codigo or not nome:
        return jsonify({"erro": "Informe o código e seu nome."}), 400

    with trava:
        sala = salas.get(codigo)

        if sala is None:
            return jsonify({"erro": "Sala não encontrada."}), 404

        if sala["iniciada"]:
            return jsonify({"erro": "A partida já começou."}), 400

        if len(sala["jogadores"]) >= 2:
            return jsonify({"erro": "A sala está cheia."}), 400

        jogador_id = "p2"
        sala["jogadores"][jogador_id] = {
            "nome": nome,
            "pontos": 0
        }

    return jsonify({
        "codigo": codigo,
        "jogador_id": jogador_id,
        "mensagem": "Você entrou na sala!"
    })


@app.route("/api/estado/<codigo>", methods=["GET"])
def estado(codigo):
    codigo = codigo.strip().upper()
    jogador_id = request.args.get("jogador_id")

    with trava:
        sala = salas.get(codigo)

        if sala is None:
            return jsonify({"erro": "Sala não encontrada."}), 404

        jogador = obter_jogador(sala, jogador_id)

        if jogador is None:
            return jsonify({"erro": "Jogador inválido."}), 400

        minha = sala["respostas"].get(jogador_id, {})
        resultado = sala["resultado"]

        return jsonify({
            "codigo": codigo,
            "jogador_id": jogador_id,
            "jogadores": sala["jogadores"],
            "host": sala["host"],
            "sou_host": jogador_id == sala["host"],
            "iniciada": sala["iniciada"],
            "letra": sala["letra"],
            "numero_rodada": sala["numero_rodada"],
            "minha_resposta": minha.get("resposta", ""),
            "desisti": minha.get("desistiu", False),
            "respostas_recebidas": len(sala["respostas"]),
            "rodada_fechada": rodada_fechada(sala),
            "resultado": resultado,
            "pontos": jogador["pontos"]
        })


@app.route("/api/iniciar", methods=["POST"])
def iniciar():
    dados = request.get_json(silent=True) or {}
    codigo = str(dados.get("codigo", "")).strip().upper()
    jogador_id = dados.get("jogador_id")

    with trava:
        sala = salas.get(codigo)

        if sala is None:
            return jsonify({"erro": "Sala não encontrada."}), 404

        if jogador_id != sala["host"]:
            return jsonify({"erro": "Somente o criador pode iniciar."}), 403

        if len(sala["jogadores"]) < 2:
            return jsonify({"erro": "Espere o segundo jogador entrar."}), 400

        sala["iniciada"] = True
        sala["numero_rodada"] = 1
        sala["letra"] = random.choice(LETRAS)
        sala["respostas"] = {}
        sala["resultado"] = {}

    return jsonify({"mensagem": "Partida iniciada!"})


@app.route("/api/responder", methods=["POST"])
def responder():
    dados = request.get_json(silent=True) or {}
    codigo = str(dados.get("codigo", "")).strip().upper()
    jogador_id = dados.get("jogador_id")
    resposta = str(dados.get("resposta", "")).strip()

    if not resposta:
        return jsonify({"erro": "Digite uma palavra."}), 400

    with trava:
        sala = salas.get(codigo)

        if sala is None:
            return jsonify({"erro": "Sala não encontrada."}), 404

        if not sala["iniciada"]:
            return jsonify({"erro": "A partida ainda não começou."}), 400

        if jogador_id not in sala["jogadores"]:
            return jsonify({"erro": "Jogador inválido."}), 400

        if rodada_fechada(sala):
            return jsonify({"erro": "A rodada já terminou."}), 400

        if jogador_id in sala["respostas"]:
            return jsonify({"erro": "Você já respondeu nesta rodada."}), 400

        correta = normalizar(resposta).startswith(
            normalizar(sala["letra"])
        )

        sala["respostas"][jogador_id] = {
            "resposta": resposta,
            "correta": correta,
            "desistiu": False
        }

        fechar_rodada(sala)

    return jsonify({
        "mensagem": "Resposta registrada.",
        "correta": correta
    })


@app.route("/api/corrigir", methods=["POST"])
def corrigir():
    dados = request.get_json(silent=True) or {}
    codigo = str(dados.get("codigo", "")).strip().upper()
    jogador_id = dados.get("jogador_id")
    resposta = str(dados.get("resposta", "")).strip()

    if not resposta:
        return jsonify({"erro": "Digite a palavra corrigida."}), 400

    with trava:
        sala = salas.get(codigo)

        if sala is None:
            return jsonify({"erro": "Sala não encontrada."}), 404

        if jogador_id not in sala["jogadores"]:
            return jsonify({"erro": "Jogador inválido."}), 400

        if rodada_fechada(sala) or sala["resultado"]:
            return jsonify({"erro": "A rodada já terminou."}), 400

        if jogador_id not in sala["respostas"]:
            return jsonify({"erro": "Responda primeiro para corrigir."}), 400

        item = sala["respostas"][jogador_id]

        if item.get("desistiu", False):
            return jsonify({"erro": "Você desistiu desta rodada."}), 400

        item["resposta"] = resposta
        item["correta"] = normalizar(resposta).startswith(
            normalizar(sala["letra"])
        )

        fechar_rodada(sala)

    return jsonify({"mensagem": "Palavra corrigida."})


@app.route("/api/desistir", methods=["POST"])
def desistir():
    dados = request.get_json(silent=True) or {}
    codigo = str(dados.get("codigo", "")).strip().upper()
    jogador_id = dados.get("jogador_id")

    with trava:
        sala = salas.get(codigo)

        if sala is None:
            return jsonify({"erro": "Sala não encontrada."}), 404

        if jogador_id not in sala["jogadores"]:
            return jsonify({"erro": "Jogador inválido."}), 400

        if not sala["iniciada"]:
            return jsonify({"erro": "A partida ainda não começou."}), 400

        if rodada_fechada(sala):
            return jsonify({"erro": "A rodada já terminou."}), 400

        if jogador_id in sala["respostas"]:
            return jsonify({"erro": "Você já respondeu ou desistiu."}), 400

        sala["respostas"][jogador_id] = {
            "resposta": "",
            "correta": False,
            "desistiu": True
        }

        fechar_rodada(sala)

    return jsonify({"mensagem": "Você desistiu desta rodada."})


@app.route("/api/proxima", methods=["POST"])
def proxima():
    dados = request.get_json(silent=True) or {}
    codigo = str(dados.get("codigo", "")).strip().upper()
    jogador_id = dados.get("jogador_id")

    with trava:
        sala = salas.get(codigo)

        if sala is None:
            return jsonify({"erro": "Sala não encontrada."}), 404

        if jogador_id != sala["host"]:
            return jsonify({"erro": "Somente o criador pode avançar."}), 403

        if not sala["resultado"]:
            return jsonify({"erro": "Aguarde o fim da rodada."}), 400

        sala["numero_rodada"] += 1
        sala["letra"] = random.choice(LETRAS)
        sala["respostas"] = {}
        sala["resultado"] = {}

    return jsonify({"mensagem": "Próxima rodada!"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
