#!/bin/sh
# Seed the SQLite database on first boot, then start gunicorn.
set -e

if [ ! -f "$DATABASE" ]; then
    echo "Initializing database at $DATABASE"
    python -c "import app; app.init_db()"
fi

exec gunicorn --bind 0.0.0.0:5000 --workers 2 app:app
