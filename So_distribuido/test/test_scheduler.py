# -*- coding: utf-8 -*-
from Libs.scheduler import SchedulerBasico

def test_scheduler_elegir():
    s = SchedulerBasico()
    agentes = [
        {"nombre":"a1","url":"u1","carga":0.1,"lat_ms":10,"disponible":True},
        {"nombre":"a2","url":"u2","carga":0.9,"lat_ms":200,"disponible":True},
    ]
    elegido = s.elegir(agentes)
    assert elegido and elegido["nombre"] in {"a1","a2"}
