import pytest

from hpo_ptbr.sapbert import DEFAULT_SAPBERT_MODEL_SHA256, SapBertEncoder


def test_sapbert_validates_batch_configuration_before_loading_model() -> None:
    with pytest.raises(ValueError, match="batch_size"):
        SapBertEncoder(batch_size=0)
    with pytest.raises(ValueError, match="max_length"):
        SapBertEncoder(max_length=1)


def test_sapbert_model_hash_is_sha256() -> None:
    assert len(DEFAULT_SAPBERT_MODEL_SHA256) == 64
    assert set(DEFAULT_SAPBERT_MODEL_SHA256) <= set("0123456789abcdef")
