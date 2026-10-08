"""原作の自弾の色と遠景2行修正の、ROM・実PPU・原画をまとめて保存する。"""
import gzip
import io
import hashlib
import json
import shutil
import tarfile
from PIL import Image,ImageDraw
from build_game import ROOT,BUILD,GAME
from verify_player_mask import verify as player_mask

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    out=GAME/'results/shot_horizon_20261009';out.mkdir(parents=True,exist_ok=True)
    release=ROOT/'releases/MonoSHFX2_v001.sfc';manifest=ROOT/'releases/v001.json'
    if not (out/'previous_release.json').exists():shutil.copy2(manifest,out/'previous_release.json')
    digest=sha(BUILD/'MonoSHFX2_v001.sfc')
    result={'romSha256':digest,'previousRomSha256':json.loads((out/'previous_release.json').read_text(encoding='utf-8'))['romSha256'],
            'hardwareTested':False,'playerMask':player_mask(),'scenarios':{}}
    for name in ['objects','display','held','color']:
        source=BUILD/name
        assert not (source/'error.txt').exists(),(name,'emulator script error')
        report=json.loads((source/'summary.json').read_text())
        assert report['romSha256']==digest,(name,'ROM mismatch')
        result['scenarios'][name]=report
        for filename in ['summary.json','objects_ppu.json','color_summary.json']:
            if (source/filename).exists():shutil.copy2(source/filename,out/(name+'_'+filename))
        for filename in ['trace.jsonl','test.lua','emulator.log']:
            (out/(name+'_'+filename+'.gz')).write_bytes(gzip.compress((source/filename).read_bytes(),mtime=0))
        if name in ['display','objects']:
            buffer=io.BytesIO()
            with tarfile.open(fileobj=buffer,mode='w') as tar:
                for path in sorted(source.iterdir()):
                    if path.suffix not in ('.bin','.png','.json'):continue
                    entry=tarfile.TarInfo(path.name);data=path.read_bytes();entry.size=len(data)
                    tar.addfile(entry,io.BytesIO(data))
            (out/(name+'_ppu_proof.tar.gz')).write_bytes(gzip.compress(buffer.getvalue(),mtime=0))
    shutil.copy2(BUILD/'objects/objview00320.png',out/'four_shot_colors.png')
    shutil.copy2(GAME/'assets/recorded_effects/bullet_color_phases.png',out/'shot_colors.png')
    before=ROOT/'.cache/github_export/build/game_v001/display'
    comparison=Image.new('RGB',(3*512,2*502),(45,45,45));draw=ImageDraw.Draw(comparison)
    for i,field in enumerate([238,478,718]):
        name=f'display{field:05d}.png'
        shutil.copy2(BUILD/'display'/name,out/name)
        previous=out/('before_'+name)
        if not previous.exists():shutil.copy2(before/name,previous)
        for row,path in enumerate([previous,out/name]):
            image=Image.open(path).convert('RGB').resize((512,478),Image.Resampling.NEAREST)
            comparison.paste(image,(i*512,row*502+20))
            draw.text((i*512+4,row*502+4),('BEFORE' if row==0 else 'AFTER')+f' CAMERA {i*32}',fill='white')
    comparison.save(out/'horizon_comparison.png')
    close=Image.new('RGB',(1024,232),(45,45,45));draw=ImageDraw.Draw(close)
    for row,name in enumerate(['before_display00238.png','display00238.png']):
        strip=Image.open(out/name).crop((0,90,256,114)).resize((1024,96),Image.Resampling.NEAREST)
        close.paste(strip,(0,row*116+20));draw.text((4,row*116+4),'BEFORE' if row==0 else 'AFTER',fill='white')
    close.save(out/'horizon_closeup.png')
    shots=[Image.open(p).convert('RGB') for p in sorted((BUILD/'held').glob('shot*.png'))]
    assert len(shots)>30,'stationary-fire animation missing'
    shots[0].save(out/'stationary_fire.gif',save_all=True,append_images=shots[1:],duration=17,loop=0)
    (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    shutil.copy2(BUILD/'MonoSHFX2_v001.sfc',release)
    meta=json.loads(manifest.read_text(encoding='utf-8'))
    phases=json.loads((GAME/'assets/recorded_effects/bullet_color_phases.json').read_text(encoding='utf-8'))
    meta.update({'romSha256':digest,'verificationReport':'game/v001/RESULTS_20261009_SHOT_HORIZON.md',
        'verificationResults':'game/v001/results/shot_horizon_20261009',
        'verificationKind':'原作の自弾四色・遠景上端2行削除と2ドット下移動。全17姿勢・弾16サイズ・実PPU三カメラ・静止連射・白黒切替を検証。',
        'sceneryDisplay':{'topTrimRows':2,'downPixels':2,'clipAtGround':True},
        'validation':{'baseCommit':'41f84bf','finalPpuScreens':76,'finalPpuObjectPixels':88749,
            'playerPoses':17,'playerFlips':4,'bulletSizes':16,'bulletPaletteGroups':4,'cameraOffsets':[0,32,64],
            'stationaryFireFields':900,'colorToggleSamples':200,'hardwareTested':False,
            'historicalResults':'game/v001/results/shot_horizon_20261009/previous_release.json'}})
    meta['objColor'].update({'bulletRgb5':phases['rgb5'][0],'bulletPhaseRgb5':phases['rgb5'],
        'bulletSizePalette':phases['sizePalette'],'objPaletteBytesAtBoot':160,
        'bulletSource':'game/v001/assets/recorded_effects/shot_color_reference/source.json'})
    manifest.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Archived and released',digest)

if __name__=='__main__':main()
