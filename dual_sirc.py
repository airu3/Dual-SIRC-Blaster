#!/usr/bin/env python3
"""Dual-SIRC Blaster • v1.0-alpha
Command line tool to blast Sony SIRC codes via Obniz.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import List

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

try:
    import typer
except Exception as e:  # pragma: no cover - gracefully handle missing Typer
    typer = None

# env flag to force mock
OBNIZ_MOCK = bool(int(os.getenv("OBNIZ_MOCK", "0")))

CARRIER_HZ = 40_000
BURST_1_US = 1200
BURST_0_US = 600
GAP_US = 600
HEADER_US = 2400

# Attempt real obniz import unless mock forced
if not OBNIZ_MOCK:
    try:
        from obniz import Obniz  # type: ignore
    except Exception:
        print("[warn] obniz SDK missing -> switching to mock")
        OBNIZ_MOCK = True

if OBNIZ_MOCK:
    class Obniz:  # type: ignore
        def __init__(self, id: str):
            self.id = id
        def wired(self, *_args, **_kwargs):
            print(f"[mock] wired IRLED on {self.id}")
        class _IR:
            @staticmethod
            def send(code: List[int], freq: int):
                print(f"[mock] -> send {len(code)} pulses @ {freq} Hz")
        @property
        def ir_led(self):
            return self._IR()


def sirc12(code: int) -> List[int]:
    bits = format(code & 0xFFF, "012b")[::-1]
    pulses = [HEADER_US, GAP_US]
    for b in bits:
        pulses += [BURST_1_US if b == "1" else BURST_0_US, GAP_US]
    return pulses

READY = sirc12(0x80)
START = sirc12(0x81)
STOP = sirc12(0x82)

@dataclass
class IRBlaster:
    id: str
    pin: int = 0
    _ob: Obniz | None = None

    def connect(self) -> None:
        self._ob = Obniz(self.id)
        self._ob.wired("IRLED", {"pin": self.pin})

    def send(self, code: List[int]) -> None:
        if not self._ob:
            raise RuntimeError("not connected")
        self._ob.ir_led.send(code, 38)


def run_demo(ids: List[str]) -> None:
    blasters = [IRBlaster(i) for i in ids]
    for b in blasters:
        b.connect()
    for b in blasters:
        b.send(READY)
    input("ENTER to START -> ")
    for b in blasters:
        b.send(START)
    time.sleep(3)
    for b in blasters:
        b.send(STOP)


def main_cli():
    if typer is None:
        raise RuntimeError("Typer not available")

    app = typer.Typer(add_completion=False)

    @app.command()
    def blast(
        mode: str = typer.Argument("demo", help="demo|ready|start|stop"),
        ids: str = typer.Option(os.getenv("OBNIZ_IDS", "OBNIZ_ID_A")),
        duration: float = typer.Option(3.0, help="duration for start mode"),
        mock: bool = typer.Option(OBNIZ_MOCK, help="force mock"),
    ) -> None:
        """Send IR codes."""
        global OBNIZ_MOCK
        if mock:
            OBNIZ_MOCK = True
        targets = [s.strip() for s in ids.split(",") if s.strip()]
        codes = {
            "ready": READY,
            "start": START,
            "stop": STOP,
        }
        blasters = [IRBlaster(i) for i in targets]
        for b in blasters:
            b.connect()
        if mode == "demo":
            for b in blasters:
                b.send(READY)
            input("ENTER to START -> ")
            for b in blasters:
                b.send(START)
            time.sleep(duration)
            for b in blasters:
                b.send(STOP)
        else:
            code = codes.get(mode)
            if code is None:
                raise typer.BadParameter("mode must be demo/ready/start/stop")
            for b in blasters:
                b.send(code)

    app()


if __name__ == "__main__":
    if typer:
        main_cli()
    else:
        ids_env = os.getenv("OBNIZ_IDS", "OBNIZ_ID_A")
        run_demo(ids_env.split(","))
