#!/usr/bin/env bash
# OSRM veri hazırlama scripti — BekoSIRS (KKTC / Cyprus haritası)
#
# Kullanım:
#   cd BekoSIRS_api/deployment/osrm
#   bash setup.sh
#
# Gereksinimler: docker
# İndirilecek: ~70 MB PBF, işlem sonrası ~300 MB OSRM dosyaları

set -euo pipefail

DATA_DIR="$(cd "$(dirname "$0")" && pwd)/data"
PBF_URL="https://download.geofabrik.de/europe/cyprus-latest.osm.pbf"
PBF_FILE="$DATA_DIR/cyprus-latest.osm.pbf"
OSRM_IMAGE="ghcr.io/project-osrm/osrm-backend:v5.27.1"

mkdir -p "$DATA_DIR"

echo "==> Kıbrıs OSM verisi indiriliyor..."
if [ -f "$PBF_FILE" ]; then
    echo "    $PBF_FILE zaten mevcut, atlanıyor. Yeniden indirmek için sil."
else
    curl -L -o "$PBF_FILE" "$PBF_URL"
    echo "    İndirme tamamlandı."
fi

echo "==> osrm-extract (profil: car) çalıştırılıyor..."
docker run --rm -v "$DATA_DIR:/data" "$OSRM_IMAGE" \
    osrm-extract -p /opt/car.lua /data/cyprus-latest.osm.pbf

echo "==> osrm-partition çalıştırılıyor (MLD)..."
docker run --rm -v "$DATA_DIR:/data" "$OSRM_IMAGE" \
    osrm-partition /data/cyprus-latest.osrm

echo "==> osrm-customize çalıştırılıyor (MLD)..."
docker run --rm -v "$DATA_DIR:/data" "$OSRM_IMAGE" \
    osrm-customize /data/cyprus-latest.osrm

echo ""
echo "✅ OSRM verisi hazır: $DATA_DIR"
echo "   Şimdi servisi başlatın:"
echo "   docker compose -f deployment/docker-compose.osrm.yml up -d"
