# Intégration Ollama avec my-RAG

Guide complet pour utiliser Ollama comme interface LLM pour les requêtes RAG.

## 🎯 Pourquoi Ollama ?

- **Local et Privé**: Toutes les données restent sur votre machine
- **Léger**: Moins de VRAM que HuggingFace Transformers
- **Simple**: API REST standard
- **Modèles variés**: Mistral, Llama 3, CodeLlama, etc.
- **Rapide**: Optimisé pour l'inférence

## 📥 Installation Ollama

### Windows

1. **Télécharger Ollama**
   ```
   https://ollama.com/download/windows
   ```

2. **Installer et Lancer**
   - Double-cliquer sur l'installeur
   - Ollama démarre automatiquement en service Windows
   - API disponible sur `http://localhost:11434`

### Vérifier l'Installation

```bash
# PowerShell ou CMD
curl http://localhost:11434/api/version
```

Réponse attendue :
```json
{"version":"0.1.x"}
```

## 📦 Modèles Recommandés

### Pour RTX 3090 (24GB VRAM)

| Modèle | Taille | VRAM | Use Case |
|--------|--------|------|----------|
| `mistral:7b-instruct` | 4.1GB | ~8GB | **Recommandé** - Général |
| `llama3:8b-instruct` | 4.7GB | ~9GB | Meilleure qualité |
| `phi3:medium` | 7.9GB | ~12GB | Bon compromis |
| `mistral:7b-instruct-q4_0` | 3.8GB | ~6GB | Plus rapide |

### Télécharger un Modèle

```bash
# Modèle recommandé pour démarrer
ollama pull mistral:7b-instruct

# Alternative plus performante
ollama pull llama3:8b-instruct

# Pour français
ollama pull mixtral:8x7b-instruct  # Attention: nécessite ~48GB VRAM
```

### Tester le Modèle

```bash
# Chat interactif
ollama run mistral:7b-instruct

# Test simple
ollama run mistral:7b-instruct "Résume ce texte : Claude est un assistant IA..."
```

## 🔌 Intégration avec my-RAG

### 1. Installer le Client Python

```bash
pip install ollama
```

### 2. Créer l'Adaptateur Ollama

**Fichier**: `src/rag/llm/ollama_adapter.py`

