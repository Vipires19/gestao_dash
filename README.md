# Sistema de Gestão de Estoque, Vendas e Despesas

Sistema web para gestão de estoque, vendas e despesas operacionais. Desenvolvido com Django e MongoDB, voltado para pequenos negócios que precisam de controle de produtos, PDV e visão financeira básica.

**Público-alvo:** negócios que precisam de gestão de estoque, registro de vendas e controle de despesas sem complexidade de ERP.

---

## Funcionalidades

- **Produtos** — Cadastro e edição de produtos com código, nome, categorias, preços e quantidade em estoque.
- **Vendas** — PDV (ponto de venda) para registro de vendas, com busca por código, atualização automática de estoque e comprovante em PDF.
- **Estoque automático** — Baixa de estoque ao registrar vendas; alertas de estoque crítico no dashboard.
- **Despesas** — Registro de despesas operacionais (data, descrição, categoria, valor) para controle financeiro.
- **Dashboard** — Visão do dia: faturamento, despesas, lucro, vendas, produtos vendidos, estoque crítico, gráficos (últimos 7 dias), últimas vendas e alertas.
- **Análise por período** — Dashboard histórico com filtro por mês atual, últimos 3 meses ou todo o período; gráficos e insights (produto mais vendido, maior venda, maior despesa).

---

## Tecnologias utilizadas

- **Python** — Linguagem principal.
- **Django** — Framework web (templates, views, URLs; sem uso do Django ORM para dados de negócio).
- **MongoDB** — Banco de dados (acesso via **pymongo**).
- **Bootstrap 5** — Layout e componentes da interface (sidebar, navbar, cards).
- **HTML / CSS / JavaScript** — Templates Django e scripts simples.
- **Chart.js** — Gráficos no dashboard e na página de análise.
- **ReportLab** — Geração de comprovante de venda em PDF.
- **python-dotenv** — Variáveis de ambiente a partir do arquivo `.env`.

---

## Como rodar o projeto localmente

1. **Clone o repositório e entre na pasta do projeto:**

```bash
git clone <url-do-repositorio>
cd estoque
```

2. **Crie e ative um ambiente virtual:**

```bash
python -m venv venv
```

No Linux/macOS:

```bash
source venv/bin/activate
```

No Windows (PowerShell ou CMD):

```bash
venv\Scripts\activate
```

3. **Instale as dependências:**

```bash
pip install -r requirements.txt
```

4. **Crie o arquivo `.env` na raiz do projeto** com as variáveis necessárias:

```env
SECRET_KEY=sua-chave-secreta-aqui
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# MongoDB local (sem usuário/senha)
MONGO_USER=
MONGO_PASS=
MONGO_HOST=localhost:27017
MONGO_DB_NAME=estoque_db
```

Para MongoDB Atlas, preencha `MONGO_USER`, `MONGO_PASS` e use em `MONGO_HOST` o host do cluster (ex.: `cluster0.xxxxx.mongodb.net`). O projeto monta a URI automaticamente.

5. **Execute as migrações do Django** (sessões e admin):

```bash
python manage.py migrate
```

6. **Inicie o servidor:**

```bash
python manage.py runserver
```

7. **Acesse no navegador:** [http://localhost:8000/](http://localhost:8000/)

---

## Deploy no Railway (MVP)

O projeto pode ser implantado no [Railway](https://railway.app/) para testes do MVP.

### Passos

1. **Crie uma conta no Railway** e um novo projeto.
2. **Conecte o repositório GitHub** ao projeto (conecte o repositório que contém este código).
3. **Configure as variáveis de ambiente** no painel do Railway:

   - `SECRET_KEY` — Chave secreta do Django (gere uma nova para produção).
   - `DEBUG` — `False` em produção.
   - `ALLOWED_HOSTS` — Domínio gerado pelo Railway (ex.: `seu-app.railway.app`) ou `*` para aceitar qualquer host.
   - `MONGO_USER` — Usuário do MongoDB (Atlas recomendado).
   - `MONGO_PASS` — Senha do MongoDB.
   - `MONGO_HOST` — Host do cluster (ex.: `cluster0.xxxxx.mongodb.net`).
   - `MONGO_DB_NAME` — Nome do banco (ex.: `estoque_db`).

4. **Defina o comando de start:**

   No Railway, em **Settings** → **Deploy**, configure o comando de start:

   ```bash
   gunicorn estoque_project.wsgi --bind 0.0.0.0:$PORT
   ```

   O Railway define a variável `PORT` automaticamente.

5. **Deploy** — Após salvar, o Railway fará o build e o deploy. A primeira execução pode exigir `python manage.py migrate` (configure como comando de release no Railway se necessário).

### Observação

- Para servir arquivos estáticos em produção, considere usar **WhiteNoise** ou um CDN; o projeto já está preparado para evoluir nesse sentido.
- Em produção, use sempre **HTTPS** e **DEBUG=False**.

---

## Variáveis de ambiente

| Variável        | Obrigatória | Descrição |
|----------------|-------------|-----------|
| `SECRET_KEY`   | Sim         | Chave secreta do Django. |
| `DEBUG`        | Não         | `True` em desenvolvimento, `False` em produção. Default: `True`. |
| `ALLOWED_HOSTS`| Não         | Hosts permitidos, separados por vírgula. Default: `localhost,127.0.0.1`. |
| `MONGO_USER`   | Não*        | Usuário MongoDB (vazio para MongoDB local). |
| `MONGO_PASS`   | Não*        | Senha MongoDB (vazio para MongoDB local). |
| `MONGO_HOST`   | Não         | Host do MongoDB. Default: `localhost:27017`. |
| `MONGO_DB_NAME`| Não         | Nome do banco. Default: `estoque_db`. |

\* Para MongoDB Atlas, `MONGO_USER` e `MONGO_PASS` são necessários.

---

## Observações importantes

- **MVP** — O projeto está em fase de MVP, adequado para testes e validação com usuários.
- **Sem autenticação** — Não há login ou controle de acesso; o sistema é aberto. A inclusão de autenticação está prevista para uma próxima etapa.
- **Dados para testes** — Use apenas dados de teste; não utilize informações sensíveis ou reais de produção sem as devidas proteções.
- **Evolução** — A estrutura (services, views, templates) foi pensada para facilitar a adição de relatórios, integrações e melhorias futuras.

---

## Estrutura do projeto (resumo)

```
estoque/
├── estoque_project/     # Configurações Django (settings, urls, wsgi)
├── estoque_app/         # App principal (views, services, urls, templates)
├── core/                # Módulo compartilhado (conexão MongoDB)
├── templates/           # Templates HTML (base, dashboard, vendas, etc.)
├── manage.py
├── requirements.txt
└── README.md
```

---

## Licença

Este projeto é um sistema de gestão de estoque, vendas e despesas desenvolvido com Django e MongoDB.
