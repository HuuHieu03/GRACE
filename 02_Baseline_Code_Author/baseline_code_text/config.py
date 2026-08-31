"""
GRACE Framework Configuration Module
Tự động nhận diện môi trường (Local / Kaggle GPU), quản lý đường dẫn và cấu hình hệ thống.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def is_kaggle_environment() -> bool:
    """Kiểm tra xem mã nguồn đang chạy trong môi trường Kaggle hay Local."""
    return os.path.exists("/kaggle/working") or "KAGGLE_URL_BASE" in os.environ


@dataclass
class ProjectConfig:
    """Cấu hình toàn cục cho hệ thống GRACE."""
    
    # Môi trường
    is_kaggle: bool = field(default_factory=is_kaggle_environment)
    
    # Đường dẫn gốc
    base_dir: Path = field(default_factory=lambda: Path("/kaggle/working") if is_kaggle_environment() else Path(__file__).parent.resolve())
    
    # Thư mục dữ liệu & Checkpoints
    data_dir: Path = field(init=False)
    checkpoint_dir: Path = field(init=False)
    output_dir: Path = field(init=False)
    
    # Cấu hình Dataset trên Hugging Face
    hf_dataset_devign: str = "DetectVul/devign"
    hf_dataset_bigvul: str = "bstee615/bigvul"
    default_sample_ratio: float = 0.05  # Mặc định 5% cho thử nghiệm nhanh
    random_seed: int = 42
    
    # Cấu hình LLM & GPU
    default_llm_model: str = "gemma-4-26B-A4B-it"
    fallback_llm_model: str = "Llama-3.3-70B-Instruct"
    use_4bit_quantization: bool = False  # Not needed for API
    device: str = "cuda" if is_kaggle_environment() else "cpu"
    
    def __post_init__(self):
        """Khởi tạo đường dẫn động tùy thuộc môi trường."""
        if self.is_kaggle:
            self.data_dir = Path("/kaggle/temp/data")
            self.checkpoint_dir = Path("/kaggle/working/checkpoints")
            self.output_dir = Path("/kaggle/working/output")
        else:
            self.data_dir = self.base_dir / "data"
            self.checkpoint_dir = self.base_dir / "checkpoints"
            self.output_dir = self.base_dir / "output"
            
        # Tạo sẵn các thư mục nếu chưa tồn tại
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_api_key(self, key_name: str = "FPT_API_KEY") -> Optional[str]:
        """Lấy API Key từ biến môi trường hoặc Kaggle Secrets."""
        api_key = os.getenv(key_name)
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY") # Fallback
        if not api_key and self.is_kaggle:
            try:
                from kaggle_secrets import UserSecretsClient
                user_secrets = UserSecretsClient()
                api_key = user_secrets.get_secret(key_name)
                if not api_key:
                    api_key = user_secrets.get_secret("OPENAI_API_KEY")
            except Exception:
                pass
        return api_key

    def get_base_url(self, key_name: str = "FPT_BASE_URL") -> Optional[str]:
        """Lấy Base URL từ biến môi trường hoặc Kaggle Secrets."""
        base_url = os.getenv(key_name)
        if not base_url and self.is_kaggle:
            try:
                from kaggle_secrets import UserSecretsClient
                user_secrets = UserSecretsClient()
                base_url = user_secrets.get_secret(key_name)
            except Exception:
                pass
        if not base_url:
            base_url = "https://mkp-api.fptcloud.com"
        return base_url


# Singleton config mặc định
config = ProjectConfig()
