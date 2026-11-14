# PyInstaller spec: the small Mini World skill runner (see backend/skill_runner.py)
# The standard-library modules skills may import must be bundled explicitly,
# because the runner itself never imports them.
safe = ['json', 'math', 're', 'datetime', 'statistics', 'collections', 'itertools', 'string', 'textwrap',
        'random', 'decimal', 'fractions', 'unicodedata', 'html', 'html.parser', 'urllib.parse', 'functools',
        'operator', 'calendar', 'pathlib', 'csv', 'glob', 'shutil', 'urllib.request', 'http.client', 'inspect']

a = Analysis(['backend/skill_runner.py'], pathex=['.'], hiddenimports=safe,
             excludes=['numpy', 'tkinter', 'PIL', 'onnxruntime', 'aiohttp', 'yaml', 'openai'], noarchive=False)
pyz = PYZ(a.pure, a.zipped_data)
exe = EXE(pyz, a.scripts, a.binaries, a.zipfiles, a.datas, name='pulseai-skill-runner', debug=False,
          console=False, upx=True)
