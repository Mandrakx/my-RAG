# Multi-stage build pour optimiser la taille de l'image
FROM python:3.11-slim as builder

# Définir le répertoire de travail
WORKDIR /app

# Installer les dépendances système nécessaires pour la compilation
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copier les requirements et installer les dépendances Python
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage final
FROM python:3.11-slim

# Variables d'environnement
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/root/.local/bin:$PATH

# Installer les dépendances système runtime uniquement
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Créer un utilisateur non-root
RUN useradd -m -u 1000 appuser

# Définir le répertoire de travail
WORKDIR /app

# Copier les dépendances Python depuis le builder
COPY --from=builder /root/.local /home/appuser/.local

# Copier le code de l'application
COPY --chown=appuser:appuser . .

# Créer les répertoires nécessaires
RUN mkdir -p /app/data /app/logs /app/cache && \
    chown -R appuser:appuser /app

# Changer vers l'utilisateur non-root
USER appuser

# Exposer le port de l'application
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Commande de démarrage
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]