@echo off
chcp 65001 > nul
title Telegram Role Bot (24/7 Auto-Restart)

echo =======================================================
echo    Telegram Role Bot - Режим непрерывной работы 24/7
echo =======================================================
echo.

:loop
echo [%DATE% %TIME%] Запуск бота...
python main.py

echo.
echo [%DATE% %TIME%] Внимание: Процесс завершился или упал с кодом ошибки %ERRORLEVEL%.
echo Перезапуск через 5 секунд...
timeout /t 5 /nobreak > nul
goto loop
