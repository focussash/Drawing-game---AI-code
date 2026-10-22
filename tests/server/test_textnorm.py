from server.textnorm import mask, normalize, word_length


def test_normalize_strips_space_punct_and_folds_width_case():
    assert normalize(" 长 颈\u3000鹿！") == "长颈鹿"
    assert normalize("ＡＢＣ") == "abc"
    assert normalize("Hello, World") == "helloworld"
    assert normalize("!!! ") == ""


def test_normalize_drops_emoji_and_symbols():
    assert normalize("长颈鹿😀~") == "长颈鹿"


def test_word_length_ignores_spaces():
    assert word_length("长颈鹿") == 3 and word_length("hello kitty") == 10
    assert mask("hello kitty") == "*" * 10
