# RAG Application with Chatbot & iOS API

Application de Retrieval-Augmented Generation (RAG) avec chatbot intelligent et API REST accessible depuis iOS.

## 📁 Structure du Projet

```
my-RAG/
├── docs/                      # Documentation complète
│   ├── specifications/        # Spécifications fonctionnelles et techniques
│   ├── design/               # Documents de conception et architecture
│   ├── adr/                  # Architecture Decision Records
│   ├── guides/               # Guides et manuels
│   │   ├── user/            # Guides utilisateur
│   │   ├── developer/       # Guides développeur
│   │   └── deployment/      # Guides de déploiement
│   └── api/                 # Documentation API (OpenAPI/Swagger)
│
├── project-management/       # Gestion de projet
│   ├── action-plans/        # Plans d'action et sprints
│   ├── post-mortems/        # Analyses post-mortem
│   ├── meetings/            # Comptes-rendus de réunions
│   └── roadmap/             # Roadmap produit
│
├── src/                     # Code source
│   ├── api/                # API REST
│   │   ├── routes/         # Routes API
│   │   ├── middleware/     # Middlewares
│   │   ├── controllers/    # Contrôleurs
│   │   └── validators/     # Validateurs de données
│   ├── chatbot/            # Module chatbot
│   │   ├── handlers/       # Gestionnaires de conversation
│   │   ├── prompts/        # Templates de prompts
│   │   └── memory/         # Gestion mémoire conversationnelle
│   ├── rag/                # Module RAG
│   │   ├── vectorstore/    # Base vectorielle
│   │   ├── embeddings/     # Génération d'embeddings
│   │   ├── retrievers/     # Récupération de documents
│   │   └── chains/         # Chaînes LangChain/LlamaIndex
│   ├── models/             # Modèles de données
│   ├── utils/              # Utilitaires
│   └── config/             # Configuration application
│
├── tests/                   # Tests
│   ├── unit/               # Tests unitaires
│   ├── integration/        # Tests d'intégration
│   ├── e2e/                # Tests end-to-end
│   └── fixtures/           # Données de test
│
├── infrastructure/          # Infrastructure
│   ├── docker/             # Configuration Docker
│   ├── kubernetes/         # Manifestes K8s
│   ├── terraform/          # Infrastructure as Code
│   └── scripts/            # Scripts de déploiement
│
├── mobile/                  # Application mobile
│   └── ios/                # Client iOS
│
├── monitoring/              # Monitoring et observabilité
│   ├── logs/               # Configuration logs
│   ├── metrics/            # Métriques
│   └── alerts/             # Alertes
│
├── data/                    # Données
│   ├── raw/                # Données brutes
│   ├── processed/          # Données traitées
│   └── indexes/            # Index vectoriels
│
└── config/                  # Configuration globale
    ├── environments/        # Config par environnement
    └── secrets/            # Secrets (non versionné)
```

## 🚀 Quick Start

1. **Installation des dépendances**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configuration**
   ```bash
   cp config/environments/.env.example .env
   ```

3. **Démarrage de l'application**
   ```bash
   python src/main.py
   ```

## 📖 Documentation

- [Spécifications](./docs/specifications/)
- [Architecture](./docs/design/)
- [Guide utilisateur](./docs/guides/user/)
- [Guide développeur](./docs/guides/developer/)
- [Documentation API](./docs/api/)

## 🧪 Tests

```bash
# Tests unitaires
pytest tests/unit/

# Tests d'intégration
pytest tests/integration/

# Tests E2E
pytest tests/e2e/
```

## 📱 Application iOS

Voir [mobile/ios/README.md](./mobile/ios/README.md) pour les instructions de build et déploiement.

## 🔧 Technologies

- **Backend**: Python, FastAPI
- **RAG**: LangChain/LlamaIndex
- **LLM**: OpenAI/Claude/Local
- **Vector DB**: Chroma/Pinecone/Weaviate
- **API**: REST, WebSocket
- **Mobile**: Swift, SwiftUI
- **Infrastructure**: Docker, Kubernetes
- **Monitoring**: Prometheus, Grafana

## 📝 Contribution

Voir [CONTRIBUTING.md](./CONTRIBUTING.md) pour les guidelines de contribution.

## 📄 License

[MIT License](./LICENSE)
