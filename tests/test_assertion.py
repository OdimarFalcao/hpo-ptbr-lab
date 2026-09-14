import pytest

from hpo_ptbr.assertion import PortugueseContextCueClassifier


@pytest.mark.parametrize(
    ("text", "mention", "expected"),
    [
        ("Há histórico familiar de tremor.", "tremor", "family_history"),
        ("A família relata ocorrência de ptose.", "ptose", "family_history"),
        ("Permanece a hipótese de ataxia.", "ataxia", "uncertain"),
        ("Ainda se investiga diplopia.", "diplopia", "uncertain"),
        ("Não há evidência de edema.", "edema", "absent"),
        ("O registro nega escoliose.", "escoliose", "absent"),
        ("A avaliação documenta parestesia.", "parestesia", "present"),
    ],
)
def test_classifies_portuguese_context_cues(text, mention, expected):
    start = text.index(mention)

    observed = PortugueseContextCueClassifier().predict(
        text,
        start,
        start + len(mention),
    )

    assert observed == expected


def test_limits_context_to_current_sentence():
    text = "Não há evidência de edema. A avaliação documenta parestesia."
    mention = "parestesia"
    start = text.index(mention)

    observed = PortugueseContextCueClassifier().predict(
        text,
        start,
        start + len(mention),
    )

    assert observed == "present"


def test_rejects_invalid_offsets():
    with pytest.raises(ValueError, match="Offsets inválidos"):
        PortugueseContextCueClassifier().predict("texto", -1, 2)
