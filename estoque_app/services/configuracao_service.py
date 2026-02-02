"""
Service para configurações operacionais (Fase 3).
Collection: configuracoes_operacao.
Divisão de lucro padrão: cliente / sócio.
"""
from typing import Dict, Any
from core.database import get_database


def get_configuracoes_collection():
    """Retorna a collection configuracoes_operacao."""
    return get_database()["configuracoes_operacao"]


def obter_divisao_lucro_padrao() -> Dict[str, Any]:
    """
    Retorna a divisão de lucro padrão (cliente_percentual, socio_percentual).
    Se não existir documento, retorna 70/30.
    """
    coll = get_configuracoes_collection()
    doc = coll.find_one({})
    if not doc or "divisao_lucro_padrao" not in doc:
        return {"cliente_percentual": 70, "socio_percentual": 30}
    d = doc["divisao_lucro_padrao"]
    return {
        "cliente_percentual": int(d.get("cliente_percentual", 70)),
        "socio_percentual": int(d.get("socio_percentual", 30)),
    }


def salvar_divisao_lucro_padrao(cliente_percentual: int, socio_percentual: int) -> None:
    """Salva ou atualiza a divisão de lucro padrão (um único documento)."""
    if cliente_percentual + socio_percentual != 100:
        raise ValueError("Soma dos percentuais deve ser 100.")
    coll = get_configuracoes_collection()
    doc = coll.find_one({})
    payload = {
        "divisao_lucro_padrao": {
            "cliente_percentual": cliente_percentual,
            "socio_percentual": socio_percentual,
        }
    }
    if doc:
        coll.update_one({}, {"$set": payload})
    else:
        coll.insert_one(payload)
