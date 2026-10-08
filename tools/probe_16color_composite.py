"""原作録画を合成し、画面全体で共通16色のRGB5画像を比較する。"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import import_4bpp_recording as recording

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'game/v001/results/palette_composite_20261009'


def fill_holes(mask):
    h,w=mask.shape;outside=np.zeros_like(mask)
    stack=[(y,x) for y in range(h) for x in range(w) if y in (0,h-1) or x in (0,w-1)]
    while stack:
        y,x=stack.pop()
        if not (0<=y<h and 0<=x<w) or mask[y,x] or outside[y,x]:continue
        outside[y,x]=True
        stack.extend(((y-1,x),(y+1,x),(y,x-1),(y,x+1)))
    return ~outside


def cut(image,kind):
    a=np.array(image).astype(int);r,g,b=a.transpose(2,0,1)
    sky=(b>150)&(r>110)&(g<180)&(b>r+20)&(b>g+45)
    if kind=='sky':mask=~sky
    elif kind=='purple':mask=(((r>g*1.15)&(b>g+20))|(r+g+b>650))&~sky
    elif kind=='tree':
        y,x=np.indices(r.shape)
        green=(g>r+15)&(g>b+10)&(y<74)&(x>4)&(x<50)
        trunk=(r>g*1.1)&(g>b*1.1)&(y>64)&(x>17)&(x<43)
        mask=fill_holes(green|trunk)
    elif kind=='fire':
        # 空中の炎なので背景の紫と背後の緑だけを除く。白・灰・黒い内部も残す。
        mask=(~sky)&~((g>r+10)&(g>b+10))
    else:raise ValueError(kind)
    return Image.fromarray(np.dstack((a.astype(np.uint8),mask.astype(np.uint8)*255)))


def rgb5(a):
    q=(np.asarray(a).astype(np.int32)*31+127)//255
    return (q*8+(q>>2)).astype(np.uint8)


def indexed(image,palette,dither=False):
    if dither:
        p=Image.new('P',(1,1));p.putpalette(palette.flatten().tolist()*16)
        values=np.array(image.quantize(palette=p,dither=Image.Dither.FLOYDSTEINBERG))%16
    else:
        a=np.array(image).astype(np.int32)
        values=((a[:,:,None,:]-palette.astype(np.int32))**2).sum(3).argmin(2).astype(np.uint8)
    out=Image.fromarray(values,'P');out.putpalette(palette.flatten().tolist()*16)
    assert len(out.getcolors())==16 and np.array(out).max()<16
    assert np.array_equal(rgb5(out.convert('RGB')),np.array(out.convert('RGB')))
    return out


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--video',type=Path,default=recording.VIDEO)
    args=parser.parse_args();recording.VIDEO=args.video
    DEST.mkdir(parents=True,exist_ok=True)
    base=recording.frame(86.5);base.save(DEST/'base_recording.png')
    composite=base.copy()
    layers=[('enemy',38,[135,78,219,115],'sky',[8,31]),
            ('purple_bullet',32.133333,[180,100,215,145],'purple',[109,28]),
            ('red_blue_bullets',32.133333,[230,54,309,102],'sky',[202,28]),
            ('tree',50,[54,96,110,184],'tree',[258,130]),
            ('explosion',77,[152,103,193,143],'fire',[200,163])]
    provenance=[]
    for name,t,box,kind,at in layers:
        crop=recording.frame(t).crop(box);crop.save(DEST/f'{name}_capture.png')
        rgba=cut(crop,kind);rgba.save(DEST/f'{name}.png')
        mask=np.array(rgba)[:,:,3]!=0
        assert np.array_equal(np.array(rgba)[:,:,:3][mask],np.array(crop)[mask]),'cutout repainted'
        assert at[0]+rgba.width<=320 and at[1]+rgba.height<=224
        composite.paste(rgba,at,rgba)
        provenance.append({'name':name,'seconds':t,'crop':box,'position':at,'mask':kind})
    composite.save(DEST/'composite_original.png')
    # パレットは原作の合成画像から学習。現行ROMの手選びの配色は使わない。
    training=Image.fromarray(rgb5(composite))
    learned=training.quantize(colors=16,method=Image.Quantize.MEDIANCUT,kmeans=20,dither=Image.Dither.NONE)
    palette=rgb5(np.array(learned.getpalette()[:48]).reshape(16,3))
    assert len(np.unique(palette,axis=0))==16
    plain=indexed(composite,palette);dither=indexed(composite,palette,True)
    plain.save(DEST/'composite_16colors.png');dither.save(DEST/'composite_16colors_dither.png')
    panel=Image.new('RGB',(960,248),(35,35,35));draw=ImageDraw.Draw(panel)
    for n,(im,label) in enumerate(((composite,'Original composite'),(plain,'16 colors / RGB5 / no dither'),(dither,'16 colors / RGB5 / dither'))):
        draw.text((n*320+5,6),label,fill='white');panel.paste(im.convert('RGB'),(n*320,24))
    panel.resize((1920,496),Image.Resampling.NEAREST).save(DEST/'comparison.png')
    swatches=Image.new('RGB',(640,64));draw=ImageDraw.Draw(swatches)
    for n,c in enumerate(palette):
        x=n*40;draw.rectangle((x,0,x+39,63),fill=tuple(c));draw.text((x+3,4),str(n),fill='white' if sum(c)<390 else 'black')
    swatches.save(DEST/'palette.png')
    summary={'video':str(args.video),'videoSha256':hashlib.sha256(args.video.read_bytes()).hexdigest(),
             'baseSeconds':86.5,'nativeCrop':[480,204,960,672],'size':[320,224],'layers':provenance,
             'originalColors':len(composite.getcolors(320*224)),
             'quantizedColors':len(plain.getcolors()),'ditherColors':len(dither.getcolors()),
             'paletteRgb8':palette.tolist(),'paletteRgb5':((palette.astype(int)*31+127)//255).tolist(),
             'method':'whole-image median cut with Pillow kmeans=20; RGB5 palette; same palette for both variants',
             'transparencyReserved':False,'runtimeChanged':False}
    (DEST/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'originalColors':summary['originalColors'],'outputColors':summary['quantizedColors'],'directory':str(DEST)},ensure_ascii=False))


if __name__=='__main__':main()
