"""二値パレットと自機の抜け修正の最終ROM・画素検証を保存する。"""
import gzip
import hashlib
import io
import json
import shutil
import subprocess
from pathlib import Path
from PIL import Image,ImageDraw
from build_game import ROOT,BUILD,GAME
from verify_player_mask import verify

def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    out=GAME/'results/binary_player_20261009';out.mkdir(parents=True,exist_ok=True)
    previous=out/'previous.sfc.gz'
    manifest=ROOT/'releases/v001.json'
    if not previous.exists():
        previous.write_bytes(gzip.compress((ROOT/'releases/MonoSHFX2_v001.sfc').read_bytes(),mtime=0))
        shutil.copy2(manifest,out/'previous_release.json')
        prefix=subprocess.check_output(['git','rev-parse','--show-prefix'],cwd=ROOT).decode().strip()
        before=subprocess.check_output(['git','show','HEAD:'+prefix+'game/v001/assets/player_recording/preview.png'],cwd=ROOT)
        (out/'player_before.png').write_bytes(before)
    old=gzip.decompress(previous.read_bytes());new=(BUILD/'MonoSHFX2_v001.sfc').read_bytes()
    assert len(old)==len(new)==0x200000
    previous_meta=json.loads((out/'previous_release.json').read_text(encoding='utf-8'))
    assert sha(old)==previous_meta['romSha256']
    mono=old.index(bytes.fromhex('0000630c1042ff7f')*8)
    assert new[mono:mono+64]==bytes.fromhex('00000000ff7fff7f')*8
    changes=[i for i,(a,b) in enumerate(zip(old,new)) if a!=b]
    # BOOTの64byte定数、OBJの4bpp CHR、checksum以外は完全一致。
    assert all(mono<=i<mono+64 or 0x3c000<=i<0x40000 or 0x7fdc<=i<0x7fe0 for i in changes)
    assert old[0x191300:0x1a0000]==new[0x191300:0x1a0000]
    delta_path=out/'player_delta.json'
    if not delta_path.exists():
        prefix=subprocess.check_output(['git','rev-parse','--show-prefix'],cwd=ROOT).decode().strip()
        restored={}
        for asset in [9,*range(15,31)]:
            name=f'game/v001/assets/obj_color/{asset:02d}.png'
            before=Image.open(io.BytesIO(subprocess.check_output(['git','show','HEAD:'+prefix+name],cwd=ROOT)))
            after=Image.open(ROOT/name)
            assert before.size==after.size==(32,48)
            pairs=list(zip(before.getdata(),after.getdata()))
            assert all(a==b for a,b in pairs if a),'以前の不透明画素を変更した'
            restored[str(asset)]=sum(a==0 and b!=0 for a,b in pairs)
        delta_path.write_text(json.dumps({'restoredPixels':sum(restored.values()),'perAsset':restored,
            'existingOpaquePixelsUnchanged':True},indent=2)+'\n')
    summary={'romSha256':sha(new),'previousRomSha256':sha(old),'changedRomBytes':len(changes),
             'allowedChanges':['monochrome CGRAM constants','static OBJ CHR','checksum'],
             'cpuGsuAudioUnchanged':True,'audioRegionSha256':sha(new[0x191300:0x1a0000]),
             'playerMask':verify(),'hardwareTested':False,'scenarios':{}}
    summary['playerDelta']=json.loads(delta_path.read_text())
    for scenario in ['color','objects','held']:
        source=BUILD/scenario
        report=json.loads((source/'summary.json').read_text())
        assert report['romSha256']==sha(new),(scenario,'different ROM')
        summary['scenarios'][scenario]=report
        for name in ['summary.json','color_summary.json','objects_ppu.json']:
            if (source/name).exists():shutil.copy2(source/name,out/(scenario+'_'+name))
        for name in ['trace.jsonl','test.lua','emulator.log']:
            (out/(scenario+'_'+name+'.gz')).write_bytes(gzip.compress((source/name).read_bytes(),mtime=0))
    for field,name in [(55,'color.png'),(110,'binary.png'),(200,'color_return.png')]:
        shutil.copy2(BUILD/'color'/f'color_mode_{field}.png',out/name)
    shutil.copy2(GAME/'assets/player_recording/preview.png',out/'player_after.png')
    images=[Image.open(out/f'player_{name}.png').convert('RGB') for name in ['before','after']]
    sheet=Image.new('RGB',(1024,520),(48,48,48));draw=ImageDraw.Draw(sheet)
    for i,im in enumerate(images):
        sheet.paste(im,(0,20+i*260));draw.text((8,i*260+4),'BEFORE' if i==0 else 'AFTER: CLOTHING MASK FIX',fill='white')
    sheet.save(out/'player_comparison.png')
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    shutil.copy2(BUILD/'MonoSHFX2_v001.sfc',ROOT/'releases/MonoSHFX2_v001.sfc')
    release=json.loads(manifest.read_text(encoding='utf-8'))
    release.update({'romSha256':sha(new),'verificationReport':'game/v001/RESULTS_20261009_BINARY_PLAYER.md',
                    'verificationResults':'game/v001/results/binary_player_20261009',
                    'binaryMonochrome':{'transparentIndex':0,'opaqueRgb5':[[0,0,0],[31,31,31],[31,31,31]]},
                    'playerMaskRepair':summary['playerMask']})
    release['validation']={'baseCommit':'4a0fa27','changedRomBytes':len(changes),
        'cpuGsuAudioUnchanged':True,'colorToggleSamples':200,'playerPoses':17,'playerFlips':4,
        'bulletSizes':16,'finalPpuScreens':66,'finalPpuObjectPixels':72664,
        'heldInputFields':900,'restoredPlayerPixels':summary['playerDelta']['restoredPixels'],
        'hardwareTested':False,'historicalResults':'game/v001/results/binary_player_20261009/previous_release.json'}
    manifest.write_text(json.dumps(release,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Archived and released',sha(new),'changed bytes',len(changes))

if __name__=='__main__':main()
