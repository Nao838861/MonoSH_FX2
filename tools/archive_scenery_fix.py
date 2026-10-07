"""遠景修正の録画比較・実PPU画像・二重スクロール・検証ログを保存する。"""
import gzip
import hashlib
import json
import shutil
from pathlib import Path
from PIL import Image, ImageDraw
from build_game import BUILD, GAME


def main():
    root=GAME.parents[1]
    dest=GAME/'results/scenery_fix_20261008'
    dest.mkdir(parents=True,exist_ok=True)
    digest=hashlib.sha256((BUILD/'MonoSHFX2_v001.sfc').read_bytes()).hexdigest()
    baseline=root/'.cache/scenery_fix/baseline'
    for scenario in ('display','scenery','objects','held','boss','boss_profile_scenery'):
        summary=json.loads((BUILD/scenario/'summary.json').read_text())
        assert summary['romSha256']==digest,scenario
        shutil.copyfile(BUILD/scenario/'summary.json',dest/f'{scenario}_summary.json')
        (dest/f'{scenario}_trace.jsonl.gz').write_bytes(gzip.compress((BUILD/scenario/'trace.jsonl').read_bytes(),mtime=0))
    for directory in ('display','scenery'):
        target=dest/directory;target.mkdir(exist_ok=True)
        for path in (BUILD/directory).glob('display*'):
            if path.is_file():shutil.copyfile(path,target/path.name)
    reference=Image.open(root/'.cache/player_capture/native_1741.png').convert('RGB')
    reference.save(dest/'reference_0058.png')
    before=Image.open(baseline/'display00238.png').convert('RGB')
    before.save(dest/'before.png')
    after=Image.open(BUILD/'scenery/display00238.png').convert('RGB')
    after.save(dest/'after.png')
    panels=[('REFERENCE VIDEO 00:58',reference.crop((0,115,256,170))),
            ('BEFORE: forest overlaps 9 rows of ground',before.crop((0,66,256,121))),
            ('AFTER: forest above ground, purple mountains behind canopy',after.crop((0,66,256,121)))]
    sheet=Image.new('RGB',(1024,3*252),(24,24,24));draw=ImageDraw.Draw(sheet)
    for i,(label,panel) in enumerate(panels):
        draw.text((8,i*252+8),label,fill='white')
        sheet.paste(panel.resize((1024,220),Image.Resampling.NEAREST),(0,i*252+28))
    sheet.save(dest/'comparison.png')
    frames=[Image.open(path).convert('RGB').crop((0,65,256,122)).resize((768,171),Image.Resampling.NEAREST)
            for path in sorted((BUILD/'scenery').glob('parallax*.png'))]
    assert len(frames)==21
    frames[0].save(dest/'parallax.gif',save_all=True,append_images=frames[1:],duration=67,loop=0)
    heights=Image.new('RGB',(768,239))
    for i,path in enumerate(sorted((BUILD/'scenery').glob('display[0-9]*.png'))):heights.paste(Image.open(path),(256*i,0))
    heights.save(dest/'camera_heights.png')
    (dest/'baseline_test.lua.gz').write_bytes(gzip.compress((baseline/'test.lua').read_bytes(),mtime=0))
    for name in ('game.lbl','game.map','build_mode.json'):
        shutil.copyfile(BUILD/name,dest/name)
    if (BUILD/'scenery_performance.json').exists():
        performance=json.loads((BUILD/'scenery_performance.json').read_text())
        assert performance['romSha256']==digest
        shutil.copyfile(BUILD/'scenery_performance.json',dest/'performance.json')
    (dest/'profile_timings.jsonl.gz').write_bytes(gzip.compress((BUILD/'boss_profile_scenery/timings.jsonl').read_bytes(),mtime=0))
    (dest/'profile_test.lua.gz').write_bytes(gzip.compress((BUILD/'boss_profile_scenery/test.lua').read_bytes(),mtime=0))
    (dest/'provenance.json').write_text(json.dumps({
        'romSha256':digest,
        'baselineRomSha256':hashlib.sha256((baseline/'baseline.sfc').read_bytes()).hexdigest(),
        'baselinePublicCommit':'c3376cf',
        'referenceFrame':1741,'referenceSeconds':58,
        'comparisonNativeCrop':[0,115,256,170],'comparisonPpuCrop':[0,66,256,121],
        'ppuOverscanTop':6,'forestRaisedPixels':9,
        'gradientNativeRows':[130,151],'gradientPpuRows':[75,96],
        'parallaxNearSpeed':2,'parallaxFarSpeed':1},indent=2)+'\n')
    print(dest,digest)


if __name__=='__main__':main()
