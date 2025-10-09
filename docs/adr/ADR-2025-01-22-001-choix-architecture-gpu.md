# ADR-2025-01-22-001: Choix d'Architecture pour Exploitation GPU RTX 3090

## Statut
Proposé

## Contexte
Nous développons un système RAG pour l'analyse de conversations professionnelles qui doit traiter des volumes importants de données (audio, texte, métadonnées) en temps réel. Nous disposons d'une NVIDIA RTX 3090 avec 24GB de VRAM que nous devons exploiter efficacement pour maximiser les performances tout en gérant plusieurs modèles d'IA simultanément.

## Décision
Nous adoptons une architecture hybride GPU/CPU avec:
1. **Modèles quantifiés 4-bit** pour le LLM principal (Mistral-7B)
2. **Pipeline de batching dynamique** pour maximiser le throughput GPU
3. **Architecture multi-modèle** avec allocation VRAM fixe par service
4. **FAISS-GPU** pour la recherche vectorielle haute performance
5. **Orchestration via Ray** pour la gestion des ressources GPU

## Justification
- La RTX 3090 offre un excellent rapport performance/coût pour l'inférence locale
- 24GB VRAM permet de charger plusieurs modèles simultanément
- La quantification 4-bit réduit l'usage VRAM de 75% avec perte minimale de qualité
- FAISS-GPU offre 10-100x speedup vs CPU pour la recherche vectorielle
- Ray permet une allocation dynamique et évite les conflits de ressources

## Alternatives considérées

### Option 1: Cloud GPU (A100/H100)
**Description**: Utiliser des GPUs cloud haute performance
**Avantages**:
- Plus de VRAM (40-80GB)
- Pas de maintenance hardware
- Scalabilité élastique

**Inconvénients**:
- Coût récurrent élevé (~2-4$/heure)
- Latence réseau
- Dépendance externe
- Problèmes de confidentialité des données

### Option 2: CPU-only avec modèles optimisés
**Description**: Utiliser uniquement CPU avec ONNX/OpenVINO
**Avantages**:
- Pas de limite VRAM
- Plus simple à déployer
- Moins de dépendances

**Inconvénients**:
- 10-50x plus lent
- Pas viable pour temps réel
- Limite la taille des modèles utilisables

### Option 3: Cluster multi-GPU local
**Description**: Plusieurs GPUs consumer (RTX 4070/4080)
**Avantages**:
- Parallélisation possible
- Redondance
- Scalabilité locale

**Inconvénients**:
- Coût initial élevé
- Complexité de gestion
- Consommation électrique
- Overhead de communication inter-GPU

## Conséquences

### Positives
- **Performance**: 10-50x speedup vs CPU sur toutes les opérations
- **Coût**: Pas de frais récurrents cloud (ROI en 3-4 mois)
- **Confidentialité**: Données restent on-premise
- **Latence**: <100ms pour la plupart des opérations
- **Flexibilité**: Contrôle total sur les modèles et optimisations

### Négatives
- **Limite VRAM**: Max 2-3 modèles large simultanément
- **Single point of failure**: Si GPU fail, système down
- **Maintenance**: Gestion drivers CUDA, cooling, etc.
- **Évolutivité limitée**: Scale-up difficile sans hardware additionnel

### Neutres
- Formation équipe sur optimisations GPU
- Monitoring VRAM/température nécessaire
- Backup strategy CPU pour failover

## Implémentation

### Plan d'action
1. **Setup environnement CUDA** (Semaine 1)
   - CUDA 12.1 + cuDNN 8.9
   - PyTorch 2.1 avec support GPU
   - Installation drivers 545.x

2. **Optimisation modèles** (Semaine 2)
   - Quantification Mistral-7B en 4-bit GPTQ
   - Configuration Whisper avec batch processing
   - Setup FAISS-GPU avec index IVF

3. **Pipeline orchestration** (Semaine 3)
   - Deployment Ray cluster
   - Configuration resource allocation
   - Setup monitoring (nvidia-smi, prometheus)

4. **Testing & Benchmarks** (Semaine 4)
   - Load testing avec données réelles
   - Profiling VRAM usage
   - Optimization bottlenecks

### Architecture VRAM Budget

```yaml
vram_allocation:
  whisper_large_v3: 6GB (float16)
  mistral_7b_gptq: 4GB (4-bit)
  bge_m3_embeddings: 2GB
  camembert_ner: 3GB
  faiss_index: 2GB
  pytorch_overhead: 2GB
  buffer: 5GB
  total: 24GB
```

### Configuration Ray

```python
# ray_config.py
import ray

ray.init(
    num_gpus=1,
    object_store_memory=8_000_000_000,  # 8GB
    _system_config={
        "automatic_object_spilling_enabled": True,
        "object_spilling_config": json.dumps({
            "type": "filesystem",
            "params": {"directory_path": "/tmp/spill"}
        })
    }
)

# Resource allocation per service
@ray.remote(num_gpus=0.3)
class WhisperService:
    pass

@ray.remote(num_gpus=0.4)
class LLMService:
    pass

@ray.remote(num_gpus=0.2)
class EmbeddingService:
    pass

@ray.remote(num_gpus=0.1)
class NERService:
    pass
```

### Monitoring Setup

```yaml
monitoring:
  metrics:
    - gpu_utilization
    - vram_usage
    - temperature
    - power_draw
    - inference_latency
    - throughput

  alerts:
    - vram_usage > 22GB
    - temperature > 83°C
    - gpu_utilization < 20% (underutilized)
    - inference_latency > 500ms

  tools:
    - nvidia-smi daemon
    - prometheus gpu exporter
    - grafana dashboards
    - custom ray metrics
```

## Références
- [NVIDIA Deep Learning Performance Guide](https://docs.nvidia.com/deeplearning/performance/index.html)
- [Quantization Impact on LLM Performance](https://arxiv.org/abs/2309.05210)
- [FAISS GPU Documentation](https://github.com/facebookresearch/faiss/wiki/Faiss-on-the-GPU)
- [Ray GPU Scheduling](https://docs.ray.io/en/latest/ray-core/scheduling/gpu.html)

## Notes
- Prévoir upgrade vers RTX 4090/5090 si besoins augmentent
- Considérer TensorRT pour optimisations supplémentaires
- Monitoring température critique en été
- Backup sur CPU avec modèles GGML en cas de failure GPU

---
**Date**: 2025-01-22
**Auteur**: Architecture Team
**Reviewers**: [Tech Lead, DevOps Lead]