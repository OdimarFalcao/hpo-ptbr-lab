import pytest

from hpo_ptbr.sapbert import SapBertEncoder


def test_sapbert_validates_batch_configuration_before_loading_model() -> None:
    with pytest.raises(ValueError, match="batch_size"):
        SapBertEncoder(batch_size=0)
    with pytest.raises(ValueError, match="max_length"):
        SapBertEncoder(max_length=1)
