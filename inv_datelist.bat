@echo off

curl -X POST -H "Content-type: application/text" --data "inv_datelist" http://127.0.0.1:8080/
pause
