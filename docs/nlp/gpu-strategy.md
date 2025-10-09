# Stratégie GPU - RTX 3090

## Contraintes Matériel

### RTX 3090 Specs
- **VRAM**: 24GB GDDR6X
- **CUDA Cores**: 10496
- **Tensor Cores**: 328 (3rd gen)
- **Memory Bandwidth**: 936 GB/s
- **FP16 Performance**: ~35 TFLOPS
- **INT8 Performance**: ~142 TOPS

## Allocation VRAM

### Budget VRAM Total: 24GB

```
┌─────────────────────────────────────────┐
│           RTX 3090 - 24GB VRAM          │
├─────────────────────────────────────────┤
│                                         │
│  Embeddings Model (Dense)      4-6 GB  │
│  - multilingual-e5-large               │
│  - intfloat/multilingual-e5-large-instruct │
│                                         │
│  NER Model (SpaCy/Transformers) 2-3 GB  │
│  - fr_core_news_lg ou camembert-ner    │
│                                         │
│  Sentiment Model               1-2 GB   │
│  - nlptown/bert-base-multilingual      │
│                                         │
│  LLM (Inference - vLLM)        12-14 GB │
│  - mistral-7b-instruct (4-bit)         │
│  - ou llama-2-7b-chat (4-bit)          │
│                                         │
│  Working Memory                2-3 GB   │
│  - Batch processing buffers            │
│  - Kernel memory                       │
│                                         │
└─────────────────────────────────────────┘
```

## Modèles Sélectionnés

### 1. Embeddings - Dense Vector Search

**Choix: intfloat/multilingual-e5-large-instruct**

- **Dimensions**: 1024
- **Langues**: 100+ (incluant FR, EN)
- **VRAM**: ~5GB
- **Performance**:
  - Batch size 32: ~200 sequences/sec
  - Latence: ~15ms/sequence

**Alternative (plus léger)**:
- `sentence-transformers/paraphrase-multilingual-mpnet-base-v2`
- Dimensions: 768, VRAM: ~2GB

### 2. Embeddings - Sparse (BM25)

**Choix: Hybrid avec Qdrant built-in**

- Pas de VRAM requise (CPU-based)
- Utilisé pour keyword search
- Combiné avec dense pour hybrid search

### 3. NER (Named Entity Recognition)

**Choix: camembert-ner (français)**

- **Model**: camembert/camembert-ner
- **Entités**: PER, LOC, ORG, MISC
- **VRAM**: ~2GB
- **Performance**: ~500 tokens/sec

**Pour multilingue**:
- `Davlan/xlm-roberta-base-ner-hrl`
- Supporte 10 langues

### 4. Sentiment Analysis

**Choix: nlptown/bert-base-multilingual-uncased-sentiment**

- **Scores**: 1-5 étoiles
- **Langues**: 6 (EN, FR, DE, ES, IT, NL)
- **VRAM**: ~1.5GB
- **Performance**: ~400 sequences/sec

### 5. LLM pour Génération (RAG)

**Choix: TheBloke/Mistral-7B-Instruct-v0.2-GPTQ**

- **Quantization**: 4-bit GPTQ
- **VRAM**: ~5-6GB (vs 14GB FP16)
- **Context**: 8192 tokens
- **Performance**: ~40 tokens/sec
- **Framework**: vLLM + ExLlama v2

**Alternative**:
- `TheBloke/Llama-2-7B-Chat-GPTQ` (4-bit)

## Stratégies d'Optimisation

### 1. Model Loading Strategy

```python
# Option A: Tout en mémoire (utilisation continue)
class ModelManager:
    def __init__(self):
        self.embedder = load_model("multilingual-e5-large")      # 5GB
        self.ner_model = load_model("camembert-ner")             # 2GB
        self.sentiment_model = load_model("bert-sentiment")      # 1.5GB
        self.llm = load_model("mistral-7b-gptq")                 # 6GB
        # Total: ~14.5GB + 2GB working = 16.5GB
        # Reste: 7.5GB pour batching

# Option B: Load on-demand (latence plus élevée)
class LazyModelManager:
    def get_embedder(self):
        if not self.embedder_loaded:
            self.embedder = load_model(...)
        return self.embedder
```

**Recommandation**: Option A pour embeddings/NER/sentiment, Option B pour LLM

### 2. Batching Strategy

```python
# Embeddings: Batch size optimal
EMBEDDING_BATCH_SIZE = 32  # ~5GB VRAM usage
# Process 200 sequences/sec

# NER: Batch size
NER_BATCH_SIZE = 16  # ~2GB VRAM usage

# Sentiment: Batch size
SENTIMENT_BATCH_SIZE = 24
```

### 3. Mixed Precision

```python
# FP16 pour embeddings (2x faster, 1/2 memory)
model = AutoModel.from_pretrained(
    "intfloat/multilingual-e5-large-instruct",
    torch_dtype=torch.float16
)

# INT8 quantization pour NER
model = AutoModelForTokenClassification.from_pretrained(
    "camembert/camembert-ner",
    load_in_8bit=True
)
```

