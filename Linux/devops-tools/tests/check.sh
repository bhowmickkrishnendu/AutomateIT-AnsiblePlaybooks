#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m unittest discover -s tests -v
yamllint -c .yamllint .
ansible-playbook -i inventory.example.ini playbook.yml --syntax-check
ansible-playbook -i inventory.example.ini interactive.yml --syntax-check
ansible-lint -c .ansible-lint playbook.yml interactive.yml
