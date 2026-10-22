import pytest

from server.msgparse import BadMessage, req_dict, req_int, req_int_list, req_str


def test_req_str():
    assert req_str({"text": "hi"}, "text", 5) == "hi"
    for bad in [{"text": "toolong"}, {"text": 5}, {"text": "  "}, {}]:
        with pytest.raises(BadMessage):
            req_str(bad, "text", 3)
    assert req_str({"text": " "}, "text", 3, allow_blank=True) == " "


def test_req_int_rejects_bool_and_range():
    assert req_int({"n": 3}, "n", 0, 5) == 3
    for bad in [{"n": True}, {"n": 7}, {"n": -1}, {"n": 2.5}, {"n": "3"}, {}]:
        with pytest.raises(BadMessage):
            req_int(bad, "n", 0, 5)


def test_req_int_list():
    assert req_int_list({"pts": [1, 2]}, "pts", 4, 0, 10) == [1, 2]
    for bad in [{"pts": [1, 2, 3, 4, 5]}, {"pts": [1, "2"]}, {"pts": [1, 11]}, {"pts": [True]}, {"pts": "12"}, {}]:
        with pytest.raises(BadMessage):
            req_int_list(bad, "pts", 4, 0, 10)


def test_req_dict():
    assert req_dict({"d": {}}, "d") == {}
    for bad in [{"d": []}, {}]:
        with pytest.raises(BadMessage):
            req_dict(bad, "d")
