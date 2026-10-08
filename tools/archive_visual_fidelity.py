"""Archive inspected real-PPU comparisons and the evidence for art repairs."""
from pathlib import Path
import gzip
import hashlib
import json
import shutil
import zipfile
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build'
GAME=ROOT/'game/v001'
OUT=GAME/'results/visual_fidelity_20261008'
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'


def main():
 OUT.mkdir(exist_ok=True)
 try:font=ImageFont.truetype(FONT,20)
 except OSError:font=ImageFont.load_default(size=20)
 for page,names in enumerate([['foliage','enemies','projectiles'],['boss','player_shots','overlap']],1):
  sheet=Image.new('RGB',(1536,3*530),(24,24,30));d=ImageDraw.Draw(sheet)
  for row,name in enumerate(names):
   for col,(folder,title) in enumerate([('visual_precolor','Pre-color release'),('visual_before','Before repair'),('visual_fixed','After repair')]):
    im=Image.open(BUILD/folder/(name+'.png'));im=im.resize((im.width*2,im.height*2),Image.Resampling.NEAREST)
    d.text((col*512+8,row*530+6),f'{name} | {title}',font=font,fill='white');sheet.paste(im,(col*512,row*530+36))
  sheet.save(OUT/f'ppu_comparison_{page}.png')
 names={1:'Bush: opaque foliage recovered',4:'Tree: leaf detail recovered',3:'Enemy: original shape and red cap',7:'Blue shot: original rotation preserved',14:'Boss face: horns and dark details',31:'Boss fireball: restored body, warm-white core'}
 sheet=Image.new('RGB',(1200,len(names)*190+55),(44,40,50));d=ImageDraw.Draw(sheet)
 d.text((8,8),'Recording crops are color references; their pose/scale may differ from the frozen sprite.',font=font,fill='white')
 for row,(asset,title) in enumerate(names.items()):
  y=55+row*190
  d.text((8,y),f'{asset:02d} {title}',font=font,fill='white')
  for col,(label,path) in enumerate([('Recording RGB',GAME/f'assets/bg_color/{asset:02d}_source.png'),('Extracted alpha',GAME/f'assets/bg_color/{asset:02d}_source.png'),('Pre-color structure',GAME/f'assets/{asset:02d}.png'),('Repaired color',GAME/f'assets/bg_color/{asset:02d}_color.png')]):
   d.text((col*300+8,y+28),label,font=font,fill=(190,190,200))
   im=Image.open(path).convert('RGBA')
   if col==0:im.putalpha(255)
   scale=min(280/im.width,124/im.height);im=im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.NEAREST)
   sheet.paste(im,(col*300+8,y+57),im)
 sheet.save(OUT/'recording_reference_comparison.png')
 with zipfile.ZipFile(OUT/'matched_captures.zip','w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for folder in ['visual_precolor','visual_before','visual_fixed','visual_fixed_mono']:
   for p in sorted((BUILD/folder).iterdir()):
    if p.is_file():z.write(p,folder+'/'+p.name)
 for name in ['visual_repair.json','shape_regression.json']:
  source=GAME/'assets/bg_color/silhouette_repair.json' if name=='visual_repair.json' else BUILD/'visual_shape_regression.json'
  if source.exists():shutil.copy2(source,OUT/name)
 for folder in ['color','objects','packed','controls','pause','display','held','boss','stumble','stress','audio_quick','boss_profile_visual','smooth_depth']:
  src=BUILD/'game_v001'/folder
  for filename in ['summary.json','color_summary.json','tables.json']:
   if (src/filename).exists():shutil.copy2(src/filename,OUT/(folder+'_'+filename))
  for filename in ['emulator.log','test.lua','trace.jsonl',*(['timings.jsonl'] if folder=='boss_profile_visual' else [])]:
   if (src/filename).exists():(OUT/(folder+'_'+filename+'.gz')).write_bytes(gzip.compress((src/filename).read_bytes(),mtime=0))
 for source,target in [(BUILD/'game_v001/cache_compare_visual/comparison.json','render_fixture_summary.json'),(BUILD/'game_v001/road_visual.json','natural_profile.json'),(BUILD/'game_v001/scaled_assets_verified.json','scaled_assets.json')]:
  if source.exists():shutil.copy2(source,OUT/target)
 (OUT/'SHA256SUMS.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='SHA256SUMS.json'},indent=2)+'\n')
 print(OUT)

if __name__=='__main__':main()
