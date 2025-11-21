#!/bin/bash
# Script pro restart infrastruktury

set -e

echo "🔄 Restarting AI Agents Infrastructure..."

docker-compose -f docker-compose.infrastructure.yml restart

echo "✅ Infrastructure restarted"
