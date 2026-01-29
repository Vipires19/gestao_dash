"""
Service para lógica de vendas.

Localização: estoque_app/services/venda_service.py

Este service contém a lógica de negócio relacionada a vendas.
Acesso direto ao MongoDB via pymongo (sem ORM).
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from core.database import get_database
from bson import ObjectId
from estoque_app.services.produto_service import ProdutoService


def get_vendas_collection():
    """
    Retorna a collection de vendas do MongoDB.
    
    Returns:
        Collection de vendas
    """
    db = get_database()
    return db["vendas"]


class VendaService:
    """
    Service para gerenciar vendas.
    
    Exemplo de uso:
        service = VendaService()
        produto = service.buscar_produto_por_codigo('PROD001')
        venda = service.registrar_venda([
            {
                'produto_id': '...',
                'codigo': 'PROD001',
                'nome': 'Produto X',
                'valor_unitario': 10.0,
                'quantidade': 2
            }
        ])
    """
    
    def __init__(self):
        self.collection = get_vendas_collection()
        self.produto_service = ProdutoService()
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """
        Cria índices necessários para otimizar queries.
        
        Índices:
        - created_at: Para ordenação e filtros por data
        """
        # Índice para created_at (ordenação)
        self.collection.create_index('created_at')
    
    def buscar_produto_por_codigo(self, codigo: str) -> Optional[Dict[str, Any]]:
        """
        Busca um produto pelo código para adicionar à venda.
        
        Args:
            codigo: Código do produto
        
        Returns:
            Dict com dados do produto ou None se não encontrado
        """
        produto = self.produto_service.buscar_produto_por_codigo(codigo)
        
        if produto:
            # Normaliza _id para id se ainda não estiver normalizado
            produto_id = produto.get('id') or str(produto.get('_id', ''))
            # Retorna apenas campos necessários para a venda
            return {
                'id': produto_id,
                'codigo': produto.get('codigo', ''),
                'nome': produto.get('nome', ''),
                'valor_unitario': produto.get('preco_venda', 0),
                'quantidade_disponivel': produto.get('quantidade', 0)
            }
        
        return None
    
    def registrar_venda(self, itens: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Registra uma nova venda e atualiza o estoque.
        
        Args:
            itens: Lista de itens da venda, cada item deve conter:
                - produto_id: ID do produto
                - codigo: Código do produto
                - nome: Nome do produto
                - valor_unitario: Valor unitário
                - quantidade: Quantidade vendida
        
        Returns:
            Dict com dados da venda criada
        
        Raises:
            ValueError: Se estoque insuficiente ou dados inválidos
        """
        if not itens or len(itens) == 0:
            raise ValueError("A venda deve conter pelo menos um item")
        
        # Debug: log dos itens recebidos
        print("=== DEBUG: Itens recebidos ===")
        print(itens)
        print("==============================")
        
        # Valida estoque antes de registrar a venda
        produtos_collection = self.produto_service.collection
        
        # Lista para armazenar produtos encontrados e validados
        produtos_validados = []
        
        for item in itens:
            produto_id_str = item.get('produto_id')
            quantidade_vendida = item.get('quantidade', 0)
            
            if not produto_id_str:
                raise ValueError(f"Produto ID é obrigatório para o item: {item.get('nome', 'Desconhecido')}")
            
            if quantidade_vendida <= 0:
                raise ValueError(f"Quantidade deve ser maior que zero para o item: {item.get('nome', 'Desconhecido')}")
            
            # Converte produto_id de string para ObjectId
            try:
                produto_id = ObjectId(produto_id_str)
            except Exception as e:
                raise ValueError(f"ID de produto inválido: {produto_id_str}")
            
            # Busca produto no banco usando _id
            produto = produtos_collection.find_one({'_id': produto_id})
            
            if not produto:
                raise ValueError(f"Produto não encontrado com ID: {produto_id_str}")
            
            quantidade_atual = produto.get('quantidade', 0)
            
            if quantidade_vendida > quantidade_atual:
                raise ValueError(
                    f"Estoque insuficiente para '{produto.get('nome', 'Produto')}'. "
                    f"Disponível: {quantidade_atual}, Solicitado: {quantidade_vendida}"
                )
            
            # Armazena produto validado
            produtos_validados.append({
                'produto_id': produto_id,  # ObjectId convertido
                'codigo': item.get('codigo', produto.get('codigo', '')),
                'nome': item.get('nome', produto.get('nome', '')),
                'valor_unitario': float(item.get('valor_unitario', produto.get('preco_venda', 0))),
                'quantidade': int(quantidade_vendida)
            })
        
        # Calcula valor total da venda
        valor_total_venda = sum(
            produto_val['valor_unitario'] * produto_val['quantidade']
            for produto_val in produtos_validados
        )
        
        # Prepara itens para salvar (com valor_total de cada item)
        itens_para_salvar = []
        for produto_val in produtos_validados:
            valor_total_item = produto_val['valor_unitario'] * produto_val['quantidade']
            itens_para_salvar.append({
                'produto_id': produto_val['produto_id'],  # ObjectId
                'codigo': produto_val['codigo'],
                'nome': produto_val['nome'],
                'valor_unitario': produto_val['valor_unitario'],
                'quantidade': produto_val['quantidade'],
                'valor_total': valor_total_item
            })
        
        # Prepara dados da venda
        now = datetime.utcnow()
        venda_data = {
            'itens': itens_para_salvar,
            'valor_total_venda': float(valor_total_venda),
            'created_at': now
        }
        
        # Registra venda no MongoDB
        result = self.collection.insert_one(venda_data)
        
        # Atualiza estoque de cada produto
        for produto_val in produtos_validados:
            produto_id = produto_val['produto_id']  # ObjectId
            quantidade_vendida = produto_val['quantidade']
            
            # Atualiza estoque (subtrai quantidade vendida)
            produtos_collection.update_one(
                {'_id': produto_id},
                {
                    '$inc': {'quantidade': -quantidade_vendida},
                    '$set': {'updated_at': now}
                }
            )
        
        # Busca a venda inserida
        venda = self.collection.find_one({'_id': result.inserted_id})
        venda['_id'] = str(venda['_id'])
        
        # Converte ObjectId dos itens para string
        for item in venda['itens']:
            item['produto_id'] = str(item['produto_id'])
        
        return venda
    
    def listar_vendas(self) -> List[Dict[str, Any]]:
        """
        Retorna todas as vendas ordenadas da mais recente para a mais antiga.
        
        Returns:
            Lista de vendas com id normalizado e quantidade_itens
        """
        vendas = list(self.collection.find().sort('created_at', -1))
        
        for venda in vendas:
            # Normaliza _id para id (Django não permite _id nos templates)
            venda['id'] = str(venda['_id'])
            venda['_id'] = str(venda['_id'])
            # Quantidade de itens = soma das quantidades dos itens
            itens = venda.get('itens', [])
            venda['quantidade_itens'] = sum(item.get('quantidade', 0) for item in itens)
        
        return vendas
    
    def obter_venda_por_id(self, venda_id: str) -> Optional[Dict[str, Any]]:
        """
        Retorna uma venda específica pelo ID.
        
        Args:
            venda_id: ID da venda (ObjectId como string)
        
        Returns:
            Dict com dados da venda ou None se não encontrado
        """
        try:
            venda = self.collection.find_one({'_id': ObjectId(venda_id)})
            
            if not venda:
                return None
            
            # Normaliza _id para id
            venda['id'] = str(venda['_id'])
            venda['_id'] = str(venda['_id'])
            
            # Converte ObjectId dos itens para string
            for item in venda.get('itens', []):
                if 'produto_id' in item:
                    item['produto_id'] = str(item['produto_id'])
            
            return venda
        except Exception:
            return None
