"""
Service para lógica de categorias.

Localização: estoque_app/services/categoria_service.py

Este service contém a lógica de negócio relacionada a categorias.
Acesso direto ao MongoDB via pymongo (sem ORM).
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from core.database import get_database
from bson import ObjectId


def get_categorias_collection():
    """
    Retorna a collection de categorias do MongoDB.
    
    Returns:
        Collection de categorias
    """
    db = get_database()
    return db["categorias"]


class CategoriaService:
    """
    Service para gerenciar categorias.
    
    Exemplo de uso:
        service = CategoriaService()
        categorias = service.listar_categorias()
        categoria = service.criar_categoria(nome='Eletrônicos')
    """
    
    def __init__(self):
        self.collection = get_categorias_collection()
        self._ensure_indexes()
    
    def _ensure_indexes(self):
        """
        Cria índices necessários para otimizar queries.
        
        Índices:
        - nome: Único, para validação de nome único
        """
        # Índice único para nome
        self.collection.create_index('nome', unique=True)
    
    def listar_categorias(self) -> List[Dict[str, Any]]:
        """
        Lista todas as categorias ordenadas por nome.
        
        Returns:
            Lista de categorias ordenadas por nome
        """
        categorias = list(self.collection.find().sort('nome', 1))
        
        # Converte ObjectId para string para serialização
        for categoria in categorias:
            categoria['_id'] = str(categoria['_id'])
        
        return categorias
    
    def criar_categoria(self, nome: str) -> Dict[str, Any]:
        """
        Cria uma nova categoria.
        
        Args:
            nome: Nome da categoria
        
        Returns:
            Dict com dados da categoria criada
        
        Raises:
            ValueError: Se dados inválidos ou nome já existe
        """
        # Validações
        if not nome or not nome.strip():
            raise ValueError("Nome é obrigatório")
        
        # Verifica se nome já existe
        if self.collection.find_one({'nome': nome.strip()}):
            raise ValueError(f"Categoria com nome '{nome}' já existe")
        
        # Prepara dados para inserção
        now = datetime.utcnow()
        categoria_data = {
            'nome': nome.strip(),
            'created_at': now,
            'updated_at': now
        }
        
        # Insere no MongoDB
        result = self.collection.insert_one(categoria_data)
        
        # Busca a categoria inserida
        categoria = self.collection.find_one({'_id': result.inserted_id})
        categoria['_id'] = str(categoria['_id'])
        
        return categoria
    
    def buscar_categoria_por_id(self, categoria_id: str) -> Optional[Dict[str, Any]]:
        """
        Busca uma categoria pelo ID.
        
        Args:
            categoria_id: ID da categoria
        
        Returns:
            Dict com dados da categoria ou None se não encontrado
        """
        try:
            categoria = self.collection.find_one({'_id': ObjectId(categoria_id)})
            
            if categoria:
                categoria['_id'] = str(categoria['_id'])
            
            return categoria
        except Exception:
            return None
    
    def atualizar_categoria(self, categoria_id: str, nome: str) -> Dict[str, Any]:
        """
        Atualiza uma categoria.
        
        Args:
            categoria_id: ID da categoria
            nome: Novo nome da categoria
        
        Returns:
            Dict com dados da categoria atualizada
        
        Raises:
            ValueError: Se dados inválidos, categoria não encontrada ou nome já existe
        """
        # Validações
        if not nome or not nome.strip():
            raise ValueError("Nome é obrigatório")
        
        # Verifica se categoria existe
        categoria = self.buscar_categoria_por_id(categoria_id)
        if not categoria:
            raise ValueError("Categoria não encontrada")
        
        # Verifica se outro registro já tem esse nome
        existing = self.collection.find_one({
            'nome': nome.strip(),
            '_id': {'$ne': ObjectId(categoria_id)}
        })
        if existing:
            raise ValueError(f"Categoria com nome '{nome}' já existe")
        
        # Atualiza no MongoDB
        now = datetime.utcnow()
        self.collection.update_one(
            {'_id': ObjectId(categoria_id)},
            {'$set': {
                'nome': nome.strip(),
                'updated_at': now
            }}
        )
        
        # Busca a categoria atualizada
        categoria_atualizada = self.collection.find_one({'_id': ObjectId(categoria_id)})
        categoria_atualizada['_id'] = str(categoria_atualizada['_id'])
        
        return categoria_atualizada
