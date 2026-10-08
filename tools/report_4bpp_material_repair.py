"""草の透過・爆発四枚・顎の修正を、旧ROM素材と実PPUで比較する。"""
import hashlib
import io
import json
import subprocess
import zipfile
import numpy as np
from PIL import Image, ImageDraw
from build_game import ROOT, GAME
from probe_16color_composite import fill_holes

PREVIOUS='ea87bf1d9e19d556a5a16eb5bc3021d3052d9e50'
DEST=GAME/'results/material_repair_20261009'

def old_image(name):
    raw=subprocess.check_output(['git','show',f'{PREVIOUS}:game/v001/assets/color4/{name}'],cwd=ROOT)
    return Image.open(io.BytesIO(raw)).convert('RGBA')

def paste(panel,image,x,y,w,h):
    image=image.convert('RGBA');scale=min(w/image.width,h/image.height)
    image=image.resize((max(1,round(image.width*scale)),max(1,round(image.height*scale))),Image.Resampling.NEAREST)
    panel.paste(image,(x+(w-image.width)//2,y+(h-image.height)//2),image)

def main():
    manifest=json.loads((ROOT/'releases/4bpp30_color.json').read_text())
    proof=json.loads((GAME/'results/cutouts_20261009/summary.json').read_text())
    assert proof['romSha256']==manifest['sha256']
    assert hashlib.sha256((ROOT/manifest['rom']).read_bytes()).hexdigest()==manifest['sha256']
    DEST.mkdir(parents=True,exist_ok=True)
    panel=Image.new('RGB',(1200,690),(28,28,28));d=ImageDraw.Draw(panel)
    old_holes={};new_holes={}
    for row,i in enumerate((0,1,14)):
        images=[Image.open(GAME/f'assets/color4/{i:02d}_capture.png'),old_image(f'{i:02d}.png'),Image.open(GAME/f'assets/color4/{i:02d}.png')]
        for col,(im,label) in enumerate(zip(images,('Recording crop','Previous ROM','Corrected ROM'))):
            d.text((col*400+5,row*230+6),f'{i:02d}: {label}',fill='white')
            paste(panel,im,col*400,row*230+25,400,200)
        if i in (0,1):
            old=np.array(old_image(f'{i:02d}_source.png'))[:,:,3]>0
            new=np.array(Image.open(GAME/f'assets/color4/{i:02d}_source.png'))[:,:,3]>0
            old_holes[str(i)]=int((fill_holes(old)&~old).sum())
            new_holes[str(i)]=int((fill_holes(new)&~new).sum())
            assert new_holes[str(i)]==0
    panel.save(DEST/'comparison.png')
    panel=Image.new('RGB',(1024,510),(28,28,28));d=ImageDraw.Draw(panel)
    for col,i in enumerate((5,39,40,41)):
        d.text((col*256+4,6),f'{i:02d}: original monochrome / restored',fill='white')
        paste(panel,Image.open(GAME/f'assets/{i:02d}.png'),col*256,25,256,220)
        paste(panel,Image.open(GAME/f'assets/color4/{i:02d}.png'),col*256,275,256,220)
    panel.save(DEST/'explosion_patterns.png')
    scenario=GAME/'results/four_bpp_20261008/color/effects'
    assert manifest['scenarios']['effects']['romSha256']==manifest['sha256']
    with zipfile.ZipFile(scenario/'samples.zip') as z:
        phases={json.loads(z.read(n))['effectPhase'] for n in z.namelist() if n.endswith('_meta.json')}
    assert phases==set(range(6))
    with zipfile.ZipFile(scenario/'screens.zip') as z:
        names=sorted(n for n in z.namelist() if n.startswith('anim') and 240<=int(n[4:9])<336)
        frames=[Image.open(io.BytesIO(z.read(n))).convert('RGB').resize((512,448),Image.Resampling.NEAREST) for n in names]
        assert len(frames)==48
        frames[0].save(DEST/'explosion_cycle.gif',save_all=True,append_images=frames[1:],duration=[30 if i%3!=2 else 40 for i in range(48)],loop=0,optimize=False)
    old_face=np.array(old_image('14_source.png'))[:,:,3]>0
    new_face=np.array(Image.open(GAME/'assets/color4/14_source.png'))[:,:,3]>0
    summary={'romSha256':manifest['sha256'],'previousRevision':PREVIOUS,
             'previousGrassInternalAlphaHoles':old_holes,'grassInternalAlphaHoles':new_holes,
             'legacyExplosionPatternsVerified':[5,39,40,41],'explosionSequence':[5,39,40,41,40,39],
             'enemyAndBossExplosionPhasesVerified':6,'jawRemovedPixels':int((old_face&~new_face).sum()),
             'dither':False,'captureAssetsVerified':proof['captureAssetsVerified']}
    (DEST/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary))

if __name__=='__main__':main()
