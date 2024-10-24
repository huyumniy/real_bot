@echo off
REM Define the name of the shortcut
set SHORTCUT_NAME=realmadrid_bot.lnk

REM Define the path to the desktop
set DESKTOP_PATH=%USERPROFILE%\Desktop

REM Move the shortcut to the desktop
move "%cd%\%SHORTCUT_NAME%" "%DESKTOP_PATH%"

echo Shortcut moved to Desktop.

set "project_dir=..\real_bot-main"
set "venv_dir=%project_dir%"

rem Create virtual environment
python -m venv "%venv_dir%"

rem Activate virtual environment
call "%venv_dir%\Scripts\activate"

rem Navigate back to the working directory
cd /d "%~dp0"

rem Install requirements
python -m pip install -r "%project_dir%\requirements.txt"

rem Deactivate virtual environment
deactivate

echo Installation complete.
pause
