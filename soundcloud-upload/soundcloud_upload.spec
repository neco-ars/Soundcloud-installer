# soundcloud_upload.spec
#
# Использование:
#   pyinstaller soundcloud_upload.spec
#
# Результат появится в dist/soundcloud_upload.exe
#
# Если позже захочешь добавить иконку — положи файл icon.ico рядом
# и раскомментируй строку icon='icon.ico' ниже.

# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['soundcloud_upload.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='soundcloud_upload',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,          # нужно окно консоли — скрипт просит нажимать Enter
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='icon.ico',
)
