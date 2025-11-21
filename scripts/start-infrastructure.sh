#!/bin/bash
# Script pro spuštění infrastruktury

set -e

echo "🚀 Starting AI Agents Infrastructure..."

# Kontrola, zda existuje Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed!"
    exit 1
fi

# Kontrola, zda existuje docker-compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed!"
    exit 1
fi

# Kontrola .env souboru
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "Please create .env file from .env.example"
    exit 1
fi

# Vytvoření Docker sítě
echo "📡 Creating Docker network..."
docker network inspect ai-agents-network >/dev/null 2>&1 || \
    docker network create ai-agents-network

# Spuštění infrastruktury
echo "🏗️  Building and starting services..."
docker-compose -f docker-compose.infrastructure.yml up -d --build

# Čekání na služby
echo "⏳ Waiting for services to start..."
sleep 10

# Kontrola zdraví služeb
echo "🔍 Checking service health..."
services=("scraper:5001" "ai-analyzer:5002" "email:5003" "whatsapp:5004")
all_healthy=true

for service in "${services[@]}"; do
    name="${service%%:*}"
    port="${service##*:}"
    
    if curl -f -s http://localhost:$port/health > /dev/null; then
        echo "✅ $name is healthy"
    else
        echo "❌ $name is not responding"
        all_healthy=false
    fi
done

if [ "$all_healthy" = true ]; then
    echo ""
    echo "🎉 All services are running!"
    echo ""
    echo "Service endpoints:"
    echo "  - Scraper: http://localhost:5001"
    echo "  - AI Analyzer: http://localhost:5002"
    echo "  - Email: http://localhost:5003"
    echo "  - WhatsApp: http://localhost:5004"
    echo ""
    echo "View logs: docker-compose -f docker-compose.infrastructure.yml logs -f"
else
    echo ""
    echo "⚠️  Some services failed to start. Check logs:"
    echo "docker-compose -f docker-compose.infrastructure.yml logs"
    exit 1
fi
