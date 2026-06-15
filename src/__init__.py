"""Overlap-aware speaker-attributed ASR project package.

Keep package import lightweight so ``python -m src.<module>`` works in
minimal environments where optional repair-loop dependencies are absent.
"""


def run_repair_loop_all(*args, **kwargs):
    from .llm_repair_loop import run_repair_loop_all as _fn

    return _fn(*args, **kwargs)


def run_repair_loop_offline(*args, **kwargs):
    from .llm_repair_loop import run_repair_loop_offline as _fn

    return _fn(*args, **kwargs)


def build_reference_knowledge_base(*args, **kwargs):
    from .rag_repair import build_reference_knowledge_base as _fn

    return _fn(*args, **kwargs)


def retrieve_relevant_segments(*args, **kwargs):
    from .rag_repair import retrieve_relevant_segments as _fn

    return _fn(*args, **kwargs)


def compute_feature_importance(*args, **kwargs):
    from .router_feature_importance import compute_feature_importance as _fn

    return _fn(*args, **kwargs)
