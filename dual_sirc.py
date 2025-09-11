#!/usr/bin/env python3
"""Dual-SIRC Blaster • v1.0-alpha
Command line tool to blast Sony SIRC codes via Obniz.
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import List

# 環境変数の読み込み用にdotenvを試みる
try:
    from dotenv import load_dotenv

    load_dotenv()  # .envファイルから環境変数を読み込む
except Exception:
    pass  # dotenvがインストールされていなくても続行

# CLIツール用にTyperを試みる
try:
    import typer
except Exception as e:  # pragma: no cover - gracefully handle missing Typer
    typer = None  # Typerがない場合はNoneにセット

# モックモードを強制するための環境変数
OBNIZ_MOCK = bool(int(os.getenv("OBNIZ_MOCK", "0")))

# SIRC（Sony Infrared Remote Control）プロトコルのパラメータ設定
CARRIER_HZ = 40_000  # キャリア周波数（40kHz）
BURST_1_US = 1200    # 論理1のバースト時間（マイクロ秒）
BURST_0_US = 600     # 論理0のバースト時間（マイクロ秒）
GAP_US = 600         # 信号間のギャップ（マイクロ秒）
HEADER_US = 2400     # ヘッダーバースト時間（マイクロ秒）

# 実際のObnizライブラリをインポート（モックモードでなければ）
if not OBNIZ_MOCK:
    try:
        from obniz import Obniz  # type: ignore
    except Exception:
        print("[warn] obniz SDK missing -> switching to mock")
        OBNIZ_MOCK = True  # SDKが見つからない場合はモックモードに切り替え

# モックモードの場合、Obnizクラスをエミュレート
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


# 12ビットのSIRCコードをパルスリストに変換する関数
def sirc12(code: int) -> List[int]:
    bits = format(code & 0xFFF, "012b")[::-1]  # 12ビットに制限し、ビット順を反転
    pulses = [HEADER_US, GAP_US]  # ヘッダーとギャップから開始
    for b in bits:
        pulses += [BURST_1_US if b == "1" else BURST_0_US, GAP_US]  # 各ビットに対応するパルスとギャップを追加
    return pulses


# 定義済みの制御コード
READY = sirc12(0x80)  # 準備完了コード
START = sirc12(0x81)  # 開始コード
STOP = sirc12(0x82)   # 停止コード


# 赤外線送信機能を提供するクラス
@dataclass
class IRBlaster:
    id: str  # ObnizのID
    pin: int = 0  # 使用するピン番号
    _ob: Obniz | None = None  # Obnizインスタンス

    def connect(self) -> None:
        """Obnizに接続しIRLEDをセットアップする"""
        self._ob = Obniz(self.id)
        self._ob.wired("IRLED", {"pin": self.pin})

    def send(self, code: List[int]) -> None:
        """IRコードを送信する"""
        if not self._ob:
            raise RuntimeError("not connected")
        self._ob.ir_led.send(code, 38)  # 38kHzで送信


# デモ実行用の関数
def run_demo(ids: List[str]) -> None:
    """複数のデバイスでデモシーケンスを実行"""
    blasters = [IRBlaster(i) for i in ids]  # 各IDに対してIRBlasterを作成
    for b in blasters:
        b.connect()  # すべてのブラスターを接続
    for b in blasters:
        b.send(READY)  # 準備コードを送信
    input("ENTER to START -> ")  # ユーザーの入力待ち
    for b in blasters:
        b.send(START)  # 開始コードを送信
    time.sleep(3)  # 3秒待機
    for b in blasters:
        b.send(STOP)  # 停止コードを送信


# CLIアプリケーションのエントリーポイント
def main_cli():
    """Typerを使用したCLIインターフェースの定義"""
    if typer is None:
        raise RuntimeError("Typer not available")

    app = typer.Typer(add_completion=False)

    @app.command()
    def blast(
        mode: str = typer.Argument("demo", help="demo|ready|start|stop"),  # 動作モード
        ids: str = typer.Option(os.getenv("OBNIZ_IDS", "OBNIZ_ID_A")),  # 使用するObnizのID
        duration: float = typer.Option(3.0, help="duration for start mode"),  # 開始モードの持続時間
        mock: bool = typer.Option(OBNIZ_MOCK, help="force mock"),  # モックモードの強制
    ) -> None:
        """IR信号を送信するコマンド"""
        global OBNIZ_MOCK
        if mock:
            OBNIZ_MOCK = True
        targets = [s.strip() for s in ids.split(",") if s.strip()]  # IDをリストに分割
        codes = {
            "ready": READY,
            "start": START,
            "stop": STOP,
        }
        blasters = [IRBlaster(i) for i in targets]  # 各IDに対してIRBlasterを作成
        for b in blasters:
            b.connect()
        if mode == "demo":
            # デモモードの場合、準備→開始→待機→停止の流れを実行
            for b in blasters:
                b.send(READY)
            input("ENTER to START -> ")
            for b in blasters:
                b.send(START)
            time.sleep(duration)
            for b in blasters:
                b.send(STOP)
        else:
            # 特定のコードだけを送信
            code = codes.get(mode)
            if code is None:
                raise typer.BadParameter("mode must be demo/ready/start/stop")
            for b in blasters:
                b.send(code)

    app()


# メインエントリーポイント
if __name__ == "__main__":
    if typer:
        main_cli()  # TyperがあればCLIモードで実行
    else:
        # Typerがなければシンプルなデモ実行
        ids_env = os.getenv("OBNIZ_IDS", "OBNIZ_ID_A")
        run_demo(ids_env.split(","))