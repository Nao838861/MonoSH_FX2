"""録画からの減色と、実PPUでの通常弾の色周期を一緒に保存する。"""
import hashlib
import io
import json
import zipfile
import numpy as np
from PIL import Image,ImageDraw
from build_game import ROOT,GAME

DEST=GAME/'results/color_review_20261009'

def main():
 manifest=json.loads((ROOT/'releases/4bpp30_color.json').read_text())
 proof=json.loads((GAME/'results/cutouts_20261009/summary.json').read_text())
 assert proof['romSha256']==manifest['sha256']
 assert hashlib.sha256((ROOT/manifest['rom']).read_bytes()).hexdigest()==manifest['sha256']
 data=GAME/'results/four_bpp_20261008/color';player_cases=set();bullet_ages=set()
 for scenario in ('players','bullets'):
  assert manifest['scenarios'][scenario]['romSha256']==manifest['sha256']
  with zipfile.ZipFile(data/scenario/'samples.zip') as z:
   for name in z.namelist():
    if not name.endswith('_meta.json'):continue
    meta=json.loads(z.read(name));p=meta.get('playerInput')
    if scenario=='players' and p:player_cases.add((p['asset'],p['flags'],p['center'],p['bottom']))
    bullet_ages.update(meta.get('bulletAges') or [])
 assert len(player_cases)==408 and bullet_ages==set(range(64))
 DEST.mkdir(parents=True,exist_ok=True)
 with zipfile.ZipFile(data/'bullets/screens.zip') as z:
  names=sorted(n for n in z.namelist() if n.startswith('anim') and 240<=int(n[4:9])<368)
  frames=[Image.open(io.BytesIO(z.read(n))).convert('RGB').crop((32,24,224,156)).resize((576,396),Image.Resampling.NEAREST) for n in names]
  assert len(frames)==64,'color cycle screenshots incomplete'
  frames[0].save(DEST/'bullet_cycle.gif',save_all=True,append_images=frames[1:],duration=[30 if i%3!=2 else 40 for i in range(64)],loop=0,optimize=False)
 examples=[(9,'Player'),(14,'Boss face'),(13,'Boss body'),(4,'Tree'),(0,'Grass'),(1,'Bush'),(3,'Enemy'),(12,'Metal enemy')]
 panel=Image.new('RGB',(1024,448),(20,20,20));d=ImageDraw.Draw(panel)
 for n,(i,title) in enumerate(examples):
  im=Image.open(GAME/f'assets/{"obj_color" if i==9 else "color4"}/{i:02d}.png').convert('RGBA')
  factor=min(244/im.width,195/im.height);im=im.resize((int(im.width*factor),int(im.height*factor)),Image.Resampling.NEAREST)
  x=n%4*256;y=n//4*224;d.text((x+4,y+4),title,fill='white');panel.paste(im,(x+(256-im.width)//2,y+25),im)
 panel.save(DEST/'materials.png')
 summary={'romSha256':manifest['sha256'],'dither':False,'palette':'one shared 15 colors + transparent; player has dedicated palette',
  'bulletCycleTicks':32,'rotationTicks':64,'bulletAgesVerified':64,'playerCasesVerified':408,
  'capturedAssetsVerified':proof['captureAssetsVerified'],'recordingOpaquePixelsVerified':proof['sourceOpaquePixelsVerified'],
  'bossShot':'original recording orange flames; no normal-bullet hue remapping'}
 (DEST/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 print('Cutout colors: 408 player cases, 64 bullet ages; actual PPU animation saved')

if __name__=='__main__':main()