```python
"""
Ollama LLM adapter for my-RAG
Replaces HuggingFace Transformers with Ollama API
"""

import ollama
import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class OllamaConfig:
    """Configuration for Ollama LLM"""
    model: str = "mistral:7b-instruct"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 512
    timeout: int = 60

class OllamaLLM:
    """Ollama LLM wrapper compatible with RAG chains"""

    def __init__(self, config: Optional[OllamaConfig] = None):
        self.config = config or OllamaConfig()
        self.client = ollama.Client(host=self.config.base_url)

        # Verify model is available
        self._ensure_model_available()

        logger.info(f"OllamaLLM initialized with model: {self.config.model}")

    def _ensure_model_available(self):
        """Check if model is downloaded, pull if not"""
        try:
            models = self.client.list()
            model_names = [m['name'] for m in models.get('models', [])]

            if self.config.model not in model_names:
                logger.warning(f"Model {self.config.model} not found. Pulling...")
                self.client.pull(self.config.model)
                logger.info(f"Model {self.config.model} downloaded successfully")
        except Exception as e:
            logger.error(f"Error checking model availability: {e}")
            raise

    def generate(self,
                 prompt: str,
                 system_prompt: Optional[str] = None,
                 max_tokens: Optional[int] = None,
                 temperature: Optional[float] = None) -> str:
        """
        Generate response using Ollama

        Args:
            prompt: User prompt
            system_prompt: System instructions (optional)
            max_tokens: Max tokens to generate
            temperature: Sampling temperature

        Returns:
            Generated text
        """
        start_time = time.time()

        try:
            # Build messages
            messages = []
            if system_prompt:
                messages.append({
                    'role': 'system',
                    'content': system_prompt
                })

            messages.append({
                'role': 'user',
                'content': prompt
            })

            # Generate
            response = self.client.chat(
                model=self.config.model,
                messages=messages,
                options={
                    'temperature': temperature or self.config.temperature,
                    'top_p': self.config.top_p,
                    'num_predict': max_tokens or self.config.max_tokens
                },
                stream=False
            )

            generated_text = response['message']['content']

            duration = time.time() - start_time
            logger.info(f"Generated response in {duration:.2f}s")

            return generated_text.strip()

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise

    def generate_stream(self,
                       prompt: str,
                       system_prompt: Optional[str] = None):
        """
        Generate response with streaming (for real-time display)

        Yields:
            str: Token chunks as they're generated
        """
        try:
            messages = []
            if system_prompt:
                messages.append({'role': 'system', 'content': system_prompt})
            messages.append({'role': 'user', 'content': prompt})

            stream = self.client.chat(
                model=self.config.model,
                messages=messages,
                options={
                    'temperature': self.config.temperature,
                    'top_p': self.config.top_p,
                    'num_predict': self.config.max_tokens
                },
                stream=True
            )

            for chunk in stream:
                if 'message' in chunk and 'content' in chunk['message']:
                    yield chunk['message']['content']

        except Exception as e:
            logger.error(f"Error in streaming generation: {e}")
            raise


class OllamaRAGChain:
    """
    RAG Chain using Ollama instead of HuggingFace
    Drop-in replacement for BaseRAGChain
    """

    def __init__(self,
                 search_engine,
                 ollama_config: Optional[OllamaConfig] = None):
        self.search_engine = search_engine
        self.llm = OllamaLLM(ollama_config)

    def get_system_prompt(self) -> str:
        """Override in subclasses"""
        return """Tu es un assistant expert en analyse de conversations professionnelles.
Ton rôle est d'analyser les conversations et d'extraire des insights utiles.

Instructions:
- Réponds en français de manière claire et structurée
- Identifie les points clés, décisions et actions
- Mets en évidence les préoccupations et opportunités
- Propose des suggestions concrètes
- Base-toi uniquement sur les informations fournies dans le contexte"""

    def format_context(self, search_results) -> str:
        """Format search results as context"""
        context_parts = []

        for i, result in enumerate(search_results[:5]):
            chunk = result.chunk
            context_parts.append(f"""
Conversation {i+1} (Score: {result.relevance_score:.2f}):
Date: {chunk.metadata.get('date', 'Non spécifiée')[:10]}
Participants: {', '.join(chunk.metadata.get('participants', []))}
Contenu: {chunk.text}
---""")

        return '\n'.join(context_parts)

    def process(self, query: str, **search_kwargs):
        """Main RAG pipeline using Ollama"""
        from datetime import datetime
        from ..chains.rag_chains import RAGResponse

        start_time = datetime.now()

        # 1. Search
        search_results = self.search_engine.search_conversations(query, **search_kwargs)

        # 2. Format context
        context = self.format_context(search_results)

        # 3. Build prompt
        prompt = f"""Context:
{context}

Question: {query}"""

        # 4. Generate with Ollama
        answer = self.llm.generate(
            prompt=prompt,
            system_prompt=self.get_system_prompt()
        )

        # 5. Calculate confidence
        confidence = self._calculate_confidence(search_results)

        processing_time = (datetime.now() - start_time).total_seconds()

        return RAGResponse(
            answer=answer,
            sources=search_results,
            confidence=confidence,
            processing_time=processing_time,
            metadata={
                "query": query,
                "num_sources": len(search_results),
                "chain_type": self.__class__.__name__,
                "llm_backend": "ollama"
            }
        )

    def _calculate_confidence(self, search_results) -> float:
        """Calculate confidence score"""
        if not search_results:
            return 0.0

        total_score = 0.0
        total_weight = 0.0

        for i, result in enumerate(search_results[:5]):
            weight = 1.0 / (i + 1)
            total_score += result.relevance_score * weight
            total_weight += weight

        return total_score / total_weight if total_weight > 0 else 0.0
```

### 3. Mettre à Jour le Chain Manager

**Fichier**: `src/rag/chains/rag_chains.py`

Ajouter en haut du fichier :

```python
# Import Ollama adapter
try:
    from ..llm.ollama_adapter import OllamaLLM, OllamaConfig, OllamaRAGChain
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
```

Modifier `RAGChainManager.__init__()` :

```python
def __init__(self,
             search_engine: ConversationSearchEngine,
             use_ollama: bool = True,  # NEW
             ollama_config: Optional[OllamaConfig] = None):
    self.search_engine = search_engine
    self.use_ollama = use_ollama

    if use_ollama and OLLAMA_AVAILABLE:
        # Use Ollama for all chains
        from ..llm.ollama_adapter import OllamaRAGChain

        base_chain_class = OllamaRAGChain
        logger.info("Using Ollama LLM backend")
    else:
        # Use HuggingFace (original)
        base_chain_class = BaseRAGChain
        logger.info("Using HuggingFace LLM backend")

    # Initialize chains with selected backend
    # ... rest of initialization
```

### 4. Configuration Environnement

**Fichier**: `.env`

```bash
# LLM Backend
LLM_BACKEND=ollama  # ou 'huggingface'

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=mistral:7b-instruct
OLLAMA_TEMPERATURE=0.7
OLLAMA_MAX_TOKENS=512

# Pour comparer les performances
# OLLAMA_MODEL=llama3:8b-instruct
# OLLAMA_MODEL=phi3:medium
```

