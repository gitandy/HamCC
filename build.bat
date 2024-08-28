@echo off
set PATH=%ProgramFiles%\Git\bin

::echo Get version info...
::git describe --tags > version.txt
::set /p VERSION=<version.txt
::git rev-parse --abbrev-ref HEAD > branch.txt
::set /p BRANCH=<branch.txt
::if "%BRANCH%" EQU "master" set BRANCH=
::git status -s -uno --porcelain > status.txt
::FOR %%I in (status.txt) do set STAT_SIZE=%%~zI
::if %STAT_SIZE% GTR 0 (set UNCLEAN=True) else (set UNCLEAN=False)
::echo __version__ = '%VERSION%'> src\adif_file\__version__.py
::echo __branch__ = '%BRANCH%'>> src\adif_file\__version__.py
::echo __unclean__ = %UNCLEAN%>> src\adif_file\__version__.py
::echo Version: %VERSION% %BRANCH% %UNCLEAN%
::del version.txt branch.txt status.txt

call venv\Scripts\activate.bat

python -m pip install --upgrade build
python -m build
pause
