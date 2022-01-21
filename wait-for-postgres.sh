#!/bin/sh
# wait-for-postgres.sh

set -e
  
host="$1"
shift
  
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$host" -U "notifier" -c '\q'; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 5
done
  
>&2 echo "Postgres is up - executing command"
exec "$@"


