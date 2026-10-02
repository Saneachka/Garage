.PHONY: help up down build logs ps clean dev backend-frontend

# Default target
help:
	@echo "Garage Auto Service - Docker Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@echo "  up              Start all services (detached)"
	@echo "  down            Stop all services"
	@echo "  build           Build all images"
	@echo "  logs            Show logs for all services"
	@echo "  ps              Show running containers"
	@echo "  clean           Remove containers, volumes, and images"
	@echo "  dev             Start with live reload (backend only)"
	@echo "  backend-logs    Show backend logs"
	@echo "  frontend-logs   Show frontend logs"
	@echo "  db-logs         Show database logs"
	@echo "  migrate         Run database migrations"
	@echo "  migrate-create  Create new migration (usage: make migrate-create MSG='message')"
	@echo "  shell-backend   Open shell in backend container"
	@echo "  shell-db        Open psql in database"

# Start all services
up:
	docker compose up -d

# Stop all services
down:
	docker compose down

# Build all images
build:
	docker compose build --no-cache

# Show logs
logs:
	docker compose logs -f

# Show running containers
ps:
	docker compose ps

# Clean everything
clean:
	docker compose down -v --rmi all --remove-orphans

# Development with hot reload (backend)
dev:
	docker compose up -d postgres redis
	docker compose up backend

# Individual service logs
backend-logs:
	docker compose logs -f backend

frontend-logs:
	docker compose logs -f frontend

db-logs:
	docker compose logs -f postgres

# Database migrations
migrate:
	docker compose exec backend alembic upgrade head

migrate-create:
	docker compose exec backend alembic revision --autogenerate -m "$(MSG)"

# Shell access
shell-backend:
	docker compose exec backend bash

shell-db:
	docker compose exec postgres psql -U postgres -d auto_service

# Quick restart
restart: down up