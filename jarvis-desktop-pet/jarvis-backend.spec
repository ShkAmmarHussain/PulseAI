# PyInstaller spec
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_submodules

project = Path('.')

extra_datas, extra_bins, extra_hidden = [], [], []
for pkg in ('ctranslate2', 'faster_whisper', 'sounddevice', 'ddgs', 'primp', 'huggingface_hub', 'tokenizers',
            'kokoro_onnx', 'phonemizer', 'espeakng_loader', 'openwakeword', 'onnxruntime'):
    try:
        d, b, h = collect_all(pkg)
        extra_datas += d
        extra_bins += b
        extra_hidden += h
    except Exception as e:
        print(f'collect_all({pkg}) skipped: {e}')

try:
    extra_hidden += collect_submodules('win32com')
except Exception as e:
    print(f'win32com submodules skipped: {e}')

extra_hidden += ['pythoncom', 'aiohttp', 'pydantic', 'yaml', 'openai', 'smolagents']

a = Analysis(
    ['backend/main.py'],
    pathex=[str(project)],
    datas=[('config', 'config'), ('agents', 'agents'), ('skills', 'skills'), ('core', 'core')] + extra_datas,
    binaries=extra_bins,
    hiddenimports=list(dict.fromkeys(extra_hidden)),
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas, name='jarvis-backend', debug=False, console=False, upx=True)
