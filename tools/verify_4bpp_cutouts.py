"""切り抜きの元画素・透明・ディザなし減色・ROMへの配置を独立に検査する。"""
import hashlib
import json
import struct
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from build_game import ROOT,BUILD,GAME
from probe_16color_composite import fill_holes

DEST=GAME/'results/cutouts_20261009'

def main():
 assets=GAME/'assets/color4';pack=BUILD/'assets4';rom=(BUILD/'MonoSHFX2_v001.sfc').read_bytes()
 source=json.loads((assets/'source.json').read_text(encoding='utf-8'))
 assert source['shapePolicy']['dither'] is False
 assert source['shapePolicy']['trainingBackgroundExcluded']
 pal=np.array(json.loads((assets/'palette.json').read_text())['rgb5'],dtype=int);pal=pal*8+(pal>>2)
 assert pal.shape==(16,3) and len(np.unique(pal,axis=0))==16
 assert tuple(pal[0])==(0,0,0)
 table=(pack/'bullet_variants.bin').read_bytes();records=[];total=0;source_pixels=0
 for i in range(44):
  native=np.array(Image.open(assets/f'{i:02d}_native.png').convert('RGBA'))
  mask=native[:,:,3]>0
  im=Image.open(assets/f'{i:02d}.png');index=np.array(im)
  assert im.mode=='P' and im.info.get('transparency')==0
  assert np.array_equal(index!=0,mask),f'{i}: alpha changed during reduction'
  assert max(im.size)<=128
  expected=np.zeros(mask.shape,dtype='uint8')
  expected[mask]=1+((native[:,:,:3][mask,None,:].astype(int)-pal[None,1:,:])**2).sum(2).argmin(1)
  assert np.array_equal(index,expected),f'{i}: nearest palette mapping changed / dither'
  for phase in range(3) if i in (6,7,8,31,37) else (0,):
   pix=np.array(Image.open(assets/f'{i:02d}_hue{phase}.png')) if i in (6,7,8,31,37) else index
   assert np.array_equal(pix!=0,mask),f'{i}/{phase}: color phase changes alpha'
   bank,_,offset=struct.unpack_from('<BBH',table,i*12+phase*4)
   linked=np.stack([np.frombuffer(rom,dtype='uint8',count=im.width,offset=(bank-0x40)*65536+offset+y*256) for y in range(im.height)])
   assert np.array_equal(pix,linked),f'{i}/{phase}: linked ROM differs'
  if str(i) in source['assets']:
   original=np.array(Image.open(assets/f'{i:02d}_capture.png').convert('RGB'))
   cut=np.array(Image.open(assets/f'{i:02d}_source.png').convert('RGBA'));opaque=cut[:,:,3]>0
   assert np.array_equal(original[opaque],cut[:,:,:3][opaque]),f'{i}: recording RGB changed'
   if i in (0,1):
    assert np.array_equal(fill_holes(opaque),opaque),f'{i}: grass contains artificial alpha holes'
    x,y=(50,22) if i==0 else (50,8)
    assert opaque[y,x] and original[y,x,1]>180,f'{i}: bright leaf was removed'
   source_pixels+=int(opaque.sum())
  if i in (5,39,40,41):
   legacy=np.array(Image.open(GAME/f'assets/{i:02d}.png').convert('RGBA'))
   assert native.shape==legacy.shape and np.array_equal(mask,legacy[:,:,3]>0),f'{i}: explosion outline changed'
   reduced=np.array(im.convert('RGBA'))
   assert np.array_equal(reduced[:,:,:3].mean(2)[mask]>=128,legacy[:,:,:3].mean(2)[mask]>=128),f'{i}: explosion pattern changed'
  total+=int(mask.sum());records.append({'asset':i,'size':im.size,'opaquePixels':int(mask.sum()),'colors':len(np.unique(index[mask]))})
 DEST.mkdir(parents=True,exist_ok=True)
 examples=[0,1,2,3,4,11,12,13,14,5,39,40,41,31]
 sheet=Image.new('RGB',(1024,((len(examples)+3)//4)*220),(20,20,20));d=ImageDraw.Draw(sheet)
 for n,i in enumerate(examples):
  x=n%4*256;y=n//4*220;label='legacy pattern' if i in (5,39,40,41) else 'cutout'
  d.text((x+4,y+4),f'{i:02d}: {label} / 16 colors',fill='white')
  for col,name in enumerate((f'{i:02d}_source.png',f'{i:02d}.png')):
   im=Image.open(assets/name).convert('RGBA');scale=min(120/im.width,185/im.height)
   im=im.resize((max(1,int(im.width*scale)),max(1,int(im.height*scale))),Image.Resampling.NEAREST)
   sheet.paste(im,(x+col*128+(128-im.width)//2,y+27),im)
 sheet.save(DEST/'materials.png')
 summary={'romSha256':hashlib.sha256(rom).hexdigest(),'assetsVerified':44,'captureAssetsVerified':len(source['assets']),
  'sourceOpaquePixelsVerified':source_pixels,'opaquePixelsVerified':total,'sourceAlphaChanges':0,'packedAlphaChanges':0,
  'nearestPaletteChanges':0,'dither':False,'totalPaletteColors':16,'opaquePaletteColors':15,
  'trainingBackgroundExcluded':True,'legacyShapePolicyReplacedBy':'recording cutouts and uniform nearest scaling; normal bullet rotation masks retained at half size',
  'paddingAsset':43,'paletteRgb5':json.loads((assets/'palette.json').read_text())['rgb5'],'assets':records}
 summary.update(grassInternalAlphaHoles=0,legacyExplosionPatternsVerified=[5,39,40,41])
 (DEST/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 print(f'Cutouts: 44 assets; {source_pixels} recording pixels unchanged; alpha, nearest-color mapping and ROM match; no dither')

if __name__=='__main__':main()
