# 1. Rasmiy Python 3.12 muhitini yuklab olamiz
FROM python:3.12-slim

# 2. Postgres va shifrlash kutubxonalari ishlashi uchun Linux paketlarini o'rnatamiz
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# 3. Konteyner ichida ishchi papka yaratamiz
WORKDIR /app

# 4. Bizning sevimli 'uv' paket menejerimizni o'rnatamiz
RUN pip install uv

# 5. Kutubxonalar ro'yxatini (pyproject.toml) nusxalaymiz
COPY pyproject.toml ./

# 6. uv orqali barcha kutubxonalarni tizimga o'rnatamiz
RUN uv pip install --system -e .

# 7. Qolgan barcha kodlarni (app, frontend papkalarini) nusxalaymiz
COPY . .

# 8. Tashqaridan 8000-port orqali kirishga ruxsat beramiz
EXPOSE 8000

# 9. Konteyner ishga tushganda bajariladigan asosiy buyruq
CMD ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000"]