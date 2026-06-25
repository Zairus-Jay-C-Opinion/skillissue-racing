# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Skill Issue Racing.
Produces a one-directory build in dist/SkillIssueRacing/.
Run via: pyinstaller skillissue.spec --clean
Or use:  python build.py
"""

from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files

# Collect uvicorn — it uses dynamic imports for protocol implementations
uvicorn_datas, uvicorn_binaries, uvicorn_hidden = collect_all("uvicorn")

# SQLAlchemy dialects loaded at runtime
sqlalchemy_hidden = collect_submodules("sqlalchemy")

# Google Generative AI has many lazy submodules
google_hidden = collect_submodules("google.generativeai")
google_hidden += collect_submodules("google.ai")
google_hidden += collect_submodules("google.api_core")
google_hidden += collect_submodules("google.protobuf")

# pyirsdk — collect everything so the frozen app can import irsdk
try:
    irsdk_datas, irsdk_binaries, irsdk_hidden = collect_all("irsdk")
except Exception:
    irsdk_datas, irsdk_binaries, irsdk_hidden = [], [], []

a = Analysis(
    ["agent/main.py"],
    pathex=["."],
    binaries=[*uvicorn_binaries, *irsdk_binaries],
    datas=[
        ("frontend/dist", "frontend/dist"),
        *uvicorn_datas,
        *irsdk_datas,
    ],
    hiddenimports=[
        # uvicorn
        *uvicorn_hidden,
        # SQLAlchemy
        *sqlalchemy_hidden,
        "sqlalchemy.dialects.sqlite",
        # Google Generative AI
        *google_hidden,
        # Watchdog — Windows backend
        "watchdog.observers.winapi",
        # Other deps
        "psutil",
        "httpx",
        "httpx._transports.default",
        "dotenv",
        "irsdk",
        *irsdk_hidden,
        "pydantic",
        "pydantic.deprecated.class_validators",
        "pydantic_core",
        "starlette",
        "starlette.staticfiles",
        "starlette.responses",
        "anyio",
        "anyio._backends._asyncio",
        "PyQt6",
        "PyQt6.QtWidgets",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.sip",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "pandas"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SkillIssueRacing",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=None,      # add .ico here later
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SkillIssueRacing",
)
