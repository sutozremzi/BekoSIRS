# BekoSIRS Backend - Monitoring & Observability Setup

Production monitoring ve error tracking kurulum rehberi.

---

## 📊 Monitoring Stack Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Django    │────▶│   Sentry     │────▶│   Alerts    │
│   Backend   │     │ Error Track  │     │  (Email/    │
└─────────────┘     └──────────────┘     │   Slack)    │
       │                                   └─────────────┘
       │            ┌──────────────┐
       └───────────▶│  Prometheus  │
                    │   Metrics    │
                    └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   Grafana    │
                    │  Dashboards  │
                    └──────────────┘
```

---

## 🔴 Error Tracking - Sentry

### Installation

```bash
pip install --upgrade sentry-sdk
```

### Configuration

```python
# settings.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

if not DEBUG:
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN"),
        integrations=[DjangoIntegration()],

        # Set traces_sample_rate to 1.0 to capture 100% of transactions
        traces_sample_rate=1.0,

        # Set profiles_sample_rate to 1.0 to profile 100% of sampled transactions
        profiles_sample_rate=1.0,

        # Environment
        environment="production",

        # Release tracking
        release=f"bekosirs@{os.getenv('APP_VERSION', '1.0.0')}",

        # Send PII (be careful with GDPR)
        send_default_pii=False,
    )
```

### Environment Variable

```env
# .env
SENTRY_DSN=https://[key]@[organization].ingest.sentry.io/[project]
APP_VERSION=1.0.0
```

### Custom Error Reporting

```python
# In views or anywhere
from sentry_sdk import capture_exception, capture_message

try:
    risky_operation()
except Exception as e:
    capture_exception(e)
    # or
    capture_message("Something went wrong", level="error")
```

### Sentry Best Practices

1. **User Context:**
```python
from sentry_sdk import configure_scope

with configure_scope() as scope:
    scope.user = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
    }
```

2. **Tags:**
```python
scope.set_tag("transaction_type", "product_purchase")
scope.set_tag("user_role", user.role)
```

3. **Breadcrumbs:**
```python
from sentry_sdk import add_breadcrumb

add_breadcrumb(
    category='auth',
    message='User logged in',
    level='info',
)
```

---

## 📈 Metrics - Prometheus + Grafana

### Install django-prometheus

```bash
pip install django-prometheus
```

### Configuration

```python
# settings.py

