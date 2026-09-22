"""CLI without Telegram — local test / scripted import."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from bot.db import DeviceDB, format_device

load_dotenv()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Device DB CLI (Telegram ke bina)")
    p.add_argument("--db", default=os.getenv("DATABASE_PATH", "data/devices.db"))
    p.add_argument("--owner", type=int, default=1, help="Owner chat id (default 1)")
    sub = p.add_subparsers(dest="cmd", required=True)

    add = sub.add_parser("add", help="Device add karo")
    add.add_argument("name")
    add.add_argument("--model", default="")
    add.add_argument("--serial", default="")
    add.add_argument("--imei", default="")
    add.add_argument("--phone", default="")
    add.add_argument("--notes", default="")

    sub.add_parser("list", help="Devices list")
    find = sub.add_parser("find", help="Search")
    find.add_argument("query")
    sub.add_parser("count", help="Count")
    imp = sub.add_parser("import", help="CSV/JSON import")
    imp.add_argument("file")
    clear = sub.add_parser("clear", help="Clear all for owner")
    _ = clear
    return p


def main() -> None:
    args = build_parser().parse_args()
    db = DeviceDB(args.db)
    owner = args.owner

    if args.cmd == "add":
        did = db.add_device(
            owner, args.name, args.model, args.serial, args.imei, args.phone, args.notes
        )
        print(f"Added #{did}: {args.name}")
    elif args.cmd == "list":
        rows = db.list_devices(owner)
        if not rows:
            print("No devices.")
            return
        print("\n\n".join(format_device(r) for r in rows))
    elif args.cmd == "find":
        rows = db.search(owner, args.query)
        if not rows:
            print("No match.")
            return
        print("\n\n".join(format_device(r) for r in rows))
    elif args.cmd == "count":
        print(db.count(owner))
    elif args.cmd == "import":
        path = Path(args.file)
        n = db.import_file(owner, path)
        print(f"Imported {n} devices from {path}")
    elif args.cmd == "clear":
        print(f"Cleared {db.clear_all(owner)}")


if __name__ == "__main__":
    main()
