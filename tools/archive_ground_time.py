"""自弾の時間色・地面上2行clip・遠景復元の実PPU証跡と通常ROMを保存する。"""
import gzip
import hashlib
import io
import json
import shutil
import tarfile
from PIL import Image,ImageDraw
from build_game import ROOT,BUILD,GAME
from verify_player_mask import verify as player_mask

def main():
    out=GAME/'results/ground_time_20261009';out.mkdir(parents=True,exist_ok=True)
    manifest=ROOT/'releases/v001.json'
    if not (out/'previous_release.json').exists():shutil.copy2(manifest,out/'previous_release.json')
    digest=hashlib.sha256((BUILD/'MonoSHFX2_v001.sfc').read_bytes()).hexdigest()
    result={'romSha256':digest,'hardwareTested':False,'playerMask':player_mask(),'scenarios':{}}
    for name in ['objects','display','held','color','pause']:
        source=BUILD/name
        assert not (source/'error.txt').exists(),name
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
    old=GAME/'results/shot_horizon_20261009'
    comparison=Image.new('RGB',(3*512,2*502),(45,45,45));draw=ImageDraw.Draw(comparison)
    for i,field in enumerate([238,478,718]):
        name=f'display{field:05d}.png';shutil.copy2(BUILD/'display'/name,out/name)
        for row,path in enumerate([old/name,out/name]):
            im=Image.open(path).convert('RGB').resize((512,478),Image.Resampling.NEAREST)
            comparison.paste(im,(i*512,row*502+20))
            draw.text((i*512+4,row*502+4),('WRONG SCENERY CROP' if row==0 else 'FIXED GROUND CROP')+f' CAMERA {i*32}',fill='white')
    comparison.save(out/'horizon_comparison.png')
    close=Image.new('RGB',(1024,3*164),(45,45,45));draw=ImageDraw.Draw(close)
    for row,(label,path) in enumerate([
            ('ORIGINAL',old/'before_display00238.png'),
            ('WRONG SCENERY CROP',old/'display00238.png'),
            ('FIXED GROUND CROP',out/'display00238.png')]):
        strip=Image.open(path).crop((0,90,256,126)).resize((1024,144),Image.Resampling.NEAREST)
        close.paste(strip,(0,row*164+20));draw.text((4,row*164+4),label,fill='white')
    close.save(out/'horizon_closeup.png')
    shots=[Image.open(p).convert('RGB') for p in sorted((BUILD/'held').glob('shot*.png'))]
    assert len(shots)>30
    shots[0].save(out/'stationary_fire.gif',save_all=True,append_images=shots[1:],duration=17,loop=0)
    fixed=[Image.open(BUILD/'objects'/f'objview{n:05d}.png').convert('RGB') for n in range(308,341,4)]
    fixed[0].save(out/'fixed_size_time_colors.gif',save_all=True,append_images=fixed[1:],duration=67,loop=0)
    grid=Image.new('RGB',(4*512,502),(45,45,45));draw=ImageDraw.Draw(grid)
    for i,n in enumerate(range(312,325,4)):
        raw=(BUILD/'objects'/f'objview{n:05d}_oam.bin').read_bytes()
        pals={((raw[j*4+3]>>1)&7) for j in range(32) if raw[j*4+1]!=240 and raw[j*4+3]&14}
        assert len(pals)==1,pals
        im=Image.open(BUILD/'objects'/f'objview{n:05d}.png').resize((512,478),Image.Resampling.NEAREST)
        grid.paste(im,(i*512,24));draw.text((i*512+4,5),f'FIELD {n} / PALETTE {next(iter(pals))}',fill='white')
    grid.save(out/'fixed_size_time_colors.png')
    (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    shutil.copy2(BUILD/'MonoSHFX2_v001.sfc',ROOT/'releases/MonoSHFX2_v001.sfc')
    meta=json.loads(manifest.read_text(encoding='utf-8'))
    phases=json.loads((GAME/'assets/recorded_effects/bullet_color_phases.json').read_text(encoding='utf-8'))
    ppu=json.loads((out/'objects_objects_ppu.json').read_text())
    meta.update({'previousRomSha256':json.loads((out/'previous_release.json').read_text())['romSha256'],
        'romSha256':digest,'verificationReport':'game/v001/RESULTS_20261009_GROUND_TIME.md',
        'verificationResults':'game/v001/results/ground_time_20261009',
        'verificationKind':'自弾を時間色へ修正。地面の上2行だけをclipし、山・森林を全復元して下へ2ドット表示。三カメラ・実PPU・反転とclip・ポーズ・二値切替を検証。',
        'sceneryDisplay':{'groundTopClipRows':2,'downPixels':2,'sceneryTrimRows':0,'projectionHorizon':104,'visibleGroundStart':106},
        'validation':{'baseCommit':'e8a1f64','finalPpuScreens':ppu['screens'],
            'finalPpuObjectPixels':ppu['checkedObjectPixels'],'playerPoses':17,'playerFlips':4,
            'bulletSizes':16,'bulletPaletteGroups':4,'bulletTimeFramesPerPhase':4,'bulletTimeCycleFrames':16,
            'bulletClock':'globalLogicFrame','fixedSizeTimePalettes':ppu['fixedSizeTimePalettes'],
            'bulletFlips':ppu['bulletFlips'],'bulletClipCenters':ppu['bulletClipCenters'],
            'cameraOffsets':[0,32,64],'stationaryFireFields':900,
            'colorToggleSamples':json.loads((out/'color_color_summary.json').read_text())['samples'],
            'pauseObjColorFrozen':result['scenarios']['pause']['pauseObjColorFrozen'],
            'hardwareTested':False,'historicalResults':'game/v001/results/ground_time_20261009/previous_release.json'}})
    meta['objColor'].pop('bulletSizePalette',None)
    meta['objColor'].update({'bulletClock':'globalLogicFrame','bulletFramesPerPhase':4,'bulletCycleFrames':16,
        'bulletCycleTiming':'仮設定。原作の正確な周期は未同定。','bulletPhaseRgb5':phases['rgb5']})
    meta['scenarioFrames'].update({'objects':360,'display':720,'held':900,'color':360,'pause':360})
    manifest.write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Archived and released',digest)

if __name__=='__main__':main()
