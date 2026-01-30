# Chatwoot ↔ LinkedIn Bridge (Unipile)

## 📌 Visão Geral do Projeto

Este projeto tem como objetivo atuar como uma **ponte de integração entre o Chatwoot e o LinkedIn**, utilizando a API da **Unipile**.
Ele permite que mensagens enviadas e recebidas no LinkedIn sejam sincronizadas com o Chatwoot, centralizando o atendimento ao cliente em uma única plataforma.

A solução foi pensada para ser:

* 🔗 **Desacoplada**, facilitando manutenção e evolução
* ⚡ **Leve e performática**
* 🧩 **Fácil de integrar** com outros serviços
* 🐳 **Pronta para rodar em containers**

---

## 🧠 Decisões Técnicas e Justificativas

### 🐍 Por que Python?

Python foi escolhido por ser:

* Uma linguagem **simples, legível e produtiva**
* Muito utilizada em **APIs, integrações e automações**
* Possuir um ecossistema maduro de bibliotecas para web e cloud

Isso acelera o desenvolvimento e reduz a complexidade do código, o que é ideal para um serviço de integração.

---

### ⚡ Por que FastAPI?

O framework **FastAPI** foi utilizado para construir a API por diversos motivos:

* 🚀 **Alta performance**, baseada em ASGI
* 📄 **Validação automática de dados** com Pydantic
* 🔍 **Documentação automática** via Swagger/OpenAPI
* 🧪 Facilita testes e manutenção

Como o projeto depende fortemente de **webhooks** e troca de mensagens em tempo real, o FastAPI se mostrou uma escolha moderna e eficiente.

---

### 🗄️ Por que Supabase como banco de dados?

O **Supabase** foi escolhido por oferecer:

* PostgreSQL gerenciado (banco robusto e confiável)
* Interface simples para criação e manutenção de tabelas
* Fácil integração com aplicações modernas
* Ótimo custo-benefício para projetos pequenos e médios

Além disso, o uso do arquivo `supabase.sql` permite **reproduzir o banco facilmente** em qualquer ambiente, garantindo consistência.

---

### 🔔 Por que Webhooks?

Webhooks são ideais para esse cenário porque:

* Permitem comunicação **em tempo real**
* Evitam polling desnecessário
* Reduzem consumo de recursos
* São amplamente suportados por Chatwoot e Unipile

O projeto possui dois webhooks principais:

* **Chatwoot → API** (mensagens enviadas)
* **Unipile → API** (mensagens recebidas do LinkedIn)

---

### 🐳 Por que Docker?

O Docker foi utilizado para:

* Garantir **padronização do ambiente**
* Evitar problemas de “funciona na minha máquina”
* Facilitar deploy em servidores ou cloud
* Simplificar onboarding de novos desenvolvedores

Arquivos como `Dockerfile` e `stack.yml` deixam o projeto pronto para produção.

---

## 🗂️ Estrutura do Projeto

```text
.
├── app/                # Código principal da API (FastAPI)
├── dashboard.py        # Dashboard opcional com Streamlit
├── requirements.txt    # Dependências do projeto
├── Dockerfile          # Configuração do container
├── stack.yml           # Orquestração (Docker Swarm / Stack)
├── supabase.sql        # Script de criação das tabelas no banco
├── .env.example        # Exemplo de variáveis de ambiente
└── README.md           # Documentação do projeto
```

### Por que essa organização?

* 📁 Separação clara entre **API**, **dashboard** e **infraestrutura**
* 🔧 Facilita manutenção e escalabilidade
* 🧪 Permite testar partes do sistema de forma isolada
* 📖 Segue boas práticas de projetos backend

---

## ⚙️ Configuração do Projeto

### 1️⃣ Criar as tabelas no Supabase

Execute o conteúdo do arquivo `supabase.sql` no editor SQL do Supabase.

Isso garante que todas as tabelas necessárias estejam corretamente configuradas.

---

### 2️⃣ Configurar variáveis de ambiente

Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

E preencha com suas credenciais e segredos (tokens, URLs, etc).

---

### 3️⃣ Instalar dependências

```bash
pip install -r requirements.txt
```

---

### 4️⃣ Executar a API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Após isso, a API estará pronta para receber webhooks.

---

## 🔔 Endpoints de Webhook

### Chatwoot → API

```http
POST /webhook/chatwoot
```

Usado para receber mensagens enviadas a partir do Chatwoot.

---

### Unipile → API

```http
POST /webhook/unipile
```

Usado para receber mensagens vindas do LinkedIn via Unipile.

Ambos os endpoints suportam o header:

```http
X-Webhook-Secret
```

Isso adiciona uma camada extra de segurança para evitar chamadas não autorizadas.

---

## 🧪 Exemplos de Teste com cURL

### Chatwoot (mensagem enviada)

```bash
curl -X POST http://localhost:8000/webhook/chatwoot \
  -H 'Content-Type: application/json' \
  -H 'X-Webhook-Secret: change_me' \
  -d '{
    "event": "message_created",
    "message_type": "outgoing",
    "content": "Hello from Chatwoot",
    "conversation": {
      "meta": {
        "sender": {
          "custom_attributes": {
            "chat_id": "1Mha-KY4UaGmFPHDm1a7RQ"
          }
        }
      }
    }
  }'
```

---

### Unipile (mensagem recebida)

```bash
curl -X POST http://localhost:8000/webhook/unipile \
  -H 'Content-Type: application/json' \
  -H 'X-Webhook-Secret: change_me' \
  -d '{
    "event": "message_received",
    "chat_id": "1Mha-KY4UaGmFPHDm1a7RQ",
    "message": "Hello from LinkedIn",
    "is_sender": false,
    "attendees": [
      {
        "attendee_id": "RcVEq8W3XVSFa5wbO5nRfA",
        "attendee_name": "Joao Lucas"
      }
    ]
  }'
```

---

## 📊 Dashboard (Opcional)

O projeto inclui um dashboard simples usando **Streamlit**, útil para monitoramento e testes:

```bash
streamlit run dashboard.py
```

---

## ✅ Conclusão

Este projeto foi estruturado com foco em:

* Boas práticas de backend
* Clareza arquitetural
* Facilidade de deploy
* Escalabilidade futura

Ele demonstra domínio em **APIs, integrações, webhooks, containers e organização de código**, sendo ideal tanto para uso real quanto para portfólio ou avaliação acadêmica.
