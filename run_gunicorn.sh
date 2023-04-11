#!/bin/sh
if [ -f "gunicorn.pid" ]; then
    kill -9 `cat gunicorn.pid` || true
    rm gunicorn.pid
fi

gunicorn --bind 0.0.0.0:8000 --pid gunicorn.pid stargeo.wsgi:application