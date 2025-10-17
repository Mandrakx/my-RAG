# 🚀 Quick Start - Ollama avec my-RAG

Guide rapide pour utiliser Ollama comme interface de requêtes pour votre RAG en **5 minutes**.

## ⚡ Installation Express (Windows)

### Étape 1: Installer Ollama (2 min)

```powershell
# Option A: Téléchargement direct
# Aller sur https://ollama.com/download/windows
# Double-cliquer sur l'installeur

# Option B: Via Chocolatey (si installé)
choco install ollama
```

### Étape 2: Télécharger un Modèle (2 min)

```bash
# Modèle recommandé pour démarrer
ollama pull mistral:7b-instruct

# Tester le modèle
ollama run mistral:7b-instruct "Bonjour, présente-toi en français"
```

### Étape 3: Installer le Client Python (30 sec)

```bash
pip install ollama
```

### Étape 4: Tester l'Intégration (30 sec)

```python
# test_ollama.py
from src.rag.llm.ollama_adapter import OllamaLLM

llm = OllamaLLM()
response = llm.generate("Résume en 3 points ce qu'est le RAG")
print(response)
```

```bash
python test_ollama.py
```

## 🎯 Utilisation avec my-RAG

### Test Simple (Sans Données)

```python
from src.rag.llm.ollama_adapter import OllamaLLM, OllamaConfig

# Configuration
config = OllamaConfig(
    model="mistral:7b-instruct",
    temperature=0.7,
    max_tokens=512
)

# Initialiser
llm = OllamaLLM(config)

# Question simple
response = llm.generate(
    prompt="Explique le concept de RAG en termes simples",
    system_prompt="Tu es un expert en IA explicatif"
)

print(response)
```

### Avec RAG Complet (Avec Données Indexées)

```python
from src.rag.llm.ollama_adapter import OllamaRAGChain, OllamaConfig
from src.rag.retrieval.hybrid_retriever import ConversationSearchEngine

# 1. Initialiser le search engine
search_engine = ConversationSearchEngine(
    qdrant_host="localhost",
    qdrant_port=6333,
    collection_name="conversations"
)

# 2. Configurer Ollama
ollama_config = OllamaConfig(
    model="mistral:7b-instruct",
    temperature=0.7,
    max_tokens=512
)

# 3. Créer la chain RAG
rag_chain = OllamaRAGChain(
    search_engine=search_engine,
    ollama_config=ollama_config
)

# 4. Poser une question
response = rag_chain.process(
    query="Quels sont les derniers projets dont on a parlé ?",
    max_results=5
)

# 5. Afficher la réponse
print("=== Réponse ===")
print(response.answer)
print(f"\nConfiance: {response.confidence:.2%}")
print(f"Temps: {response.processing_time:.2f}s")
print(f"Sources: {len(response.sources)}")

# 6. Voir les sources
for i, source in enumerate(response.sources[:3], 1):
    print(f"\nSource {i}:")
    print(f"  Date: {source.chunk.metadata.get('date', 'N/A')[:10]}")
    print(f"  Score: {source.relevance_score:.2f}")
    print(f"  Extrait: {source.chunk.text[:150]}...")
```

### Streaming (Affichage en Temps Réel)

```python
from src.rag.llm.ollama_adapter import OllamaLLM

llm = OllamaLLM()

# Génération avec streaming
print("Réponse: ", end='')
for chunk in llm.generate_stream("Explique le RAG en détail"):
    print(chunk, end='', flush=True)
print()  # Nouvelle ligne à la fin
```

## 🔧 Configuration dans my-RAG

### Via Fichier .env

```bash
# .env
LLM_BACKEND=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral:7b-instruct
OLLAMA_TEMPERATURE=0.7
OLLAMA_MAX_TOKENS=512
```

### Via Code

```python
import os
from src.rag.llm.ollama_adapter import OllamaConfig, OllamaRAGChain

# Charger depuis env
config = OllamaConfig(
    model=os.getenv("OLLAMA_MODEL", "mistral:7b-instruct"),
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
    temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0.7")),
    max_tokens=int(os.getenv("OLLAMA_MAX_TOKENS", "512"))
)

chain = OllamaRAGChain(search_engine, config)
```

