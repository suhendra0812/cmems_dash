build:
	docker compose up --build -d

down:
	docker compose down

clean:
	docker compose down
	docker system prune -fa