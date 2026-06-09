"""
collector.py - Coinbase WebSocket L2 feed collector
Usage: python collector.py --duration 120
"""
import argparse
import asyncio
import csv
import json
import time
from pathlib import Path

import websockets

WS_URL = "wss://advanced-trade-ws.coinbase.com"
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)


async def stream(product: str, duration: int, outfile: Path):
    subscribe_msg = json.dumps({
        "type": "subscribe",
        "product_ids": [product],
        "channel": "ticker",
    })

    print(f"[collector] Connecting to Coinbase WebSocket...")
    print(f"[collector] Product: {product}  |  Duration: {duration}s")
    print(f"[collector] Output: {outfile}\n")

    row_count = 0
    start = time.time()

    async with websockets.connect(WS_URL, ping_interval=20, max_size=10_000_000) as ws:
        await ws.send(subscribe_msg)
        confirmation = await ws.recv()
        print(f"[collector] Subscribed: {json.loads(confirmation).get('type', '?')}")

        with open(outfile, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["arrival_ts", "sequence", "product", "num_changes"])

            while time.time() - start < duration:
                try:
                    raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                except asyncio.TimeoutError:
                    print("[collector] No message for 5s, still waiting...")
                    continue

                arrival_ts = time.time()
                msg = json.loads(raw)

                if msg.get("channel") != "ticker":
                    continue

                for event in msg.get("events", []):
                    changes = event.get("updates", [])
                    seq = msg.get("sequence_num", -1)
                    writer.writerow([arrival_ts, seq, product, len(changes)])
                    row_count += 1

                if row_count % 100 == 0:
                    elapsed = time.time() - start
                    print(f"[collector] {row_count} messages  |  {elapsed:.1f}s elapsed")

    print(f"\n[collector] Done. {row_count} rows saved to {outfile}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duration", type=int, default=60)
    parser.add_argument("--product", type=str, default="BTC-USD")
    parser.add_argument("--output", type=str, default="data/raw_feed.csv")
    args = parser.parse_args()
    asyncio.run(stream(args.product, args.duration, Path(args.output)))


if __name__ == "__main__":
    main()
