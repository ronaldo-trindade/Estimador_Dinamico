# Estimador de Taxas Dinâmico com Gráfico de Mempool

Dashboard em tempo real que monitora a mempool do Bitcoin, estima taxas por horizonte de confirmação e alerta quando transações são confirmadas.

Desenvolvido para o hackathon do curso **Bitcoin Coders — Core Craft**.

## Link para o vídeo de demonstração:

https://drive.google.com/file/d/1CyFIJJWvKR_c0MlTgl30C74gFoJ4Hryz/view?usp=sharing

## Link para a aplicação na VPS:

http://ronaldotrindade.pro.br:5000/


## Funcionalidades

- **Histograma da mempool** — distribuição de transações por faixa de taxa (sat/vB), alternando entre contagem e vsize total
- **Estimativas de taxa** — próximo bloco, 3 blocos, 6 blocos e ~1 dia (via `estimatesmartfee`)
- **Calculadora de custo** — informa o custo em sat e em BTC para uma transação de N vBytes em cada horizonte
- **Monitoramento de tx** — insira um txid para receber alerta sonoro + notificação do navegador quando for confirmada
- **Feed de purgas** — transações removidas da mempool sem confirmação (RBF, expiração)
- **Atualização automática** — eventos via ZMQ (`hashblock`, `hashtx`) propagados ao browser por Socket.IO

## Arquitetura

```
Bitcoin Core
  ├── RPC  →  backend/rpc.py           (snapshots de estado)
  └── ZMQ  →  backend/zmq_listener.py  (eventos em tempo real)
                    ↓
          backend/app.py  (Flask + Socket.IO)
                    ↓
          frontend/index.html  (Chart.js + Socket.IO client)
```

O backend mantém o estado da mempool em memória e o reconstrói a cada novo bloco ou a cada 2 s quando chegam novas transações.

## Pré-requisitos

- Python 3.10+
- Bitcoin Core com RPC e ZMQ habilitados

## Variáveis de ambiente

| Variável       | Descrição                        | Padrão              |
|----------------|----------------------------------|---------------------|
| `RPC_USER`     | Usuário RPC do Bitcoin Core      | —                   |
| `RPC_PASSWORD` | Senha RPC do Bitcoin Core        | —                   |
| `RPC_HOST`     | Host do nó                       | `127.0.0.1`         |
| `RPC_PORT`     | Porta RPC                        | `8332`              |
| `ZMQ_URL`      | Endpoint ZMQ do nó               | `tcp://127.0.0.1:28332` |
| `PORT`         | Porta HTTP do servidor           | `5000`              |

## Estrutura do projeto

```
Estimador_Dinamico/
├── backend/
│   ├── app.py            # Flask + Socket.IO, rotas e callbacks ZMQ
│   ├── mempool.py        # Reconstrução do histograma via getrawmempool
│   ├── zmq_listener.py   # Subscriber ZMQ (hashblock / hashtx)
│   ├── rpc.py            # Cliente RPC genérico
│   ├── gunicorn.conf.py  # Configuração do servidor WSGI
│   └── requirements.txt
├── frontend/
│   ├── index.html        # Interface (Chart.js + Socket.IO client)
│   └── static/
│       └── socket.io.min.js
├── estimador.service     # Unit systemd para deploy
├── .env.example          # Template de configuração
└── .gitignore
```

## Licença

MIT
