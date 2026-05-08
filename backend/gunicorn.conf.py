import os

bind    = f"0.0.0.0:{os.getenv('PORT', '5000')}"
workers = 1          # deve ser 1 — estado da mempool fica em memória
worker_class = "gthread"
threads  = 8
timeout  = 120
keepalive = 5
accesslog = "-"
errorlog  = "-"
loglevel  = "info"
