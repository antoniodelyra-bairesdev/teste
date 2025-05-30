#!/usr/bin/env bash
set -euo pipefail

function retry {
  local retries=$1
  shift
  local count=0
  until "$@"; do
    exit=$?
    wait=$((2 ** $count))
    count=$(($count + 1))
    if [ $count -lt $retries ]; then
      echo "Retry $count/$retries exited $exit, retrying in $wait seconds..."
      sleep $wait
    else
      echo "Retry $count/$retries exited $exit, no more retries left."
      return $exit
    fi
  done
  return 0
}

echo "###############################"
echo "Running migrations..."
echo "###############################"
# if ! inv migrate; then
#   echo "inv migrate failed, falling back to inv db-upgrade..."
# retry 5 inv db-upgrade
# else
#   echo "inv migrate succeeded."
# fi

echo "###############################"
echo "Migrations done."
echo "###############################"
# We could seed the database at first run.
# exec /bin/sh -c "$*"

echo "###############################"
echo "Starting the application."
echo "###############################"
exec uvicorn application:app --host 0.0.0.0 --port 17000