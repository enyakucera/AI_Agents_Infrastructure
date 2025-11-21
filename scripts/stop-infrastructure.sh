#!/bin/bash
# Script pro zastavení infrastruktury

set -e

echo "🛑 Stopping AI Agents Infrastructure..."

docker-compose -f docker-compose.infrastructure.yml down

echo "✅ Infrastructure stopped"
