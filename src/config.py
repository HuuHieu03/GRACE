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
    base_dir: Path = field(default_factory=lambda: Path("/kaggle/working") if is_kaggle_environment() else (Path(__file__).parent.parent.resolve() if Path(__file__).parent.name == "src" else Path(__file__).parent.resolve()))
    
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

    # Cấu hình Vertex AI (Google Cloud Platform) tuân thủ evaluation_contract.yaml
    vertex_project_id: str = "grace-research-2903"
    vertex_location: str = "us-south1"
    vertex_model: str = "publishers/qwen/models/qwen3-coder-480b-a35b-instruct-maas"
    
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

        # Tự động nạp Vertex AI credentials nếu có sẵn
        try:
            setup_vertex_credentials()
        except Exception:
            pass

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

    def setup_vertex_credentials(self, custom_key_path: Optional[str] = None, project_root_dir: Optional[Path] = None) -> Optional[str]:
        """Phương thức helper gắn với instance ProjectConfig."""
        return setup_vertex_credentials(custom_key_path, project_root_dir or self.base_dir)

    def setup_gcp_credentials(self, custom_key_path: Optional[str] = None, project_root_dir: Optional[Path] = None) -> Optional[str]:
        """Alias cho setup_vertex_credentials."""
        return setup_vertex_credentials(custom_key_path, project_root_dir or self.base_dir)


def setup_vertex_credentials(
    custom_key_path: Optional[str] = None,
    project_root_dir: Optional[Path] = None
) -> Optional[str]:
    """
    Nạp Service Account Credentials cho Google Cloud Vertex AI:
    - Trên Kaggle: Đọc secret GCP_SA_KEY qua kaggle_secrets.UserSecretsClient().get_secret("GCP_SA_KEY"),
      ghi vào file tạm /tmp/gcp_sa_key.json và set biến môi trường GOOGLE_APPLICATION_CREDENTIALS.
    - Trên Local: Ưu tiên GOOGLE_APPLICATION_CREDENTIALS, nếu chưa có tự động fallback tìm file
      grace-research-*.json trong Downloads hoặc project root, sao chép an toàn vào .gcp_key.json (được gitignore).
    Returns:
        Đường dẫn file credential (str) hoặc None nếu không tìm thấy.
    """
    import shutil

    # 0. Nếu người dùng chỉ định đường dẫn cụ thể
    if custom_key_path:
        p = Path(custom_key_path)
        if p.exists():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(p.resolve())
            return str(p.resolve())

    # 1. Trên Kaggle: Nạp từ Kaggle Secret "GCP_SA_KEY"
    if is_kaggle_environment():
        try:
            from kaggle_secrets import UserSecretsClient
            user_secrets = UserSecretsClient()
            sa_key_str = user_secrets.get_secret("GCP_SA_KEY")
            if sa_key_str:
                tmp_dir = Path("/tmp")
                tmp_dir.mkdir(parents=True, exist_ok=True)
                tmp_key_file = tmp_dir / "gcp_sa_key.json"
                with open(tmp_key_file, "w", encoding="utf-8") as f:
                    f.write(sa_key_str.strip())
                try:
                    os.chmod(tmp_key_file, 0o600)
                except Exception:
                    pass
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(tmp_key_file)
                return str(tmp_key_file)
        except Exception:
            pass

    # 2. Trên Local: Ưu tiên GOOGLE_APPLICATION_CREDENTIALS nếu đang trỏ tới file tồn tại
    env_cred = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if env_cred and Path(env_cred).exists():
        return str(Path(env_cred).resolve())

    # 3. Kiểm tra .gcp_key.json tại project root
    project_root = project_root_dir or (Path(__file__).parent.parent.resolve() if Path(__file__).parent.name == "src" else Path(__file__).parent.resolve())
    cached_key = project_root / ".gcp_key.json"
    if cached_key.exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(cached_key.resolve())
        return str(cached_key.resolve())

    # 4. Fallback tự động tìm file grace-research-*.json trong Downloads hoặc project root
    search_dirs = [
        project_root,
        Path.cwd(),
        Path.home() / "Downloads"
    ]
    userprofile = os.getenv("USERPROFILE")
    if userprofile:
        search_dirs.append(Path(userprofile) / "Downloads")

    for s_dir in search_dirs:
        try:
            if s_dir.exists():
                matches = list(s_dir.glob("grace-research-*.json"))
                if matches:
                    src_file = matches[0]
                    try:
                        shutil.copy2(src_file, cached_key)
                        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(cached_key.resolve())
                        return str(cached_key.resolve())
                    except Exception:
                        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(src_file.resolve())
                        return str(src_file.resolve())
        except Exception:
            pass

    return None


setup_gcp_credentials = setup_vertex_credentials

# Singleton config mặc định
config = ProjectConfig()

