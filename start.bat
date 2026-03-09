@echo off
setlocal

echo Starting Nano Banana Pro Local...

if "%EVOLINK_API_KEY%"=="" (
    echo Warning: EVOLINK_API_KEY is not set. Seedream 5.0 Lite will not work.
)
if "%GEMINI_API_KEY%"=="" (
    echo Warning: GEMINI_API_KEY is not set. Nano Banana Pro will not work.
)

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH.
    pause
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Node.js is not installed or not in PATH.
    pause
    exit /b 1
)

REM Create virtual environment if it doesn't exist
if not exist "backend\venv" (
    echo Creating Python virtual environment...
    python -m venv backend\venv
)

REM Always install/update dependencies to ensure they are current
call backend\venv\Scripts\activate.bat
echo Installing/Updating Python dependencies...
pip install -r backend\requirements.txt

REM Start Backend
echo Starting Backend Server...
cd backend
start "Backend Server" cmd /k "call venv\Scripts\activate.bat && python main.py"
cd ..

REM Install Frontend dependencies if needed
if not exist "frontend\node_modules" (
    echo Installing Frontend dependencies...
    cd frontend
    call npm install
    cd ..
)

REM Start Frontend
echo Starting Frontend Server...
cd frontend
start "Frontend Server" cmd /k "npm run dev"

echo.
echo Application started!
echo Backend running on http://localhost:8000
echo Frontend running on http://localhost:5173
echo.
echo Press any key to close this launcher (servers will keep running)...
pause >nul
