# Guide Utilisateur - RAG Application

## Introduction
Bienvenue dans l'application RAG (Retrieval-Augmented Generation). Cette application vous permet d'interroger vos documents via un chatbot intelligent alimenté par un LLM.

## Démarrage rapide

### 1. Accès à l'application
- **Web**: Accédez à l'URL [https://your-domain.com]
- **iOS**: Téléchargez l'application depuis l'App Store
- **API**: Endpoint disponible sur [https://api.your-domain.com]

### 2. Authentification
1. Créez un compte ou connectez-vous
2. Obtenez votre clé API depuis votre profil
3. Configurez l'authentification dans votre client

## Fonctionnalités principales

### Téléchargement de documents
1. Cliquez sur "Nouveau document"
2. Sélectionnez vos fichiers (formats supportés: PDF, TXT, JSON, DOCX)
3. Attendez l'indexation (barre de progression)
4. Votre document est prêt à être interrogé

### Interrogation via chatbot
1. Sélectionnez les documents sources
2. Tapez votre question dans le chat
3. Le système recherche les informations pertinentes
4. Recevez une réponse contextualisée

### Gestion des conversations
- Historique des conversations sauvegardé
- Export des conversations en PDF/JSON
- Partage de conversations avec d'autres utilisateurs

## Utilisation de l'API

### Authentification
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     https://api.your-domain.com/v1/chat
```

### Envoi d'une question
```json
POST /v1/chat
{
  "question": "Votre question ici",
  "documents": ["doc_id_1", "doc_id_2"],
  "context_length": 5
}
```

### Réponse
```json
{
  "answer": "Réponse générée",
  "sources": [
    {
      "document": "doc_name",
      "page": 5,
      "confidence": 0.95
    }
  ],
  "conversation_id": "conv_123"
}
```

## Application iOS

### Installation
1. Téléchargez depuis l'App Store
2. Ouvrez l'application
3. Entrez votre clé API dans les paramètres

### Fonctionnalités mobile
- Chat en temps réel
- Mode hors ligne (documents cachés)
- Notifications push pour les réponses
- Partage rapide vers d'autres apps

## Paramètres avancés

### Configuration du modèle
- **Température**: Contrôle la créativité (0.0 - 1.0)
- **Max tokens**: Longueur maximale de réponse
- **Top-p**: Contrôle la diversité des réponses

### Filtres de recherche
- Par date
- Par type de document
- Par tags/catégories
- Par niveau de confiance

## Limites et quotas

| Plan | Documents/mois | Questions/jour | Taille max document |
|------|---------------|----------------|-------------------|
| Free | 10 | 50 | 5 MB |
| Pro | 100 | 500 | 50 MB |
| Enterprise | Illimité | Illimité | 500 MB |

## Résolution des problèmes

### Le chatbot ne répond pas
1. Vérifiez votre connexion internet
2. Vérifiez que votre quota n'est pas dépassé
3. Essayez de reformuler votre question

### Documents non indexés
1. Vérifiez le format du document
2. Assurez-vous que le document n'est pas corrompu
3. Vérifiez la taille du document

### Réponses non pertinentes
1. Affinez votre question
2. Sélectionnez des documents plus spécifiques
3. Ajustez les paramètres du modèle

## FAQ

**Q: Mes données sont-elles sécurisées?**
R: Oui, toutes les données sont chiffrées en transit et au repos.

**Q: Puis-je supprimer mes documents?**
R: Oui, depuis l'interface de gestion des documents.

**Q: Le système apprend-il de mes questions?**
R: Non, chaque session est indépendante pour garantir la confidentialité.

## Support

- **Email**: support@your-domain.com
- **Documentation**: [https://docs.your-domain.com]
- **Status page**: [https://status.your-domain.com]

## Raccourcis clavier

| Raccourci | Action |
|-----------|--------|
| Ctrl/Cmd + Enter | Envoyer question |
| Ctrl/Cmd + N | Nouvelle conversation |
| Ctrl/Cmd + D | Upload document |
| Ctrl/Cmd + / | Afficher l'aide |

## Mises à jour

Consultez le [changelog](../../../CHANGELOG.md) pour les dernières mises à jour.