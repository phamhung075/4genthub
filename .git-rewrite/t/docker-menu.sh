#!/bin/bash

# Wrapper script to call the actual docker-menu.sh from correct location
# This allows running docker-menu.sh from project root

echo "🔗 Redirecting to docker-system/docker-menu.sh..."
cd docker-system && ./docker-menu.sh "$@"