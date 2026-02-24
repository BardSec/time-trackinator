#!/bin/sh
set -e

mkdir -p /app/instance

echo "Starting Time Trackinator..."
exec "$@"
