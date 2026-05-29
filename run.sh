#!/bin/bash

nohup .venv/bin/python pyserver.py > /dev/null 2>&1 &
echo "Start Running Server!"
