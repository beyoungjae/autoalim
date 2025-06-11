@echo off
chcp 65001 > nul
cd /d C:\autokakao

:: 가상환경 활성화
call venv\Scripts\activate.bat

:: 로그 파일에 UTF-8로 출력 저장
python main.py >> log.txt 2>&1