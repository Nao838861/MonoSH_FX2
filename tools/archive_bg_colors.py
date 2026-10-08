"""カラー化ROMと、そのROMを実際に検証した標本・性能測定を保存する。"""
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import statistics
import zipfile
from PIL import Image, ImageDraw
from build_game import ROOT, BUILD, GAME

def main():
    target=GAME/'results/bg_color_20261008';target.mkdir(parents=True,exist_ok=True)
    rom=BUILD/'MonoSHFX2_v001.sfc';sha=hashlib.sha256(rom.read_bytes()).hexdigest()
    profiles={}
    names=['color','display','objects','play','boss','controls','pause','packed','stress']
    for name in names:
        src=BUILD/name;assert not (src/'error.txt').exists(),name
        summary=json.loads((src/'summary.json').read_text())
        assert summary['romSha256']==sha,(name,'different ROM')
        rows=[json.loads(x) for x in (src/'trace.jsonl').read_text().splitlines()]
        fields=[r['field'] for r in rows if 'dmaStartLine' in r]
        fields=fields[:sum('dmaMs' in r for r in rows)]
        assert all(b>=a for a,b in zip(fields,fields[1:]))
        # 同じ黒帯内で複数回書いた場合、画面に出る最後の画像だけを提示として数える。
        unique=list(dict.fromkeys(fields))
        summary['extraWritesInSameBlank']=len(fields)-len(unique)
        fields=unique
        intervals=[b-a for a,b in zip(fields,fields[1:])]
        summary['presentationFps']=60.0988*(len(fields)-1)/(fields[-1]-fields[0])
        summary['presentationIntervals']={str(n):intervals.count(n) for n in sorted(set(intervals))}
        summary['intervalBasis']='DMA開始field。完了のfield跨ぎを除外。'
        summary['cpuMeanMs']=statistics.mean(r['cpuMs'] for r in rows if 'cpuMs' in r)
        summary['gsuMeanMs']=statistics.mean(r['gsuMs'] for r in rows if 'gsuMs' in r)
        profiles[name]=summary
        out=target/name;out.mkdir(exist_ok=True)
        (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (out/'trace.jsonl.gz').write_bytes(gzip.compress((src/'trace.jsonl').read_bytes(),mtime=0))
        (out/'test.lua.gz').write_bytes(gzip.compress((src/'test.lua').read_bytes(),mtime=0))
        shutil.copy2(src/'emulator.log',out/'emulator.log')
        # 元の検査ツールへ展開して再照合できるよう、全標本をまとめて保存する。
        with zipfile.ZipFile(out/'samples.zip','w',zipfile.ZIP_DEFLATED) as z:
            for path in sorted(src.iterdir()):
                if path.suffix in ['.bin','.json','.png'] and path.name!='summary.json':z.write(path,path.name)
    assert profiles['boss']['loopSeen'] and profiles['boss']['doneSeen']
    for name in ['color_summary.json']:
        shutil.copy2(BUILD/'color'/name,target/name)
    for name in ['game.map','game.lbl','build_mode.json']:
        shutil.copy2(BUILD/name,target/name)
    for name,source in [('color.png','color/color_mode_55.png'),('mono.png','color/color_mode_110.png'),
                        ('color_return.png','color/color_mode_200.png'),('boss.png','boss/scene_boss.png'),
                        ('enemies.png','play/scene_enemies.png')]:
        path=BUILD/source
        if path.exists():shutil.copy2(path,target/name)
    pair=Image.new('RGB',(1024,239*2+28))
    draw=ImageDraw.Draw(pair)
    for i,(name,label) in enumerate([('color.png','COLOR'),('mono.png','MONO: SELECT')]):
        pic=Image.open(target/name).convert('RGB').resize((512,478),Image.Resampling.NEAREST)
        pair.paste(pic,(i*512,28));draw.text((i*512+10,8),label,fill='white')
    pair.save(target/'comparison.png')
    old=json.loads((ROOT/'releases/v001.json').read_text(encoding='utf-8'))
    if not (target/'previous_release.json').exists():
        shutil.copy2(ROOT/'releases/MonoSHFX2_v001.sfc',ROOT/'releases/MonoSHFX2_pre_color_20261008.sfc')
        (target/'previous_release.json').write_text(json.dumps(old,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    previous=json.loads((target/'previous_release.json').read_text(encoding='utf-8'))
    assert hashlib.sha256((ROOT/'releases/MonoSHFX2_pre_color_20261008.sfc').read_bytes()).hexdigest()==previous['romSha256']
    shutil.copy2(rom,ROOT/'releases/MonoSHFX2_v001.sfc')
    keep=['display','framebuffer','format','sourceSha256','hardwareObjects','testedEmulator',
          'groundPalette','objColor','playerImageSource','recordedEffectsSource']
    manifest={k:old[k] for k in keep if k in old}
    manifest.update({'romSha256':sha,'romBytes':rom.stat().st_size,
        'buildMode':json.loads((BUILD/'build_mode.json').read_text()),
        'verificationKind':'2bpp敵・障害物のカラー化とSELECT切替。色属性・VRAM/CGRAM・最終PPU合成・操作・ボス進行を検証。60fps未達。',
        'verificationResults':'game/v001/results/bg_color_20261008',
        'scenarioFrames':{k:v['fields'] for k,v in profiles.items()},
        'previousRomSha256':json.loads((target/'previous_release.json').read_text(encoding='utf-8'))['romSha256'],
        'bgColor':{'source':'game/v001/assets/bg_color/source.json','paletteGroups':8,'visibleColorsPerGroup':3,
                   'attributeTilePixels':[8,8],'default':'color','toggle':'SELECT','toggleScope':'2bpp enemies and obstacles only',
                   'physicalHardwareTested':False},
        'performance':{k:{n:v[n] for n in ['presentationFps','cpuMeanMs','cpuMaxMs','gsuMeanMs','gsuMaxMs']}
                       for k,v in profiles.items() if k in ['play','boss']}})
    (ROOT/'releases/v001.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (target/'profiles.json').write_text(json.dumps(profiles,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(sha)
    print({k:round(v['presentationFps'],2) for k,v in profiles.items()})

if __name__=='__main__':main()
