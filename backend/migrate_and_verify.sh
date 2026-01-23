#!/bin/bash
cd "$(dirname "$0")"
"/c/Users/Admin/AppData/Local/Programs/Python/Python312/python.exe" migrate_and_verify.py
exit $?
