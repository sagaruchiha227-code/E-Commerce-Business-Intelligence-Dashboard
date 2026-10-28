@echo off
echo ======================================================================
echo Pushing OmniStore BI Suite to GitHub
echo Repo: https://github.com/sagaruchiha227-code/E-Commerce-Business-Intelligence-Dashboard.git
echo ======================================================================

cd /d "%~dp0"

where git >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo [!] Git command not found on your system.
    echo If you haven't installed Git yet, please download it from:
    echo     https://git-scm.com/download/win
    echo After installing Git, double-click this script again.
    echo.
    pause
    exit /b 1
)

echo [1/4] Initializing Git repository...
git init

echo [2/4] Setting remote repository origin...
git remote remove origin 2>nul
git remote add origin https://github.com/sagaruchiha227-code/E-Commerce-Business-Intelligence-Dashboard.git
git branch -M main

echo [3/4] Staging project files and committing...
git add .
git commit -m "Initial commit: E-Commerce Business Intelligence Suite (Landing Page, Executive Dashboard, Sales Analytics, KPI Documentation)"

echo [4/4] Pushing to GitHub...
echo (If prompted, click Sign in with browser to authorize your GitHub account)
echo.
git push -u origin main

if %errorlevel% equ 0 (
    echo.
    echo ======================================================================
    echo [SUCCESS] Your project is now published on GitHub!
    echo Check it out at:
    echo https://github.com/sagaruchiha227-code/E-Commerce-Business-Intelligence-Dashboard
    echo ======================================================================
) else (
    echo.
    echo [!] Push encountered an issue. Please verify your GitHub login or permissions.
)

pause
