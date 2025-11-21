#!/bin/bash
# Script pro zobrazení logů infrastruktury

echo "📋 Showing infrastructure logs (Ctrl+C to exit)..."
echo ""

docker-compose -f docker-compose.infrastructure.yml logs -f --tail=100
