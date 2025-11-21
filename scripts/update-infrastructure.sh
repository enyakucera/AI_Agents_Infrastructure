#!/bin/bash
# Script pro update infrastruktury z Gitu

set -e

echo "🔄 Updating AI Agents Infrastructure..."

# Pull nejnovější verze z Gitu
echo "📥 Pulling latest changes from Git..."
git pull

# Rebuild a restart služeb
echo "🏗️  Rebuilding services..."
docker-compose -f docker-compose.infrastructure.yml up -d --build

echo "✅ Update complete!"
echo ""
echo "View logs: ./scripts/logs-infrastructure.sh"
