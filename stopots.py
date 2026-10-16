from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

def fechar_rodada(sala):
    if len(sala["respostas"]) < 2 or sala["resultado"]:
        return

    respostas_validas = [
        item for item in sala["respostas"].values()
        if item["correta"] and not item.get("desistiu", False)
    ]

    palavras_iguais = (
        len(respostas_validas) == 2
        and normalizar(respostas_validas[0]["resposta"])
        == normalizar(respostas_validas[1]["resposta"])
    )

    sala["resultado"] = {}

    for jogador_id, item in sala["respostas"].items():
        pontos = 0

        if item["correta"] and not item.get("desistiu", False):
            pontos = 5 if palavras_iguais else 10
            sala["jogadores"][jogador_id]["pontos"] += pontos

        sala["resultado"][jogador_id] = {
            "resposta": item["resposta"],
            "correta": item["correta"],
            "desistiu": item.get("desistiu", False),
            "pontos_ganhos": pontos
        }
