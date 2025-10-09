"""
GPU Configuration for RTX 3090 optimization
"""
import torch
import os
from dataclasses import dataclass
from typing import Dict, Optional
from pathlib import Path

@dataclass
class GPUConfig:
    """Configuration for GPU resource management"""

    # Device settings
    device_id: int = 0
    device_name: str = "cuda:0"
    total_vram_gb: int = 24

    # Model memory allocations (in GB)
    vram_allocation: Dict[str, float] = None

    # Optimization settings
    use_flash_attention: bool = True
    use_mixed_precision: bool = True
    use_gradient_checkpointing: bool = True
    max_batch_size: int = 8

    # Quantization settings
    use_quantization: bool = True
    quantization_bits: int = 4

    # Cache settings
    cache_dir: Path = Path("./models/cache")
    use_kv_cache: bool = True

    def __post_init__(self):
        if self.vram_allocation is None:
            self.vram_allocation = {
                "llm": 8.0,          # Mistral-7B 4-bit (plus de VRAM disponible)
                "embeddings": 3.0,   # BGE-M3 avec batches plus larges
                "ner": 4.0,          # CamemBERT-NER + spaCy GPU
                "faiss": 3.0,        # FAISS GPU index plus large
                "reranker": 2.0,     # Cross-encoder
                "buffer": 4.0,       # Safety buffer + PyTorch overhead
            }

    def get_available_vram(self) -> float:
        """Get currently available VRAM in GB"""
        if torch.cuda.is_available():
            return torch.cuda.get_device_properties(0).total_memory / 1024**3
        return 0

    def check_vram_usage(self) -> Dict[str, float]:
        """Check current VRAM usage"""
        if not torch.cuda.is_available():
            return {"error": "CUDA not available"}

        allocated = torch.cuda.memory_allocated() / 1024**3
        reserved = torch.cuda.memory_reserved() / 1024**3
        free = self.total_vram_gb - reserved

        return {
            "allocated_gb": round(allocated, 2),
            "reserved_gb": round(reserved, 2),
            "free_gb": round(free, 2),
            "utilization_percent": round((reserved / self.total_vram_gb) * 100, 1)
        }

    def optimize_for_model(self, model_type: str) -> Dict:
        """Get optimized settings for specific model type"""

        optimizations = {
            "llm": {
                "dtype": torch.float16,
                "quantization": "4bit",
                "max_new_tokens": 2048,
                "use_flash_attention_2": True,
                "load_in_4bit": True,
                "bnb_4bit_compute_dtype": torch.float16,
                "bnb_4bit_use_double_quant": True,
                "bnb_4bit_quant_type": "nf4"
            },
            "embeddings": {
                "dtype": torch.float16,
                "batch_size": 64,
                "max_length": 512,
                "normalize": True
            },
            "ner": {
                "dtype": torch.float16,
                "batch_size": 32,
                "max_length": 512
            },
            "faiss": {
                "index_type": "IVF16384,PQ64",
                "nprobe": 64,
                "use_gpu": True,
                "device": self.device_id
            }
        }

        return optimizations.get(model_type, {})

    def setup_cuda_environment(self):
        """Configure CUDA environment variables"""
        # Enable TF32 for better performance on Ampere
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True

        # Set memory fraction
        torch.cuda.set_per_process_memory_fraction(0.95)

        # Enable cudnn benchmarking for CNNs
        torch.backends.cudnn.benchmark = True

        # Set CUDA device
        torch.cuda.set_device(self.device_id)

        # Environment variables
        os.environ["CUDA_VISIBLE_DEVICES"] = str(self.device_id)
        os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:512"

        print(f"✓ CUDA environment configured for {torch.cuda.get_device_name()}")
        print(f"✓ Available VRAM: {self.get_available_vram():.1f} GB")

class ModelManager:
    """Manage multiple models on GPU with memory allocation"""

    def __init__(self, config: GPUConfig):
        self.config = config
        self.loaded_models = {}
        self.memory_tracker = {}

    def load_model(self, model_name: str, model_loader_fn, model_type: str):
        """Load a model with memory tracking"""

        # Check if enough VRAM available
        required_vram = self.config.vram_allocation.get(model_type, 2.0)
        current_usage = self.config.check_vram_usage()

        if current_usage["free_gb"] < required_vram:
            # Try to free memory
            self.cleanup_memory()
            current_usage = self.config.check_vram_usage()

            if current_usage["free_gb"] < required_vram:
                raise RuntimeError(
                    f"Insufficient VRAM. Required: {required_vram}GB, "
                    f"Available: {current_usage['free_gb']}GB"
                )

        # Get optimized settings
        settings = self.config.optimize_for_model(model_type)

        # Load model
        print(f"Loading {model_name} with {model_type} settings...")
        model = model_loader_fn(**settings)

        # Track memory usage
        self.loaded_models[model_name] = model
        self.memory_tracker[model_name] = {
            "type": model_type,
            "allocated_gb": required_vram,
            "loaded_at": torch.cuda.memory_allocated() / 1024**3
        }

        print(f"✓ {model_name} loaded. Current VRAM: {self.config.check_vram_usage()}")
        return model

    def unload_model(self, model_name: str):
        """Unload a model and free VRAM"""
        if model_name in self.loaded_models:
            del self.loaded_models[model_name]
            del self.memory_tracker[model_name]
            self.cleanup_memory()
            print(f"✓ {model_name} unloaded")

    def cleanup_memory(self):
        """Force cleanup of GPU memory"""
        import gc
        gc.collect()
        torch.cuda.empty_cache()
        torch.cuda.synchronize()

    def get_memory_summary(self) -> Dict:
        """Get summary of memory usage by model"""
        summary = {
            "models": self.memory_tracker,
            "current_usage": self.config.check_vram_usage(),
            "loaded_models": list(self.loaded_models.keys())
        }
        return summary

# Singleton instance
gpu_config = GPUConfig()
model_manager = ModelManager(gpu_config)

# Initialize on import
if torch.cuda.is_available():
    gpu_config.setup_cuda_environment()
else:
    print("⚠ CUDA not available. Running in CPU mode.")