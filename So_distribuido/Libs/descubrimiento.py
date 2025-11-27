# -*- coding: utf-8 -*-
"""
Módulo de descubrimiento de nodos usando multidifusión (UDP).
Mantiene una tabla local de vecinos con latidos (heartbeats) que incluyen métricas.
"""
import socket, struct, json, threading, time
from typing import Dict, Any, List

class Descubridor:
    def __init__(
        self,
        grupo: str,
        puerto: int,
        nombre: str,
        servicio_url: str,
        obtener_metricas_fn,  # ← NUEVO: función callback para obtener métricas locales
        ttl: int = 1,
        intervalo: float = 2.0,
        timeout: float = 6.0
    ):
        self.grupo = grupo
        self.puerto = puerto
        self.nombre = nombre
        self.servicio_url = servicio_url
        self.obtener_metricas_fn = obtener_metricas_fn  # e.g., lambda: {"carga": _carga}
        self.intervalo = intervalo
        self.timeout = timeout
        # vecinos: nombre -> (último_ts, url, métricas_dict)
        self.vecinos: Dict[str, tuple] = {}
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
            # Obtener métricas dinámicamente desde el nodo
            metricas_locales = self.obtener_metricas_fn() or {}
            mensaje = {
                "nombre": self.nombre,
                "url": self.servicio_url,
                "ts": time.time(),
                **metricas_locales  # incluye carga, etc.
            }
            try:
                sock.sendto(json.dumps(mensaje).encode('utf-8'), (self.grupo, self.puerto))
            except Exception:
                pass  # silencioso ante fallos de red
            time.sleep(self.intervalo)

            def escuchar(self):
                sock = self._socket_receptor()
                sock.settimeout(0.5)  # timeout corto para responder rápido a detener()
                while not self._detener.is_set():
                    try:
                        data, _ = sock.recvfrom(4096)
                        try:
                            info = json.loads(data.decode('utf-8'))
                            if not isinstance(info, dict):
                                continue
                            nombre_vecino = info.get("nombre")
                            if not nombre_vecino or nombre_vecino == self.nombre:
                                continue
                            ts = info.get("ts", 0)
                            url = info.get("url", "")
                            if not url or not isinstance(ts, (int, float)):
                                continue
                            metricas = {k: v for k, v in info.items() if k not in {"nombre", "url", "ts"}}
                            self.vecinos[nombre_vecino] = (ts, url, metricas)
                        except (json.JSONDecodeError, UnicodeDecodeError, ValueError, KeyError):
                            # Mensaje malformado: ignorar silenciosamente
                            continue
                    except socket.timeout:
                        # Timeout normal: permite verificar _detener frecuentemente
                        pass
                    except OSError as e:
                        # Error de socket grave (ej: interfaz caída)
                        print(f"[Descubridor] Error de socket: {e}")
                        time.sleep(1)  # evitar bucle rápido de error
                    # Purgar expirados en cada iteración (ligero y constante)
                    ahora = time.time()
                    expirados = [k for k, (ts, _, _) in self.vecinos.items() if ahora - ts > self.timeout]
                    for k in expirados:
                        self.vecinos.pop(k, None)
                sock.close()

    def iniciar(self):
        self._detener.clear()
        threading.Thread(target=self.anunciar, daemon=True).start()
        threading.Thread(target=self.escuchar, daemon=True).start()

    def detener(self):
        self._detener.set()

    def lista_vecinos_con_metricas(self) -> List[Dict[str, Any]]:
        """Devuelve lista de vecinos con sus métricas actualizadas."""
        resultado = []
        for nombre, (ts, url, metricas) in self.vecinos.items():
            resultado.append({
                "nombre": nombre,
                "url": url,
                "ultimo_latido": ts,
                **metricas
            })
        return resultado