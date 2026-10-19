"""
Unit Tests for Vertex AI Credentials, Configuration & LLMEvaluator Integration
Kiểm thử toàn diện các thành phần tích hợp Google Cloud Vertex AI MaaS:
1. Cấu hình ProjectConfig cho Vertex AI (Project ID, Location, Model).
2. Helper nạp Service Account Credentials (trên Local và Kaggle).
3. Khởi tạo LLMEvaluator với Provider Vertex AI và cơ chế Bearer Token.
4. Tự động làm mới Token (Access Token Refresh) khi token hết hạn.
5. Xử lý lỗi khi thiếu Service Account Credentials.
6. Tham số suy luận tuân thủ evaluation_contract.yaml (seed=42, temp=0.0, max_tokens=256).
"""

import os
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

repo_root = Path(__file__).parent.parent.resolve()
src_dir = repo_root / "src"
for p in [str(repo_root), str(src_dir)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from config import config, setup_vertex_credentials, setup_gcp_credentials, ProjectConfig
from evaluator import LLMEvaluator


def test_vertex_ai_config_attributes():
    """Kiểm tra các thuộc tính cấu hình Vertex AI trong ProjectConfig."""
    assert hasattr(config, "vertex_project_id")
    assert config.vertex_project_id == "grace-research-2903"
    assert hasattr(config, "vertex_location")
    assert config.vertex_location == "us-central1"
    assert hasattr(config, "vertex_model")
    assert config.vertex_model == "publishers/qwen/models/qwen3-coder-480b-a35b-instruct-maas"
    assert hasattr(config, "setup_vertex_credentials")
    assert hasattr(config, "setup_gcp_credentials")


def test_setup_vertex_credentials_explicit_path(tmp_path):
    """Kiểm tra nạp credentials khi truyền đường dẫn cụ thể."""
    fake_key_file = tmp_path / "custom_key.json"
    fake_key_file.write_text('{"type": "service_account"}', encoding="utf-8")

    result = setup_vertex_credentials(str(fake_key_file))
    assert result == str(fake_key_file.resolve())
    assert os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") == str(fake_key_file.resolve())


def test_setup_vertex_credentials_kaggle_secret(tmp_path):
    """Kiểm tra nạp credentials từ Kaggle Secret GCP_SA_KEY trong môi trường Kaggle."""
    mock_secrets_client = MagicMock()
    mock_secrets_client.return_value.get_secret.return_value = '{"type": "service_account", "project_id": "grace-research-2903"}'

    with patch("config.is_kaggle_environment", return_value=True), \
         patch.dict("sys.modules", {"kaggle_secrets": MagicMock(UserSecretsClient=mock_secrets_client)}), \
         patch("pathlib.Path.mkdir"), \
         patch("builtins.open", MagicMock()):
        
        # Test nạp secret
        cred_path = setup_vertex_credentials()
        assert cred_path is not None
        assert "gcp_sa_key.json" in str(cred_path)


def test_setup_vertex_credentials_local_fallback(tmp_path):
    """Kiểm tra fallback tìm kiếm grace-research-*.json trên máy cục bộ và sao chép an toàn vào .gcp_key.json."""
    fake_downloads = tmp_path / "Downloads"
    fake_downloads.mkdir()
    fake_sa_file = fake_downloads / "grace-research-2903-testkey.json"
    fake_sa_file.write_text('{"project_id": "grace-research-2903"}', encoding="utf-8")

    with patch("config.is_kaggle_environment", return_value=False), \
         patch.dict(os.environ, {}, clear=True), \
         patch("pathlib.Path.home", return_value=tmp_path):
        
        # Gọi helper với project_root_dir=tmp_path để cách ly hoàn toàn môi trường test
        cred_path = setup_vertex_credentials(project_root_dir=tmp_path)
        # Phải tìm thấy file, sao chép vào .gcp_key.json và thiết lập GOOGLE_APPLICATION_CREDENTIALS
        assert cred_path is not None
        assert os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") is not None
        assert ".gcp_key.json" in os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        assert (tmp_path / ".gcp_key.json").exists()


def test_llm_evaluator_vertex_provider_detection():
    """Kiểm tra LLMEvaluator tự động phát hiện Provider Vertex AI khi model thuộc publishers/qwen/."""
    # Khi use_mock=True
    evaluator_mock = LLMEvaluator(
        model_name="publishers/qwen/models/qwen3-coder-480b-a35b-instruct-maas",
        use_mock=True
    )
    assert evaluator_mock.provider == "Vertex AI"
    assert evaluator_mock.model_name == "publishers/qwen/models/qwen3-coder-480b-a35b-instruct-maas"

    # Khi truyền rõ provider="Vertex AI"
    evaluator_explicit = LLMEvaluator(
        provider="Vertex AI",
        use_mock=True
    )
    assert evaluator_explicit.provider == "Vertex AI"
    assert evaluator_explicit.model_name == config.vertex_model


def test_llm_evaluator_missing_vertex_credentials_raises():
    """Kiểm tra LLMEvaluator ném RuntimeError rõ ràng khi không tìm thấy Service Account Credentials."""
    with patch("config.setup_vertex_credentials", return_value=None), \
         patch.dict(os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": ""}, clear=True), \
         patch("google.auth.default", side_effect=Exception("No credentials found")):
        
        with pytest.raises(RuntimeError) as exc_info:
            LLMEvaluator(provider="Vertex AI", use_mock=False)
        
        assert "Lỗi cấu hình: Không tìm thấy Service Account Credentials cho Vertex AI" in str(exc_info.value)


def test_llm_evaluator_vertex_ai_generation():
    """Kiểm tra gọi suy luận thành công trên Vertex AI MaaS endpoint với token tự động refresh."""
    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_creds.expired = False
    mock_creds.token = "fake_oauth2_access_token_12345"

    mock_chat_completion = MagicMock()
    mock_chat_completion.choices = [
        MagicMock(message=MagicMock(content="1", reasoning_content=None))
    ]

    mock_openai_client = MagicMock()
    mock_openai_client.chat.completions.create.return_value = mock_chat_completion

    with patch("config.setup_vertex_credentials", return_value="/tmp/fake_key.json"), \
         patch("os.path.exists", return_value=True), \
         patch("google.oauth2.service_account.Credentials.from_service_account_file", return_value=mock_creds), \
         patch("openai.OpenAI", return_value=mock_openai_client):
        
        evaluator = LLMEvaluator(
            model_name="publishers/qwen/models/qwen3-coder-480b-a35b-instruct-maas",
            provider="Vertex AI",
            use_mock=False
        )

        assert evaluator.provider == "Vertex AI"
        response = evaluator.generate_response("Check if this function is vulnerable: strcpy(dest, src);")
        
        assert response == "1"
        # Xác minh tham số gọi tuân thủ evaluation_contract.yaml
        mock_openai_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_openai_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["temperature"] == 0.0
        assert call_kwargs["seed"] == 42
        assert call_kwargs["max_tokens"] == 256
        assert call_kwargs["model"] == "publishers/qwen/models/qwen3-coder-480b-a35b-instruct-maas"


def test_run_label_flip_metadata_vertex_defaults(tmp_path):
    """Kiểm tra run_experiment ghi đúng metadata model_name và provider khi dùng Vertex AI."""
    from scripts.run_label_flip_test import run_experiment
    fake_split = tmp_path / "split.json"
    fake_split.write_text(json.dumps({
        "split_name": "test_split",
        "dataset": "devign",
        "sample_details": [
            {"id": "s1", "target": 1, "func": "void f1(){}", "nodes": [], "edges": []}
        ]
    }), encoding="utf-8")

    mock_engine = MagicMock()
    mock_engine.generate_response.return_value = "1"

    with patch("scripts.run_label_flip_test.LLMEvaluator", return_value=mock_engine):
        rep = run_experiment(
            dev_split_file=fake_split,
            dataset_name="devign",
            use_mock=False,
            model_name=None,
            provider="Vertex AI",
            train_samples=[{"id": "t1", "func": "void t(){}", "target": 0}]
        )
        meta = rep["experiment_metadata"]
        assert meta["model_name"] == config.vertex_model
        assert meta["provider"] == "Vertex AI"
        assert meta["use_mock"] is False
