"""承認済みの物体切り抜きと同じ方法で、共通15色＋透明へ減色する。"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import import_4bpp_recording as rec
from probe_16color_objects import cut_tree, cut_sky, mask_image
from probe_16color_composite import fill_holes, rgb5

OUT=rec.OUT
PLAYERS={9,*range(15,31)}
BULLETS={6,7,8,31,37}
EXPLOSIONS=(5,39,40,41)
# 各矩形の物体の外周。内部の明るい葉・暗部へ色キーを適用しない。
BOUNDARIES={
 0:[(6,34),(7,28),(8,24),(8,18),(13,17),(17,13),(21,13),(22,9),(25,8),(25,6),
    (29,6),(30,4),(33,5),(35,4),(38,5),(41,4),(44,5),(46,4),(49,5),(51,4),
    (54,5),(58,5),(60,8),(63,9),(64,14),(68,16),(72,17),(74,19),(77,20),
    (76,22),(77,24),(76,28),(74,30),(75,32),(70,33),(66,34),(62,35),(59,36),
    (56,38),(54,39),(50,39),(48,41),(47,43),(44,43),(42,44),(39,44),(36,43),
    (35,42),(31,41),(29,39),(30,36),(30,34),(24,34),(23,35),(20,36),(15,36),(10,36),(8,35)],
 1:[(6,34),(6,27),(8,23),(11,21),(14,20),(16,18),(18,17),(20,13),(23,11),
    (27,12),(29,9),(32,8),(35,9),(36,7),(39,6),(42,6),(44,4),(48,6),(50,4),
    (53,5),(54,3),(57,4),(59,6),(62,3),(65,4),(67,3),(71,4),(76,4),(78,5),
    (81,4),(85,4),(87,6),(89,5),(92,6),(95,5),(99,5),(101,7),(104,7),
    (105,10),(108,11),(109,17),(110,19),(108,20),(111,21),(111,24),
    (106,25),(103,26),(99,26),(97,27),(94,27),(89,28),(89,32),(87,34),
    (84,35),(80,36),(78,37),(72,37),(70,36),(65,36),(64,38),(61,37),
    (58,39),(56,40),(52,39),(50,40),(46,39),(44,37),(42,38),(39,37),
    (37,38),(35,36),(28,36),(25,35),(23,36),(20,36),(18,35),(9,35)],
 14:[(0,0),(34,0),(34,30),(30,31),(29,35),(29,39),(25,41),
     (20,41),(16,38),(14,34),(14,31),(0,31)],
}
# 小型敵は同じ位置を追跡して各開閉姿勢を採る。自機と重ならない左側を使う。
CUTS={
 0:(9,(140,150,220,196),'grass'),1:(41,(128,151,245,197),'grass'),
 2:(10,(100,108,143,136),'sky'),3:(38,(135,78,219,115),'sky'),
 4:(50,(54,96,110,184),'tree'),
 6:(32.133333,(180,100,215,145),'purple'),
 7:(31.75,(239,87,276,116),'blue'),8:(34,(88,105,137,142),'red'),
 11:(32.25,(152,54,181,83),'metal'),12:(32.866667,(76,95,134,150),'metal'),
 13:(63,(144,35,192,69),'body'),14:(62,(79,101,114,144),'face'),
 31:(63,(142,165,191,220),'fire'),
 32:(32.333333,(78,98,133,143),'metal'),
 33:(32.466667,(78,98,133,149),'metal'),
 34:(32.6,(76,95,134,150),'metal'),
 35:(32.733333,(76,95,134,150),'metal'),
 36:(32.866667,(76,95,134,150),'metal'),
}

def extract(rgb,kind,background=None,boundary=None):
 a=np.array(rgb).astype(int);r,g,b=a.transpose(2,0,1)
 foreground=np.max(np.abs(a-background[:,None,:]),axis=2)>18 if background is not None else np.array(cut_sky(rgb))[:,:,3]>0
 if kind=='tree':return cut_tree(rgb)
 if kind in ('grass','face'):
  outline=Image.new('L',rgb.size);ImageDraw.Draw(outline).polygon(boundary,fill=255)
  mask=np.array(outline)>0
  if kind=='face':mask&=foreground
  if kind=='grass':
   # 外周のすぐ外にある山の青灰色だけを落とし、草の内部は色で抜かない。
   y=np.indices(mask.shape)[0]
   mountain=(y<12)&(b>g*.85)&(b>r*.95)
   mask=fill_holes(mask&~mountain)
  return mask_image(rgb,mask)
 if kind in ('purple','blue','red'):
  hue={'purple':(r>g*1.15)&(b>g+20),
       'blue':(b>r+20)&(b>g+5),'red':(r>g+20)&(r>b+5)}[kind]
  seed=rec.largest_component((hue|(r+g+b>650))&foreground)
  return mask_image(rgb,fill_holes(seed))
 if kind=='fire':
  sky=(b>r+20)&(b>g+40)
  return mask_image(rgb,foreground&~sky&~((g>r+10)&(g>b+10)))
 mask=foreground
 if kind=='metal':
  mask=rec.largest_component(mask&((a.max(2)-a.min(2))<95)&(g<=r+12))
  opened=Image.fromarray(mask.astype('uint8')*255).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
  neighborhood=np.array(opened.filter(ImageFilter.MaxFilter(3)))>0
  mask=rec.largest_component(mask&neighborhood)
  mask=fill_holes(mask)
 return mask_image(rgb,mask)

def native_canvas(im,legacy):
 """縦横を別々に伸ばさず、既存の投影比率に透明余白を足す。"""
 bbox=im.getbbox();assert bbox
 im=im.crop(bbox);w,h=legacy.size
 scale=min(max(im.width/w,im.height/h),128/max(w,h))
 size=(max(1,math.ceil(w*scale)),max(1,math.ceil(h*scale)))
 factor=min(size[0]/im.width,size[1]/im.height)
 wh=(max(1,round(im.width*factor)),max(1,round(im.height*factor)))
 if wh!=im.size:im=im.resize(wh,Image.Resampling.NEAREST)
 out=Image.new('RGBA',size);out.paste(im,((size[0]-wh[0])//2,size[1]-wh[1]))
 return out

def minor_coordinate(mask):
 y,x=np.indices(mask.shape);coords=np.column_stack((x[mask],y[mask]));center=coords.mean(0)
 _,vectors=np.linalg.eigh(np.cov(coords.T));minor=vectors[:,0]
 if minor[0]<0:minor=-minor
 distance=(x-center[0])*minor[0]+(y-center[1])*minor[1]
 return np.clip(distance/max(1,abs(distance[mask]).max()),-1,1)

def recorded_ramp(legacy,reference):
 """撮影姿勢の傾きを移さず、撮影画素の短軸方向の階調だけを移す。"""
 a=np.array(reference);mask=a[:,:,3]>0;distance=minor_coordinate(mask)
 positions=np.clip(np.rint((distance+1)*16),0,32).astype(int)
 profile=[]
 for n in range(33):
  # 近傍の実画素の中央値。Bayerやランダムな色は生成しない。
  delta=abs(positions[mask]-n);colors=a[:,:,:3][mask]
  profile.append(np.median(colors[delta<=max(1,delta.min())],axis=0))
 original=np.array(legacy);mask=original[:,:,3]>0;distance=minor_coordinate(mask)
 positions=np.clip(np.rint((distance+1)*16),0,32).astype(int)
 original[:,:,:3]=np.array(profile,dtype='uint8')[positions]
 return Image.fromarray(original).resize((math.ceil(legacy.width/2),math.ceil(legacy.height/2)),Image.Resampling.NEAREST)

def main():
 p=argparse.ArgumentParser();p.add_argument('--video',type=Path,default=rec.VIDEO);args=p.parse_args()
 rec.VIDEO=args.video;OUT.mkdir(exist_ok=True)
 legacy={i:Image.open(rec.ASSETS/f'{i:02d}.png').convert('RGBA') for i in range(44)}
 images={i:im.copy() for i,im in legacy.items()};manifest={};frames={}
 for i,(t,box,kind) in CUTS.items():
  if t not in frames:frames[t]=rec.frame(t)
  raw=frames[t].crop(box)
  frame_array=np.array(frames[t])
  # 岩のコマでは画面左端にも敵がいる。空は画面全体の走査線中央値で測る。
  background=np.median(frame_array if kind=='sky' else frame_array[:,:20],axis=1)[box[1]:box[3]]
  im=extract(raw,kind,background,BOUNDARIES.get(i))
  if kind=='body':
   # 録画では隣の胴が右端に重なる。既存の同じ正面姿勢の外形を採取境界にする。
   template=np.array(legacy[i].resize(raw.size,Image.Resampling.NEAREST))[:,:,3]>0
   im=mask_image(raw,(np.array(im)[:,:,3]>0)&template)
  raw.save(OUT/f'{i:02d}_capture.png');im.save(OUT/f'{i:02d}_source.png')
  assert np.array_equal(np.array(im)[:,:,:3],np.array(raw))
  images[i]=native_canvas(im,legacy[i])
  manifest[str(i)]={'seconds':t,'crop':box,'mask':kind,'size':images[i].size,'resize':'nearest; uniform; transparent padding'}
  if i in BOUNDARIES:manifest[str(i)]['boundary']=BOUNDARIES[i]
 # 白黒版の四枚と同一輪郭・模様を持つ、火球置換前の素材へ戻す。
 for i in EXPLOSIONS:
  images[i]=Image.open(OUT/f'{i:02d}_legacy.png').convert('RGBA')
  assert images[i].size==legacy[i].size
  assert np.array_equal(np.array(images[i])[:,:,3],np.array(legacy[i])[:,:,3])
  legacy[i].convert('RGB').save(OUT/f'{i:02d}_capture.png')
  images[i].save(OUT/f'{i:02d}_source.png')
 # 第4回転姿勢は水平の原画。各姿勢の主軸を既存原画から保持する。
 references=[images[i] for i in (6,7,8)]
 variants={}
 for i in (6,7,8,37):
  variants[i]=[recorded_ramp(legacy[i],im) for im in references]
  images[i]=variants[i][0]
 for i in PLAYERS:images[i]=Image.open(rec.ASSETS/f'obj_color/{i:02d}.png').convert('RGBA')
 images[10]=Image.open(rec.ASSETS/'recorded_effects/bullet_source.png').convert('RGBA').resize((56,32),Image.Resampling.NEAREST)
 # 炎形のボス弾は録画どおり橙色。通常弾の色相を混入させない。
 variants[31]=[images[31].copy() for _ in range(3)]
 for i in CUTS:manifest[str(i)]['size']=images[i].size
 training=[]
 for i,im in images.items():
  if i in PLAYERS or i in (6,7,8,37,38,42,43):continue
  for sample in [im]:
   a=np.array(sample);colors=a[:,:,:3][a[:,:,3]>0]
   if len(colors)>1800:colors=colors[np.linspace(0,len(colors)-1,1800).astype(int)]
   training.append(colors)
 sample=Image.fromarray(rgb5(np.concatenate(training)).reshape(-1,1,3))
 learned=sample.quantize(colors=12,method=Image.Quantize.MEDIANCUT,kmeans=20,dither=Image.Dither.NONE)
 # 出現面積の小さい紫・青・赤が消えないよう、実録画の有彩色を各1色確保する。
 anchors=[]
 for im in references:
  a=np.array(im);colors=a[:,:,:3][a[:,:,3]>0].astype(int)
  chromatic=(colors.max(1)-colors.min(1)>60)&(colors.min(1)<140)
  assert chromatic.any()
  anchors.append(np.median(colors[chromatic],axis=0))
 palette=np.vstack((np.zeros((1,3),dtype=np.uint8),rgb5(np.array(learned.getpalette()[:36]).reshape(12,3)),rgb5(anchors)))
 assert len(np.unique(palette,axis=0))==16
 def quantize(im):
  a=np.array(im);mask=a[:,:,3]>0;index=np.zeros(mask.shape,dtype='uint8')
  index[mask]=1+((a[:,:,:3][mask,None,:].astype(int)-palette[None,1:,:].astype(int))**2).sum(2).argmin(1)
  out=Image.fromarray(index,'P');out.putpalette(palette.flatten().tolist()+[0]*720);out.info['transparency']=0
  return out
 for i,im in images.items():
  im.save(OUT/f'{i:02d}_native.png');quantize(im).save(OUT/f'{i:02d}.png')
 for i,phases in variants.items():
  for phase,im in enumerate(phases):quantize(im).save(OUT/f'{i:02d}_hue{phase}.png')
 (OUT/'palette.json').write_text(json.dumps({'rgb5':((palette.astype(int)*31+127)//255).tolist()},indent=2)+'\n')
 policy={'reference':'recording cutouts; opaque pixels only; same shared palette for all objects',
  'dither':False,'trainingBackgroundExcluded':True,'assets':sorted(CUTS),
  'paletteAllocation':'12 learned object colors; one recorded purple, blue and red each; transparent index 0',
  'bulletShading':'legacy rotation axes; white center; continuous single-hue gradient without dither',
  'bulletCycleTicks':32,'bulletCycle':['purple']*16+['red']*8+['blue']*8,
  'playerRendering':'dedicated original OBJ palette including upstream alpha repairs',
  'grassAlpha':'traced perimeter; bright leaves and dark interior retained; no internal color key',
  'bossFace':'jaw outline only; adjacent body removed',
  'explosions':'original four binary silhouettes and patterns restored; original animation sequence',
  'resize':'uniform nearest-neighbor; transparent padding to existing projected aspect'}
 (OUT/'source.json').write_text(json.dumps({'video':str(args.video),'sha256':hashlib.sha256(args.video.read_bytes()).hexdigest(),
  'nativeCrop':[480,204,960,672],'nativeSize':[320,224],'assets':manifest,'shapePolicy':policy,
  'otherAssets':{'capturedPlayer':sorted(PLAYERS),'legacyRotationMasks':[6,7,8,37],'recordedBullet':10,'existingMonochrome':[38,42,43],
   'legacyExplosionPatterns':list(EXPLOSIONS),'legacyExplosionColorCommit':'aba0c20332a45fdaf1a23a6359aef637f5a13a09',
   'explosionSequence':[5,39,40,41,40,39]}},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 sheet=Image.new('RGB',(1024,6*190),(24,24,24));d=ImageDraw.Draw(sheet)
 for n,i in enumerate(CUTS):
  x=n%4*256;y=n//4*190;d.text((x+4,y+4),f'{i:02d} recording / ROM texture',fill='white')
  for col,im in enumerate((Image.open(OUT/f'{i:02d}_source.png'),Image.open(OUT/f'{i:02d}.png').convert('RGBA'))):
   im=im.convert('RGBA');im.thumbnail((120,156),Image.Resampling.NEAREST)
   sheet.paste(im,(x+col*128,y+25),im)
 sheet.save(OUT/'captures.png')
 print('Imported recording cutouts: common 15 opaque colors + transparency; no dither')

if __name__=='__main__':main()
