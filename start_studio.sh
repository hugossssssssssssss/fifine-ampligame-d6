#!/usr/bin/env bash
# Quickstart script for Fifine AmpliGame D6 Studio
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "=========================================================="
echo " Starting Fifine AmpliGame D6 Studio Pro (Zero Fifine App)"
echo "=========================================================="

python3 run_cli.py studio