## 🚀 Utilisation

### Test Rapide

```python
from src.rag.llm.ollama_adapter import OllamaLLM, OllamaConfig

# Configuration
config = OllamaConfig(
    model="mistral:7b-instruct",
    temperature=0.7
)

# Initialiser
llm = OllamaLLM(config)

# Tester
response = llm.generate(
    prompt="Résume ce texte en 3 points...",
    system_prompt="Tu es un assistant expert en résumé."
)

print(response)
```

### Avec RAG Complet

```python
from src.rag.chains.rag_chains import RAGChainManager
from src.rag.retrieval.hybrid_retriever import ConversationSearchEngine
from src.rag.llm.ollama_adapter import OllamaConfig

# Initialiser search engine
search_engine = ConversationSearchEngine(...)

# Configurer Ollama
ollama_config = OllamaConfig(
    model="mistral:7b-instruct",
    temperature=0.7,
    max_tokens=512
)

# Créer chain manager avec Ollama
chain_manager = RAGChainManager(
    search_engine=search_engine,
    use_ollama=True,
    ollama_config=ollama_config
)

# Faire une requête
response = chain_manager.process_query(
    query="Quels sont les projets en cours ?",
    chain_type="project_analysis"
)

print(response.answer)
```

### API REST

Mettre à jour `src/main.py` :

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan"""
    # Startup
    print("Starting my-RAG with Ollama...")

    # Initialize search engine
    app.state.search_engine = ConversationSearchEngine(...)

    # Initialize chain manager with Ollama
    from src.rag.llm.ollama_adapter import OllamaConfig

    ollama_config = OllamaConfig(
        model=os.getenv("OLLAMA_MODEL", "mistral:7b-instruct"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    )

    app.state.chain_manager = RAGChainManager(
        search_engine=app.state.search_engine,
        use_ollama=True,
        ollama_config=ollama_config
    )

    yield

    # Shutdown
    print("Shutting down...")
```

## 📊 Comparaison Performance

| Aspect | HuggingFace Transformers | Ollama |
|--------|-------------------------|--------|
| **VRAM** | ~12-16GB | ~6-9GB |
| **Vitesse** | 2-5 tokens/s | 15-30 tokens/s |
| **Setup** | Complexe (quantization) | Simple (1 commande) |
| **Modèles** | Tous HF Hub | Liste Ollama |
| **Streaming** | Difficile | Natif |
| **API** | PyTorch direct | REST standard |

## 🔧 Troubleshooting

### Ollama n'est pas accessible

```bash
# Vérifier le service
curl http://localhost:11434/api/version

# Redémarrer Ollama (Windows)
# Chercher "Ollama" dans les services et redémarrer
```

### Modèle introuvable

```bash
# Lister les modèles installés
ollama list

# Télécharger le modèle
ollama pull mistral:7b-instruct
```

### Erreur de mémoire

```bash
# Utiliser une version quantifiée
ollama pull mistral:7b-instruct-q4_0

# Ou un modèle plus petit
ollama pull phi3:mini
```

### Réponses lentes

```python
# Réduire max_tokens
config = OllamaConfig(
    model="mistral:7b-instruct",
    max_tokens=256  # Au lieu de 512
)
```

## 📈 Optimisations

### 1. Utiliser le Streaming

```python
# Pour affichage temps réel
for chunk in llm.generate_stream(prompt, system_prompt):
    print(chunk, end='', flush=True)
```

### 2. Cache des Prompts

Ollama cache automatiquement les prompts système pour accélérer les réponses suivantes.

### 3. Batch Processing

```python
# Pour traiter plusieurs requêtes
responses = []
for query in queries:
    response = llm.generate(query)
    responses.append(response)
```

## 🎯 Modèles Recommandés par Use Case

| Use Case | Modèle | Raison |
|----------|--------|--------|
| **Général** | `mistral:7b-instruct` | Équilibré vitesse/qualité |
| **Qualité max** | `llama3:8b-instruct` | Meilleure compréhension |
| **Vitesse max** | `phi3:mini` | Ultra-rapide, petit |
| **Français** | `mistral:7b-instruct` | Excellent en français |
| **Code** | `codellama:7b-instruct` | Optimisé pour code |

## 📚 Ressources

- Documentation Ollama: https://ollama.com/docs
- Modèles disponibles: https://ollama.com/library
- GitHub: https://github.com/ollama/ollama

---

**Prochaine étape**: Créer l'adaptateur Ollama en exécutant :
```bash
python -m src.rag.llm.create_ollama_adapter
```
