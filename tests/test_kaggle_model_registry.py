"""Unit tests cho Kaggle Modular Model Registry và Host Runner (Bước 1)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts.kaggle_host_runner import (
    build_server_command,
    export_backend_yaml,
    find_registry_config,
    inspect_hardware,
    load_registry,
)


@pytest.fixture
def registry():
    reg_path = find_registry_config()
    return load_registry(reg_path)


def test_registry_schema_and_metadata(registry):
    assert "version" in registry
    assert "default_model" in registry
    assert "default_engine" in registry
    assert "hardware_profiles" in registry
    assert "models" in registry

    # Kiểm tra hardware profiles
    hw = registry["hardware_profiles"]
    assert "kaggle_2xt4" in hw
    assert hw["kaggle_2xt4"]["total_vram_gb"] == 32.0
    assert hw["kaggle_2xt4"]["supports_tensor_parallel"] is True
    assert "kaggle_1xp100" in hw
    assert hw["kaggle_1xp100"]["total_vram_gb"] == 16.0


def test_registered_models_exist(registry):
    models = registry["models"]
    expected_models = [
        "qwen2.5-coder-7b-instruct",
        "qwen2.5-coder-14b-instruct",
        "qwen2.5-coder-32b-instruct",
        "qwen3-coder-30b-a3b-instruct",
    ]
    for m in expected_models:
        assert m in models, f"Model {m} chưa được đăng ký trong registry!"
        mcfg = models[m]
        assert "hf_repo" in mcfg
        assert "engines" in mcfg
        assert "llamacpp" in mcfg["engines"]
        assert mcfg["engines"]["llamacpp"]["supported"] is True


def test_command_builder_llamacpp(registry):
    # 7B Model llamacpp
    cmd_7b = build_server_command(
        registry,
        model_id="qwen2.5-coder-7b-instruct",
        engine="llamacpp",
        model_path_or_repo="models/qwen2.5-coder-7b-instruct-q4_k_m.gguf",
        port=8080,
    )
    cmd_str_7b = " ".join(cmd_7b)
    assert "--port 8080" in cmd_str_7b
    assert "--ctx-size 8192" in cmd_str_7b
    assert "models/qwen2.5-coder-7b-instruct-q4_k_m.gguf" in cmd_str_7b

    # 32B Model llamacpp trên 2xT4: phải có split-mode layer
    cmd_32b = build_server_command(
        registry,
        model_id="qwen2.5-coder-32b-instruct",
        engine="llamacpp",
        model_path_or_repo="models/qwen2.5-coder-32b-instruct-q4_k_m.gguf",
        port=8080,
    )
    cmd_str_32b = " ".join(cmd_32b)
    assert "--split-mode layer" in cmd_str_32b


def test_command_builder_vllm(registry):
    # 32B Model vllm: phải có tensor-parallel-size 2
    cmd_vllm = build_server_command(
        registry,
        model_id="qwen2.5-coder-32b-instruct",
        engine="vllm",
        model_path_or_repo="Qwen/Qwen2.5-Coder-32B-Instruct-AWQ",
        port=8080,
    )
    cmd_str_vllm = " ".join(cmd_vllm)
    assert "vllm serve" in cmd_str_vllm
    assert "--tensor-parallel-size 2" in cmd_str_vllm
    assert "--quantization awq" in cmd_str_vllm


def test_command_builder_transformers(registry):
    cmd_trans = build_server_command(
        registry,
        model_id="qwen2.5-coder-7b-instruct",
        engine="transformers",
        model_path_or_repo="Qwen/Qwen2.5-Coder-7B-Instruct",
        port=8080,
    )
    cmd_str_trans = " ".join(cmd_trans)
    assert "--serve-transformers" in cmd_str_trans
    assert "--port 8080" in cmd_str_trans


def test_export_backend_yaml(tmp_path):
    out_yaml = tmp_path / "backend_test.yaml"
    export_backend_yaml(
        output_path=out_yaml,
        base_url="https://demo.trycloudflare.com/v1",
        model_alias="qwen2.5-coder-7b-instruct",
        kind="llamacpp",
        top_logprobs=5,
    )
    assert out_yaml.exists()
    loaded = yaml.safe_load(out_yaml.read_text(encoding="utf-8"))
    assert "backend" in loaded
    b = loaded["backend"]
    assert b["base_url"] == "https://demo.trycloudflare.com/v1"
    assert b["model"] == "qwen2.5-coder-7b-instruct"
    assert b["top_logprobs"] == 5
    assert b["temperature"] == 0.0


def test_kaggle_notebook_structure():
    notebook_paths = [
        Path("kaggle_notebooks/host_llm_kaggle_server.ipynb"),
        Path("kaggle_notebooks/host_llm/host_llm_kaggle_server.ipynb"),
    ]
    for nb_path in notebook_paths:
        assert nb_path.exists(), f"Tệp notebook {nb_path} không tồn tại!"
        data = json.loads(nb_path.read_text(encoding="utf-8"))
        assert "cells" in data
        assert len(data["cells"]) >= 10

        # Kiểm tra các ô cốt lõi
        sources = ["".join(c.get("source", [])) for c in data["cells"]]
        combined = "\n".join(sources)
        assert "SELECTED_MODEL" in combined
        assert "SELECTED_ENGINE" in combined
        assert "MODEL_REGISTRY" in combined
        assert "llama-server" in combined or "llama_cpp.server" in combined
        assert "localhost" in combined or "127.0.0.1" in combined or "cloudflared" in combined
        assert "curl" in combined
        assert "vllm" in combined
        assert "top_logprobs" in combined
        assert "p1 / (p0 + p1)" in combined

