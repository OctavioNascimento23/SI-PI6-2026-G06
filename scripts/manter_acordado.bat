@echo off
rem Duplo clique para impedir que o PC suspenda/bloqueie enquanto o Colab treina.
rem Deixe esta janela aberta. Feche-a (ou Ctrl+C) quando o treino terminar.
rem Argumentos opcionais sao repassados, por exemplo:  manter_acordado.bat -Horas 10 -SemMouse
title Mantendo o PC acordado (treino Colab)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0manter_acordado.ps1" %*
echo.
pause
