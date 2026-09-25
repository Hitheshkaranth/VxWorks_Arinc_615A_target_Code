@echo off
rem One-command setup and usage for the ARINC 615A VxWorks target on Windows.
rem
rem   setup.bat                          build and run every host check (through WSL)
rem   setup.bat rehearse                 local target + protocol peer + verify (through WSL)
rem   setup.bat run                      run the target in WSL until Enter is pressed
rem   setup.bat test ^<ip^> [options]      protocol peer against a target (Windows Python)
rem   setup.bat cli ^<ip^> ^<cli-build^> [..]  ARINC 615A CLI Tool Suite acceptance test
rem
rem The build runs in WSL because the target code is built with GCC. Board tests run
rem natively on Windows: WSL sits behind NAT, and the board's TFTP transfers back to
rem the loader must reach a Windows process.
setlocal
set "ROOT=%~dp0"
set "CMD=%~1"
if "%CMD%"=="" set "CMD=setup"

if /i "%CMD%"=="test" goto test
if /i "%CMD%"=="cli" goto cli
if /i "%CMD%"=="help" goto help

where wsl >nul 2>&1 || (
  echo WSL is required for the build. In an elevated prompt run:  wsl --install
  echo then reboot and run setup.bat again.
  exit /b 1
)
set "WINROOT=%ROOT:~0,-1%"
for /f "usebackq delims=" %%p in (`wsl -e wslpath -a "%WINROOT%"`) do set "WROOT=%%p"
if not defined WROOT (
  echo Could not reach a WSL distribution. Run:  wsl --install -d Ubuntu
  exit /b 1
)
rem Build tree in the WSL home: unpacking Boost onto the Windows drive is slow.
wsl -e bash -lc "cd '%WROOT%' && ARINC_BUILD_DIR=$HOME/.cache/arinc615a-build bash ./setup.sh %*"
exit /b %errorlevel%

:test
if "%~2"=="" (echo usage: setup.bat test ^<target-ip^> [vxworks_target_test.py options] & exit /b 2)
where python >nul 2>&1 || (echo Python 3 is required on Windows: winget install Python.Python.3.12 & exit /b 1)
set "ARGS="
shift
:test_args
if "%~1"=="" goto test_run
set ARGS=%ARGS% %1
shift
goto test_args
:test_run
python "%ROOT%tests\vxworks_target_test.py" --target%ARGS%
exit /b %errorlevel%

:cli
if "%~3"=="" (echo usage: setup.bat cli ^<target-ip^> ^<cli-build^> [-FindPort n -TftpPort n ...] & exit /b 2)
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%tests\cli_acceptance.ps1" -Target %2 -CliBuild %3 %4 %5 %6 %7 %8 %9
exit /b %errorlevel%

:help
findstr /b "rem" "%~f0"
exit /b 0
