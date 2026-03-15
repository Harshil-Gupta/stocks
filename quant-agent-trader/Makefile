# Makefile for Quant Agent Trader
# Compatible with Windows and Unix

.PHONY: help install setup run backtest dashboard data ingest test clean

# Default target
help:
	@echo Quant Agent Trader - Production Commands
	@echo.
	@echo Setup ^& Installation:
	@echo   make install          - Install dependencies
	@echo   make setup           - Full setup
	@echo.
	@echo Running:
	@echo   make run             - Run analysis on RELIANCE
	@echo   make backtest        - Run backtest
	@echo   make dashboard       - Launch Streamlit
	@echo   make analyze         - Analyze symbol
	@echo.
	@echo Development:
	@echo   make test            - Run tests
	@echo   make clean           - Clean cache

# Installation
install:
	pip install -e .

setup: install
	@mkdir data\raw 2>NUL
	@mkdir data\processed 2>NUL
	@mkdir data\cache 2>NUL
	@mkdir models 2>NUL
	@mkdir logs 2>NUL
	@mkdir notebooks 2>NUL
	@if not exist .env copy .env.example .env
	@echo Setup complete!

run:
	python main.py analyze --symbol RELIANCE

backtest:
	python main.py backtest --symbols RELIANCE,TCS --start 2024-01-01 --end 2025-01-01

dashboard:
	streamlit run dashboard/app.py

analyze:
	python main.py analyze --symbol RELIANCE

test:
	pytest tests/ -v

clean:
	@for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
	@for /r . %%f in (*.pyc) do @if exist "%%f" del /q "%%f"
	@for /d /r . %%d in (*.egg-info) do @if exist "%%d" rmdir /s /q "%%d"
	@if exist .pytest_cache rmdir /s /q .pytest_cache
	@if exist htmlcov rmdir /s /q htmlcov
