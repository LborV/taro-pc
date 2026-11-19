"""Tiny driver for build123d-mcp: run a list of tool calls in one server session.

Usage (from Hermes python with `mcp` installed):
    python tools/mcpcad.py steps.json
steps.json = [{"tool": "execute_file", "args": {...}, "save": "out/x.png"}, ...]
Images returned by render tools are saved to the given path.
"""
import asyncio
import base64
import json
import os
import re
import shutil
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER = os.path.expanduser("~/.local/bin/build123d-mcp")


async def run(steps, quiet=False):
    p = StdioServerParameters(
        command=SERVER,
        args=["--allow-imports", "params,parts,assembly,dummies,envelope,layout", "--exec-timeout", "600"],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": ROOT},
    )
    errlog = open(os.path.join(ROOT, '.mcp-server.log'), 'a')
    async with stdio_client(p, errlog=errlog) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            for st in steps:
                res = await s.call_tool(st["tool"], st.get("args", {}))
                if res.isError:
                    print(f"[{st['tool']}] ERROR:", " ".join(c.text for c in res.content if c.type == "text")[:3000])
                    if not st.get("continue_on_error"):
                        break
                save = st.get("save")
                for c in res.content:
                    if c.type == "text":
                        txt = c.text
                        m = re.search(r"\[SEND: ([^\]]+\.png)\]", txt)
                        if m and save and os.path.exists(m.group(1)):
                            os.makedirs(os.path.dirname(os.path.join(ROOT, save)), exist_ok=True)
                            shutil.copy(m.group(1), os.path.join(ROOT, save))
                        if not quiet:
                            print(f"[{st['tool']}]", txt[: st.get("max", 1500)])
                    elif c.type == "image" and save:
                        path = os.path.join(ROOT, save)
                        os.makedirs(os.path.dirname(path), exist_ok=True)
                        with open(path, "wb") as fh:
                            fh.write(base64.b64decode(c.data))
                        print(f"[{st['tool']}] image -> {save}")


if __name__ == "__main__":
    asyncio.run(run(json.load(open(sys.argv[1]))))
