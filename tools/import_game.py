"""既存60Hz版の更新処理とテーブルを、原本を変更せず固定する。"""
from pathlib import Path
import hashlib
import json
import os

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(os.environ.get('MONOSH_MSX_ROOT', 'D:/MSXDev/MSXSH'))
DEST = ROOT / 'game/v001/upstream'

def main():
    DEST.mkdir(parents=True, exist_ok=True)
    names = ['monosh_player', 'monosh_stage', 'monosh_enemy', 'monosh_combat',
             'monosh_boss', 'monosh_projection', 'monosh_draw',
             'monosh_stage_data', 'monosh_enemy_data', 'monosh_boss_data']
    files = [f'{name}.{ext}' for name in names for ext in ['c', 'h']]
    files += ['mode3_sprite.h', 'monosh_assets.h', 'monosh_runtime.h',
              'monosh_ground_camera_table.inc', 'monosh_projection_data.asm',
              'monosh_enemy_fast.asm', 'monosh_combat_fast.asm', 'monosh_stage_fast.asm',
              'monosh_boss_fast.asm', 'monosh_boss_prepare.asm', 'monosh_runtime_fast.asm',
              'monosh_far_background.c', 'monosh_far_background.h', 'monosh_far_background_fast.asm']
    manifest = {}
    for name in files:
        data = (SOURCE / 'src' / name).read_bytes()
        (DEST / name).write_bytes(data)
        manifest[name] = hashlib.sha256(data).hexdigest()
    (DEST / 'sources.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(f'{len(files)} source files frozen in {DEST}')

if __name__ == '__main__':
    main()
