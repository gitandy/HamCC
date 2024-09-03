@echo off
set PATH=C:\cygwin64\bin;%PATH%
SET PROJ_PATH=%~dp0

call %PROJ_PATH%venv\Scripts\activate.bat

echo Invoking make %* ...
make.exe %*
