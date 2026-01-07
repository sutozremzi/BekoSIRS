# Gunicorn configuration file for BekoSIRS Backend
# https://docs.gunicorn.org/en/stable/settings.html

import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests (prevent memory leaks)
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "/var/log/bekosirs/gunicorn-access.log"
errorlog = "/var/log/bekosirs/gunicorn-error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "bekosirs"

# Server mechanics
daemon = False
pidfile = "/var/run/bekosirs/gunicorn.pid"
umask = 0
user = None
group = None
tmp_upload_dir = None

# SSL (if terminating SSL at Gunicorn)
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"
