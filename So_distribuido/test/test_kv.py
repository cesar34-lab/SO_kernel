# -*- coding: utf-8 -*-
from Libs.kv import KVLocal

def test_kv_basico():
    kv = KVLocal()
    assert kv.get("x") is None
    v = kv.put("x", 123)
    assert v >= 1
    assert kv.get("x") == 123
    kv.put("x", 456)
    assert kv.get("x") == 456
    s = kv.estado()
    assert "x" in s and s["x"]["valor"] == 456
