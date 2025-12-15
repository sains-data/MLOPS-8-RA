@echo off
python scripts/train.py > train.log 2>&1
echo Done >> train.log