### 4. Model Offloading

Pour LLM (utilisé rarement):

```python
# Offload vers CPU quand non utilisé
import accelerate

model = AutoModelForCausalLM.from_pretrained(
    "mistral-7b-gptq",
    device_map="auto",  # Auto offload
    offload_folder="offload",
    offload_state_dict=True
)
```

### 5. Pipeline Séquentiel

```
Input Conversation
     ↓
1. Chunking (CPU)
     ↓
2. Embeddings (GPU - batch 32)
     ↓
3. Store in Qdrant (CPU)
     ↓
4. NER parallel (GPU - batch 16)
     ↓
5. Sentiment parallel (GPU - batch 24)
     ↓
6. Update metadata (CPU)
     ↓
Done
```

## Benchmarks Attendus

### RTX 3090 Performance Estimations

| Task | Model | Batch | Throughput | Latency |
|------|-------|-------|------------|---------|
| Embeddings | e5-large | 32 | 200 seq/s | 15ms |
| NER | camembert | 16 | 500 tok/s | 20ms |
| Sentiment | bert-multi | 24 | 400 seq/s | 25ms |
| LLM (RAG) | mistral-7b-4bit | 1 | 40 tok/s | 25ms/tok |

### Processing Time Examples

**Conversation moyenne (10 min, 120 turns)**:

1. Chunking: ~100ms (CPU)
2. Embeddings (120 chunks): ~600ms (GPU)
3. Qdrant indexing: ~200ms (CPU)
4. NER (120 turns): ~2.4s (GPU)
5. Sentiment (120 turns): ~3s (GPU)

**Total**: ~6.3 secondes

**Parallélisé**: ~3.5 secondes (NER + Sentiment parallel)

## Configuration Recommandée

### Development (Local RTX 3090)

```yaml
models:
  embeddings:
    name: "intfloat/multilingual-e5-large-instruct"
    dtype: "float16"
    batch_size: 32
    dimensions: 1024

  ner:
    name: "camembert/camembert-ner"
    quantization: "int8"
    batch_size: 16

  sentiment:
    name: "nlptown/bert-base-multilingual-uncased-sentiment"
    dtype: "float16"
    batch_size: 24

  llm:
    name: "TheBloke/Mistral-7B-Instruct-v0.2-GPTQ"
    quantization: "gptq-4bit"
    max_length: 8192
    load_strategy: "on_demand"

gpu:
  device: "cuda:0"
  memory_fraction: 0.95  # Use 95% of 24GB
  allow_growth: true
```

### Production (Cloud GPU)

Pour scale horizontal:

```yaml
# Option A: Dedicated GPUs per service
embeddings_gpu: A100-40GB (ou 2x RTX 3090)
ner_gpu: T4-16GB
llm_gpu: A100-80GB

# Option B: vLLM multi-GPU
llm_gpus: 4x A100-40GB (pour Mixtral 8x7B)
```

## Alternatives CPU-only

Si GPU non disponible:

1. **Embeddings**:
   - `sentence-transformers` avec ONNX Runtime
   - ~20x plus lent mais fonctionne

2. **NER**:
   - SpaCy `fr_core_news_lg` (CPU optimisé)
   - ~10x plus lent

3. **LLM**:
   - Appel API externe (OpenAI, Anthropic)
   - Ou llama.cpp (CPU inference)

## Migration Cloud

### AWS

```
Instance: g5.2xlarge
- GPU: 1x A10G (24GB)
- vCPU: 8
- RAM: 32GB
- Prix: ~$1.2/hour

Ou

Instance: p3.2xlarge
- GPU: 1x V100 (16GB) - moins de VRAM mais plus rapide
- Prix: ~$3/hour
```

### GCP

```
Instance: n1-standard-8 + 1x T4
- GPU: T4 (16GB) - suffisant sans LLM local
- Prix: ~$0.8/hour
```

## Monitoring GPU

Métriques à tracker:

```python
import pynvml

# GPU Utilization
pynvml.nvmlInit()
handle = pynvml.nvmlDeviceGetHandleByIndex(0)

gpu_util = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
memory_used_gb = memory_info.used / 1024**3
memory_total_gb = memory_info.total / 1024**3
temperature = pynvml.nvmlDeviceGetTemperature(handle, 0)

# Prometheus metrics
gpu_memory_used_bytes{device="cuda:0"}
gpu_utilization_percent{device="cuda:0"}
gpu_temperature_celsius{device="cuda:0"}
```

## Next Steps

1. ✅ Sélection modèles finalisée
2. [ ] Implémenter ModelManager avec lazy loading
3. [ ] Benchmarks réels RTX 3090
4. [ ] Optimisation batching
5. [ ] Tests de charge (concurrent requests)
6. [ ] Monitoring dashboard GPU
