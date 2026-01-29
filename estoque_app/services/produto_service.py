"""
Service para lógica de produtos (estoque).

Localização: estoque_app/services/produto_service.py

Este service contém a lógica de negócio relacionada a produtos.
Acesso direto ao MongoDB via pymongo (sem ORM).
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from core.database import get_database
from bson import ObjectId


def get_produtos_collection():
    """
    Retorna a collection de produtos do MongoDB.
    
    Returns:
        Collection de produtos
    """
    db = get_database()
    return db["produtos"]


class ProdutoService:
    """
    Service para gerenciar produtos (estoque).
    
    Exemplo de uso:
        service = ProdutoService()
        produtos = service.listar_produtos()
        produto = service.criar_produto(
            codigo='PROD001',
            nome='Produto Teste',
            preco_compra=10.0,
            preco_venda=20.0,
            quantidade=100
        )
    """
    
    def __init__(self):
        self.collection = get_produtos_collection()
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """
        Cria índices necessários para otimizar queries.
        
        Índices:
        - codigo: Único, para validação de código único
        - nome: Para ordenação e busca
        """
        # Índice único para código
        self.collection.create_index('codigo', unique=True)
        
        # Índice para nome (ordenação)
        self.collection.create_index('nome')
        
        # Índice para categoria_id (filtros)
        self.collection.create_index('categoria_id')
    
    def listar_produtos(self) -> List[Dict[str, Any]]:
        """
        Lista todos os produtos ordenados por nome.
        
        Returns:
            Lista de produtos ordenados por nome
        """
        produtos = list(self.collection.find().sort('nome', 1))
        
        # Converte ObjectId para string para serialização
        for produto in produtos:
            produto['_id'] = str(produto['_id'])
            if 'categoria_id' in produto:
                produto['categoria_id'] = str(produto['categoria_id'])
        
        return produtos
    
    def criar_produto(self, codigo: str, nome: str, categoria_id: str,
                     preco_compra: float, preco_venda: float, quantidade: int) -> Dict[str, Any]:
        """
        Cria um novo produto.
        
        Args:
            codigo: Código único do produto
            nome: Nome do produto
            categoria_id: ID da categoria (ObjectId como string)
            preco_compra: Preço de compra
            preco_venda: Preço de venda
            quantidade: Quantidade em estoque
        
        Returns:
            Dict com dados do produto criado
        
        Raises:
            ValueError: Se dados inválidos ou código já existe
        """
        # Validações
        if not codigo or not codigo.strip():
            raise ValueError("Código é obrigatório")
        
        if not nome or not nome.strip():
            raise ValueError("Nome é obrigatório")
        
        if not categoria_id:
            raise ValueError("Categoria é obrigatória")
        
        if preco_compra < 0:
            raise ValueError("Preço de compra não pode ser negativo")
        
        if preco_venda < 0:
            raise ValueError("Preço de venda não pode ser negativo")
        
        if quantidade < 0:
            raise ValueError("Quantidade não pode ser negativa")
        
        # Verifica se código já existe
        if self.collection.find_one({'codigo': codigo.strip()}):
            raise ValueError(f"Produto com código '{codigo}' já existe")
        
        # Busca categoria para obter o nome (denormalização)
        from estoque_app.services.categoria_service import CategoriaService
        categoria_service = CategoriaService()
        categoria = categoria_service.buscar_categoria_por_id(categoria_id)
        
        if not categoria:
            raise ValueError("Categoria não encontrada")
        
        # Prepara dados para inserção
        now = datetime.utcnow()
        produto_data = {
            'codigo': codigo.strip(),
            'nome': nome.strip(),
            'categoria_id': ObjectId(categoria_id),
            'categoria_nome': categoria['nome'],
            'preco_compra': float(preco_compra),
            'preco_venda': float(preco_venda),
            'quantidade': int(quantidade),
            'created_at': now,
            'updated_at': now
        }
        
        # Insere no MongoDB
        result = self.collection.insert_one(produto_data)
        
        # Busca o produto inserido
        produto = self.collection.find_one({'_id': result.inserted_id})
        produto['_id'] = str(produto['_id'])
        produto['categoria_id'] = str(produto['categoria_id'])
        
        return produto
    
    def buscar_produto_por_codigo(self, codigo: str) -> Optional[Dict[str, Any]]:
        """
        Busca um produto pelo código.
        
        Args:
            codigo: Código do produto
        
        Returns:
            Dict com dados do produto ou None se não encontrado
        """
        produto = self.collection.find_one({'codigo': codigo.strip()})
        
        if produto:
            # Normaliza _id para id (Django não permite _id nos templates)
            produto['id'] = str(produto['_id'])
            produto['_id'] = str(produto['_id'])
            if 'categoria_id' in produto:
                produto['categoria_id'] = str(produto['categoria_id'])
        
        return produto
    
    def obter_produto_por_id(self, produto_id: str) -> Optional[Dict[str, Any]]:
        """
        Busca um produto pelo ID.
        
        Args:
            produto_id: ID do produto (ObjectId como string)
        
        Returns:
            Dict com dados do produto ou None se não encontrado
        """
        try:
            produto = self.collection.find_one({'_id': ObjectId(produto_id)})
            
            if not produto:
                return None
            
            # Converte _id para id (Django não permite _id nos templates)
            produto['id'] = str(produto['_id'])
            produto['_id'] = str(produto['_id'])
            
            if 'categoria_id' in produto:
                produto['categoria_id'] = str(produto['categoria_id'])
            
            return produto
        except Exception:
            return None
    
    def atualizar_produto(self, produto_id: str, codigo: str, nome: str, categoria_id: str,
                         preco_compra: float, preco_venda: float, quantidade: int) -> Dict[str, Any]:
        """
        Atualiza um produto existente.
        
        Args:
            produto_id: ID do produto (ObjectId como string)
            codigo: Código único do produto
            nome: Nome do produto
            categoria_id: ID da categoria (ObjectId como string)
            preco_compra: Preço de compra
            preco_venda: Preço de venda
            quantidade: Quantidade em estoque
        
        Returns:
            Dict com dados do produto atualizado
        
        Raises:
            ValueError: Se dados inválidos, produto não encontrado ou código já existe (em outro produto)
        """
        # Validações
        if not codigo or not codigo.strip():
            raise ValueError("Código é obrigatório")
        
        if not nome or not nome.strip():
            raise ValueError("Nome é obrigatório")
        
        if not categoria_id:
            raise ValueError("Categoria é obrigatória")
        
        if preco_compra < 0:
            raise ValueError("Preço de compra não pode ser negativo")
        
        if preco_venda < 0:
            raise ValueError("Preço de venda não pode ser negativo")
        
        if quantidade < 0:
            raise ValueError("Quantidade não pode ser negativa")
        
        # Verifica se produto existe
        produto = self.obter_produto_por_id(produto_id)
        if not produto:
            raise ValueError("Produto não encontrado")
        
        # Verifica se código já existe em outro produto
        produto_existente = self.collection.find_one({
            'codigo': codigo.strip(),
            '_id': {'$ne': ObjectId(produto_id)}
        })
        if produto_existente:
            raise ValueError(f"Produto com código '{codigo}' já existe")
        
        # Busca categoria para obter o nome (denormalização)
        from estoque_app.services.categoria_service import CategoriaService
        categoria_service = CategoriaService()
        categoria = categoria_service.buscar_categoria_por_id(categoria_id)
        
        if not categoria:
            raise ValueError("Categoria não encontrada")
        
        # Atualiza no MongoDB
        now = datetime.utcnow()
        self.collection.update_one(
            {'_id': ObjectId(produto_id)},
            {'$set': {
                'codigo': codigo.strip(),
                'nome': nome.strip(),
                'categoria_id': ObjectId(categoria_id),
                'categoria_nome': categoria['nome'],
                'preco_compra': float(preco_compra),
                'preco_venda': float(preco_venda),
                'quantidade': int(quantidade),
                'updated_at': now
            }}
        )
        
        # Busca o produto atualizado
        produto_atualizado = self.collection.find_one({'_id': ObjectId(produto_id)})
        produto_atualizado['_id'] = str(produto_atualizado['_id'])
        produto_atualizado['categoria_id'] = str(produto_atualizado['categoria_id'])
        
        return produto_atualizado