## 📊 Vérifier que Tout Fonctionne

### Test 1: Ollama Server

```bash
# Vérifier si Ollama tourne
curl http://localhost:11434/api/version

# Doit retourner: {"version":"0.1.x"}
```

### Test 2: Modèles Disponibles

```bash
# Lister les modèles installés
ollama list

# Doit montrer:
# NAME                    ID              SIZE    MODIFIED
# mistral:7b-instruct     xxx             4.1GB   X minutes ago
```

### Test 3: Génération Simple

```bash
ollama run mistral:7b-instruct "Bonjour"
```

### Test 4: API Python

```python
import ollama

response = ollama.chat(
    model='mistral:7b-instruct',
    messages=[{'role': 'user', 'content': 'Hello'}]
)

print(response['message']['content'])
```

## 🎨 Exemples de Prompts

### Analyse de Conversation

```python
response = rag_chain.process(
    query="Résume les décisions prises lors de la dernière réunion",
    max_results=10
)
```

### Profil Personne

```python
response = rag_chain.process(
    query="Crée un profil de Jean Dupont basé sur nos conversations",
    max_results=20
)
```

### Préparation Réunion

```python
response = rag_chain.process(
    query="Suggère des sujets à aborder avec Marie lors de notre prochaine réunion",
    max_results=15
)
```

### Analyse Projet

```python
response = rag_chain.process(
    query="Quel est l'état d'avancement du projet X ?",
    max_results=25
)
```

## 🔥 Modèles Alternatifs

### Pour Meilleure Qualité

```bash
# Llama 3 (meilleure compréhension)
ollama pull llama3:8b-instruct

# Dans le code
config = OllamaConfig(model="llama3:8b-instruct")
```

### Pour Plus de Vitesse

```bash
# Phi-3 Mini (ultra-rapide)
ollama pull phi3:mini

# Dans le code
config = OllamaConfig(model="phi3:mini")
```

### Pour le Français

```bash
# Mistral est excellent en français (déjà téléchargé)
ollama pull mistral:7b-instruct
```

## 🐛 Troubleshooting Rapide

### Erreur: "Connection refused"

```bash
# Vérifier si Ollama tourne
curl http://localhost:11434

# Si erreur, redémarrer Ollama
# Windows: Chercher "Ollama" dans les Services et redémarrer
```

### Erreur: "Model not found"

```bash
# Télécharger le modèle
ollama pull mistral:7b-instruct
```

### Réponses Lentes

```python
# Réduire max_tokens
config = OllamaConfig(
    model="mistral:7b-instruct",
    max_tokens=256  # Au lieu de 512
)
```

### Erreur VRAM

```bash
# Utiliser version quantifiée (plus légère)
ollama pull mistral:7b-instruct-q4_0
```

## 📈 Performance Attendue

Sur RTX 3090:
- **Première requête**: ~2s (chargement modèle)
- **Requêtes suivantes**: ~0.5s
- **Génération**: 15-30 tokens/seconde
- **VRAM**: ~6GB
- **CPU**: 10-20%

## 🚀 Prochaines Étapes

1. **Indexer des conversations**
   ```python
   # Voir docs/INGESTION_PIPELINE.md
   ```

2. **Créer une API REST**
   ```python
   # Voir src/api/routes/conversations.py
   ```

3. **Ajouter plus de modèles**
   ```bash
   ollama pull llama3:8b-instruct
   ollama pull codellama:7b-instruct
   ```

4. **Monitorer les performances**
   ```python
   # Voir docs/MONITORING.md (Prometheus/Grafana)
   ```

## 📚 Documentation Complète

- **Guide Détaillé**: `docs/OLLAMA_INTEGRATION.md`
- **Comparaison Backends**: `docs/LLM_BACKENDS_COMPARISON.md`
- **Code Source**: `src/rag/llm/ollama_adapter.py`

---

**C'est tout !** Vous avez maintenant Ollama configuré et prêt à utiliser avec my-RAG 🎉

Pour des questions ou problèmes, consultez la documentation complète ou les issues GitHub.