INSTALLED_APPS = [
    'django_prometheus',  # Add as first app
    ...
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    ...
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

# Database wrapper
DATABASES = {
    'default': {
        'ENGINE': 'django_prometheus.db.backends.postgresql',  # or sqlite3
        ...
    }
}
```

### URLs

```python
# urls.py
urlpatterns = [
    path('metrics/', include('django_prometheus.urls')),
    ...
]
```

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'bekosirs'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics/'
```

### Running Prometheus

```bash
# Docker
docker run -d \
  --name prometheus \
  -p 9090:9090 \
  -v /path/to/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus

# Access: http://localhost:9090
```

### Grafana Setup

```bash
# Docker
docker run -d \
  --name grafana \
  -p 3000:3000 \
  grafana/grafana

# Access: http://localhost:3000
# Default: admin/admin
```

### Import Dashboard

1. Add Prometheus data source (http://prometheus:9090)
2. Import Django dashboard (ID: 9528)
3. Customize as needed

---

## 📝 Application Performance Monitoring (APM)

### Django Silk (Development)

```bash
pip install django-silk
```

```python
# settings.py
INSTALLED_APPS = ['silk']
MIDDLEWARE = ['silk.middleware.SilkyMiddleware']

# urls.py
urlpatterns += [path('silk/', include('silk.urls', namespace='silk'))]
```

Access: `http://localhost:8000/silk/`

### New Relic (Production)

```bash
pip install newrelic
```

```ini
# newrelic.ini
[newrelic]
license_key = YOUR_LICENSE_KEY
app_name = BekoSIRS Backend
monitor_mode = true
```

```bash
# Run with New Relic
NEW_RELIC_CONFIG_FILE=newrelic.ini newrelic-admin run-program gunicorn ...
```

---

## 🔍 Logging Best Practices

### Structured Logging

```python
import logging
import json

logger = logging.getLogger(__name__)

# Structured log
logger.info(json.dumps({
    "event": "user_login",
    "user_id": user.id,
    "ip": request.META.get('REMOTE_ADDR'),
    "user_agent": request.META.get('HTTP_USER_AGENT'),
}))
```

### Log Aggregation - ELK Stack

```bash
# Docker Compose
version: '3'
services:
  elasticsearch:
    image: elasticsearch:8.5.0
    ports:
      - "9200:9200"
    environment:
      - discovery.type=single-node

  logstash:
    image: logstash:8.5.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    ports:
      - "5000:5000"

  kibana:
    image: kibana:8.5.0
    ports:
      - "5601:5601"
```

### Logstash Configuration

```conf
# logstash.conf
input {
  file {
    path => "/var/log/bekosirs/*.log"
    start_position => "beginning"
  }
}

filter {
  grok {
    match => { "message" => "%{COMBINEDAPACHELOG}" }
  }
  date {
    match => [ "timestamp", "dd/MMM/yyyy:HH:mm:ss Z" ]
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "bekosirs-%{+YYYY.MM.dd}"
  }
}
```

---

## 🚨 Alerting

### Prometheus Alertmanager

```yaml
# alertmanager.yml
route:
  receiver: 'email'

receivers:
  - name: 'email'
    email_configs:
      - to: 'devops@bekosirs.com'
        from: 'alerts@bekosirs.com'
        smarthost: 'smtp.gmail.com:587'
        auth_username: 'alerts@bekosirs.com'
        auth_password: 'app_password'
```

### Alert Rules

```yaml
# alerts.yml
groups:
  - name: bekosirs
    rules:
      - alert: HighErrorRate
        expr: rate(django_http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"

      - alert: SlowResponse
        expr: histogram_quantile(0.95, django_http_request_duration_seconds) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Slow response times detected"

      - alert: HighMemoryUsage
        expr: process_resident_memory_bytes > 1e9
        for: 5m
        labels:
          severity: warning
```

---

## 📊 Key Metrics to Monitor

### Application Metrics

1. **Request Rate**
   - Requests per second
   - By endpoint
   - By status code

2. **Response Time**
   - Average latency
   - 95th/99th percentile
   - By endpoint

3. **Error Rate**
   - 4xx errors (client)
   - 5xx errors (server)
   - By type

4. **Database**
   - Query count
   - Query duration
   - Connection pool usage

### Infrastructure Metrics

1. **CPU Usage**
   - Overall
   - Per worker

2. **Memory Usage**
   - RSS (Resident Set Size)
   - Heap size

3. **Disk I/O**
   - Read/write rate
   - Disk space

4. **Network**
   - Bandwidth usage
   - Connection count

---

## 🎯 SLOs (Service Level Objectives)

Define and monitor your SLOs:

```python
# Example SLOs for BekoSIRS
SLOs = {
    "availability": {
        "target": "99.9%",  # 3 nines
        "measurement": "uptime / total_time"
    },
    "latency": {
        "target": "95% of requests < 200ms",
        "measurement": "p95 response time"
    },
    "error_rate": {
        "target": "< 0.1%",
        "measurement": "errors / total_requests"
    }
}
```

---

## 📱 Monitoring Checklist

### Before Production

- [ ] Sentry configured and tested
- [ ] Prometheus metrics exposed
- [ ] Grafana dashboards created
- [ ] Alerting rules configured
- [ ] Log aggregation working
- [ ] Health check endpoint (`/health/`)
- [ ] Uptime monitoring (UptimeRobot/Pingdom)

### Daily Checks

- [ ] Review error logs
- [ ] Check response times
- [ ] Monitor disk space
- [ ] Review security logs

### Weekly Reviews

- [ ] Analyze trends
- [ ] Review SLO compliance
- [ ] Update dashboards
- [ ] Security incident review

---

## 🔧 Tools Summary

| Tool | Purpose | Cost |
|------|---------|------|
| Sentry | Error tracking | Free tier available |
| Prometheus | Metrics collection | Free (OSS) |
| Grafana | Visualization | Free (OSS) |
| ELK Stack | Log aggregation | Free (OSS) |
| New Relic | APM | Paid |
| Datadog | All-in-one | Paid |
| UptimeRobot | Uptime monitoring | Free tier available |

---

## 🚀 Quick Start

### Minimum Monitoring (Free)

```bash
# 1. Install Sentry
pip install sentry-sdk
# Configure in settings.py (see above)

# 2. Setup UptimeRobot
# Visit: https://uptimerobot.com
# Add monitor for: https://api.bekosirs.com/health/

# 3. Setup basic logging
# Already configured in settings.py

# 4. Done! You have:
# - Error tracking
# - Uptime monitoring
# - Application logs
```

### Production Grade (Recommended)

1. Sentry for errors
2. Prometheus + Grafana for metrics
3. ELK for logs
4. PagerDuty/Opsgenie for alerts
5. New Relic/Datadog for APM

---

## 📞 Support

Monitoring issues:
- Email: monitoring@bekosirs.com
- Slack: #bekosirs-monitoring
- On-call: Check PagerDuty

---

**Last Updated:** 2026-01-07
**Next Review:** 2026-02-07
