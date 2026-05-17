#!/usr/bin/env python3
"""Clean terminal artifacts from Python files"""
import os
import sys

base = '/mnt/d/向海容的知识库/wiki/wiki/记忆宫殿/L5孵化室/产品开发/出海项目/中韩出海数智港/china-korea-digital-port/backend'

files_to_clean = ['main.py', 'routers/payment.py']

for fname in files_to_clean:
    path = os.path.join(base, fname)
    if not os.path.exists(path):
        print(f"{fname}: not found, skipping")
        continue

    with open(path, 'rb') as f:
        raw = f.read()

    # Decode, removing null bytes
    content = raw.decode('utf-8', errors='replace').replace('\x00', '')

    # Find the start of valid Python content
    markers = [
        '"""\n中韩出海数智港 - FastAPI应用入口\n"""',
        '"""\n中韩出海数智港 - 支付系统API路由',
        '"""\n中韩出海数智港 - 数据库模块',
        '"""\n中韩出海数智港 - Pydantic数据模型',
        '"""',
        'from fastapi import',
        'import json',
        'import sqlite3',
    ]
    start = 0
    for marker in markers:
        idx = content.find(marker)
        if idx >= 0:
            start = idx
            break

    content = content[start:]

    # Remove lines that are terminal artifacts
    lines = content.split('\n')
    clean = []
    for l in lines:
        stripped = l.strip()
            continue
        clean.append(l)

    content = '\n'.join(clean)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"{fname}: cleaned to {len(content)} bytes, {len(clean)} lines")
    sys.stdout.flush()

print("Done cleaning")
