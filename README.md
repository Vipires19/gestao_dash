# Sistema de Gestão de Estoque

Sistema de gestão de estoque/vendas usando Django como framework web e MongoDB como banco de dados (sem ORM relacional).

## 🚀 Características

- **Django** como framework web
- **MongoDB** como banco de dados (via pymongo, sem Django ORM)
- **Código simples e legível**, fácil de evoluir
- **Estrutura organizada**: views simples, services separados, templates limpos

## 📦 Estrutura do Projeto

```
estoque/
├── estoque_project/          # Configurações do projeto Django
│   ├── settings.py           # Configurações (inclui MongoDB)
│   ├── urls.py               # URLs principais
│   └── wsgi.py               # WSGI config
├── estoque_app/              # App principal de estoque
│   ├── services/
│   │   └── produto_service.py  # Lógica de negócio de produtos
│   ├── views.py              # Views simples
│   └── urls.py               # URLs do app
├── core/                     # Módulo core compartilhado
│   └── database.py           # Conexão MongoDB centralizada
├── templates/                # Templates HTML
│   ├── base.html
│   └── estoque_app/
│       ├── produto_list.html
│       └── produto_form.html
└── manage.py
```

## 🗂 Entidade: Produto

Cada produto contém:

- `codigo` (string, único)
- `nome` (string)
- `preco_compra` (float)
- `preco_venda` (float)
- `quantidade` (int)
- `created_at` (datetime)
- `updated_at` (datetime)
- `_id` (ObjectId, gerado automaticamente pelo MongoDB)

## 🔌 Configuração do MongoDB

O projeto usa `pymongo` para acesso direto ao MongoDB. A conexão é centralizada em `core/database.py`.

### Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
# MongoDB
MONGO_USER=seu_usuario
MONGO_PASS=sua_senha
MONGO_HOST=cluster.mongodb.net
MONGO_DB_NAME=estoque_db

# Django
SECRET_KEY=sua-secret-key-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Exemplo de Conexão Local

Para MongoDB local sem autenticação:

```env
MONGO_USER=
MONGO_PASS=
MONGO_HOST=localhost:27017
MONGO_DB_NAME=estoque_db
```

## 📋 Instalação

1. **Clone ou navegue até o diretório do projeto:**

```bash
cd estoque
```

2. **Crie um ambiente virtual (recomendado):**

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. **Instale as dependências:**

```bash
pip install -r requirements.txt
```

4. **Configure o arquivo `.env`** (veja seção acima)

5. **Execute as migrações do Django (para sessões/admin):**

```bash
python manage.py migrate
```

6. **Execute o servidor:**

```bash
python manage.py runserver
```

7. **Acesse no navegador:**

- Listagem: http://localhost:8000/produtos/
- Cadastro: http://localhost:8000/produtos/novo/

## 🧩 Funcionalidades

### ✅ Listagem de Produtos

- **Rota:** `/produtos/`
- Exibe tabela com código, nome, preços e quantidade
- Ordena por nome
- Mensagem quando não houver produtos cadastrados

### ✅ Cadastro de Produto

- **Rota:** `/produtos/novo/`
- Formulário com todos os campos
- Validações:
  - Código obrigatório e único
  - Preços não podem ser negativos
  - Quantidade não pode ser negativa
- Redireciona para listagem após salvar
- Mensagens de sucesso/erro

## 🧱 Arquitetura

### Views (`estoque_app/views.py`)
- Views simples que chamam services e renderizam templates
- Não contêm lógica de negócio

### Services (`estoque_app/services/produto_service.py`)
- Contêm toda a lógica de negócio
- Acesso direto ao MongoDB via `get_produtos_collection()`
- Validações e regras de negócio

### Database (`core/database.py`)
- Conexão centralizada com MongoDB
- Singleton pattern para eficiência
- Função `get_database()` retorna o banco de dados

## 🚫 O que NÃO está implementado

- Login/autenticação
- Movimentação de estoque
- Vendas
- API REST
- Edição/exclusão de produtos (pode ser adicionado depois)

## 📝 Próximos Passos

O código está preparado para evoluir facilmente:

- Edição de produtos
- Exclusão de produtos
- Sistema de vendas
- Movimentação de estoque
- Integração com IA (se necessário)

## 📄 Licença

Este projeto é um exemplo de sistema de gestão de estoque usando Django + MongoDB.
