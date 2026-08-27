"""
BERT Whitening - Re-implementation based on Su et al. 2021
"Whitening Sentence Representations for Better Semantics and Faster Retrieval"

This module provides functions to:
1. Encode sentences (code) into vectors using a pretrained model (CodeT5/RoBERTa)
2. Compute whitening kernel and bias from training vectors
3. Apply whitening transformation and L2 normalization
"""

import numpy as np
import torch


def sents_to_vecs(sents, tokenizer, model, max_length=512):
    """
    Encode a list of sentences/code into vectors using a pretrained model.
    Uses the [CLS] token (first token) representation.
    
    Args:
        sents: list of strings (code snippets)
        tokenizer: HuggingFace tokenizer
        model: HuggingFace model (RoBERTa/CodeT5)
        max_length: max token length
    
    Returns:
        numpy array of shape (len(sents), hidden_dim)
    """
    device = next(model.parameters()).device
    vecs = []
    
    with torch.no_grad():
        for sent in sents:
            inputs = tokenizer(
                sent, 
                return_tensors='pt', 
                max_length=max_length, 
                truncation=True, 
                padding=True
            ).to(device)
            
            outputs = model(**inputs)
            # Use [CLS] token representation (first token)
            cls_vec = outputs.last_hidden_state[:, 0, :].cpu().numpy()
            vecs.append(cls_vec)
    
    vecs = np.concatenate(vecs, axis=0)
    return vecs


def compute_kernel_bias(vecs, n_components=256):
    """
    Compute the whitening kernel and bias.
    
    The whitening transformation is:
        new_vec = (vec - bias) @ kernel
    
    Where kernel is derived from SVD of the covariance matrix.
    
    Args:
        vecs: numpy array of shape (n_samples, hidden_dim)
        n_components: target dimension after whitening
    
    Returns:
        kernel: numpy array of shape (hidden_dim, n_components)
        bias: numpy array of shape (1, hidden_dim) - the mean vector
    """
    # Compute mean (bias)
    mu = vecs.mean(axis=0, keepdims=True)
    
    # Center the vectors
    centered = vecs - mu
    
    # Compute covariance matrix
    cov = np.cov(centered.T)
    
    # SVD decomposition
    u, s, vh = np.linalg.svd(cov)
    
    # Whitening kernel: U @ diag(1/sqrt(S))
    # Take only the first n_components
    W = u[:, :n_components] @ np.diag(1.0 / np.sqrt(s[:n_components] + 1e-8))
    
    return W, mu


def transform_and_normalize(vecs, kernel, bias):
    """
    Apply whitening transformation and L2 normalization.
    
    Args:
        vecs: numpy array of shape (n_samples, hidden_dim)
        kernel: whitening kernel from compute_kernel_bias
        bias: mean vector from compute_kernel_bias
    
    Returns:
        numpy array of shape (n_samples, n_components), L2 normalized
    """
    # Apply whitening: (vec - mean) @ kernel
    transformed = (vecs - bias) @ kernel
    
    # L2 normalize
    norms = np.linalg.norm(transformed, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-8)  # avoid division by zero
    normalized = transformed / norms
    
    return normalized
