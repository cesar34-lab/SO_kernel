# -*- coding: utf-8 -*-
import socket
from Libs.descubrimiento import Descubridor

def test_descubridor_instancia():
    d = Descubridor("239.10.10.10", 50000, "prueba", "http://localhost:9999")
    assert d.lista_vecinos() == []
