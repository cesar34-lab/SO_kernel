# -*- coding: utf-8 -*-
"""
Módulo de descubrimiento de nodos usando multidifusión (UDP).
Mantiene una tabla local de vecinos con latidos (heartbeats).
"""
import socket, struct, json, threading, time
from typing import Dict, Tuple

class Descubridor:
    def __init__(self, grupo:str, puerto:int, nombre:str, servicio_url:str, ttl:int=1, intervalo:float=2.0, timeout:float=6.0):
        self.grupo = grupo
        self.puerto = puerto
        self.nombre = nombre
        self.servicio_url = servicio_url
        self.intervalo = intervalo
        self.timeout = timeout
        self.vecinos: Dict[str, Tuple[float, str]] = {}  # nombre -> (ultimo_latido_ts, url)
        self._detener = threading.Event()

    def _socket_emisor(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        ttl_bin = struct.pack('b', 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl_bin)
        return sock

    def _socket_receptor(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', self.puerto))
        mreq = struct.pack('4sl', socket.inet_aton(self.grupo), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        return sock

    def anunciar(self):
        sock = self._socket_emisor()
        while not self._detener.is_set():
            mensaje = json.dumps({"nombre": self.nombre, "url": self.servicio_url, "ts": time.time()})
            sock.sendto(mensaje.encode('utf-8'), (self.grupo, self.puerto))
            time.sleep(self.intervalo)

    def escuchar(self):
        sock = self._socket_receptor()
        sock.settimeout(1.0)
        while not self._detener.is_set():
            try:
                data, _ = sock.recvfrom(4096)
                info = json.loads(data.decode('utf-8'))
                if info.get("nombre") != self.nombre:
                    self.vecinos[info["nombre"]] = (time.time(), info["url"])
            except socket.timeout:
                pass
            # purgar expirados
            ahora = time.time()
            expirados = [k for k,(ts,_) in self.vecinos.items() if ahora - ts > self.timeout]
            for k in expirados:
                self.vecinos.pop(k, None)

    def iniciar(self):
        self._detener.clear()
        threading.Thread(target=self.anunciar, daemon=True).start()
        threading.Thread(target=self.escuchar, daemon=True).start()

    def detener(self):
        self._detener.set()

    def lista_vecinos(self):
        return [{"nombre": k, "url": v[1], "ultimo": v[0]} for k, v in self.vecinos.items()]
