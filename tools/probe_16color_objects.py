"""FX2側の物体だけを黒背景へ合成し、黒＋共通15色へディザなしで減色する。"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import import_4bpp_recording as recording
from probe_16color_composite import rgb5, fill_holes

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'game/v001/results/palette_objects_20261009'


def mask_image(rgb,mask):
    a=np.array(rgb)
    return Image.fromarray(np.dstack((a,mask.astype(np.uint8)*255)))


def cut_tree(rgb):
    a=np.array(rgb).astype(int);r,g,b=a.transpose(2,0,1);y,x=np.indices(r.shape)
    # 地面の黄緑を葉へ混ぜない。彩度の高い葉と茶色い幹を分離する。
    leaves=(b<g*.48)&(r<g*.85)&(g>35)&(y<74)
    trunk=(r>g*1.10)&(g>b*1.1)&(y>64)&(x>17)&(x<43)
    seed=recording.largest_component(leaves|trunk)
    edge=np.array(Image.fromarray(seed.astype(np.uint8)*255).filter(ImageFilter.MaxFilter(3)))>0
    dark=(r+g+b<130)
    mask=fill_holes(seed|(edge&dark))
    return mask_image(rgb,mask)


def cut_sky(rgb,purple=False,fire=False):
    a=np.array(rgb).astype(int);r,g,b=a.transpose(2,0,1)
    sky=(b>150)&(r>110)&(g<180)&(b>r+20)&(b>g+45)
    sky|=np.max(np.abs(a-np.median(a[0],axis=0)),axis=2)<=18
    mask=~sky
    if purple:mask&=(((r>g*1.15)&(b>g+20))|(r+g+b>650))
    if fire:mask&=~((g>r+10)&(g>b+10))
    return mask_image(rgb,mask)


def cut_boss_scene(rgb):
    a=np.array(rgb).astype(int);r,g,b=a.transpose(2,0,1);y,x=np.indices(r.shape[:2])
    # このフレームの空の各走査線は左端に露出している。
    sky=np.median(a[:,:20],axis=1)
    background=np.max(np.abs(a-sky[:,None,:]),axis=2)<=16
    boss=(x>=44)&(x<151)&(y>=59)&(y<142)
    # 専用OBJの自機と、それに重なる採取不能な輪の部分は含めない。
    boss&=~((x>=128)&(y>=104))
    flame=Image.new('L',rgb.size);d=ImageDraw.Draw(flame)
    d.polygon([(208,106),(214,108),(221,115),(225,109),(225,100),(222,94),
               (225,87),(222,79),(224,76),(222,72),(223,58),(227,57),
               (233,57),(239,64),(245,59),(260,58),(269,60),(278,59),
               (280,64),(282,71),(278,75),(284,81),(288,85),(288,90),
               (290,96),(292,105),(290,116),(287,124),(283,127),(283,131),
               (275,137),(267,140),(259,140),(255,138),(252,144),(247,149),
               (238,151),(227,150),(218,146),(210,137),(207,127),(208,119)],fill=255)
    flame=np.array(flame)>0
    # 炎の外縁と接する山の青灰色だけを除く。内部の灰色は穴埋めで保つ。
    mountain=(y>=142)&(((b>r+8)&(b>g-3))|((g>r+15)&(g>b-10)))
    flame=fill_holes(flame&~background&~mountain)
    mask=(boss&~background)|flame
    return mask_image(rgb,mask)


def main():
    p=argparse.ArgumentParser();p.add_argument('--video',type=Path,default=recording.VIDEO);args=p.parse_args()
    recording.VIDEO=args.video;DEST.mkdir(parents=True,exist_ok=True)
    base=recording.frame(86.5);base.save(DEST/'base_recording.png')
    scene=cut_boss_scene(base);scene.save(DEST/'boss_scene_cutout.png')
    composite=Image.new('RGB',(320,224));mask=np.array(scene)[:,:,3]>0
    composite.paste(scene,(0,0),scene)
    layers=[('enemy',38,[135,78,219,115],[8,31],'sky'),
            ('purple_bullet',32.133333,[180,100,215,145],[109,28],'purple'),
            ('red_blue_bullets',32.133333,[230,54,309,102],[202,28],'sky'),
            ('tree',50,[54,96,110,184],[258,130],'tree'),
            ('explosion',77,[148,101,198,144],[194,160],'fire')]
    provenance=[]
    for name,t,box,at,kind in layers:
        crop=recording.frame(t).crop(box);crop.save(DEST/f'{name}_capture.png')
        rgba=cut_tree(crop) if kind=='tree' else cut_sky(crop,purple=kind=='purple',fire=kind=='fire')
        rgba.save(DEST/f'{name}.png');local=np.array(rgba)[:,:,3]>0
        assert np.array_equal(np.array(rgba)[:,:,:3][local],np.array(crop)[local]),'source pixels changed'
        xx,yy=at;mask[yy:yy+rgba.height,xx:xx+rgba.width]|=local
        composite.paste(rgba,at,rgba)
        provenance.append({'name':name,'seconds':t,'crop':box,'position':at,'mask':kind})
    original=np.array(composite)
    assert (original[~mask]==0).all(),'background is not black'
    assert not mask[:28].any() and not mask[218:].any(),'HUD/background included'
    Image.fromarray(mask.astype(np.uint8)*255).save(DEST/'foreground_mask.png')
    composite.save(DEST/'objects_original.png')
    # 学習対象は不透明物体だけ。黒背景の広さにパレットを左右させない。
    training=Image.fromarray(rgb5(original[mask]).reshape(-1,1,3))
    learned=training.quantize(colors=15,method=Image.Quantize.MEDIANCUT,kmeans=20,dither=Image.Dither.NONE)
    palette=np.vstack((np.zeros((1,3),dtype=np.uint8),rgb5(np.array(learned.getpalette()[:45]).reshape(15,3))))
    assert len(np.unique(palette,axis=0))==16,'palette has duplicate colors'
    index=np.zeros(mask.shape,dtype=np.uint8)
    index[mask]=1+((original[mask,None,:].astype(int)-palette[None,1:,:].astype(int))**2).sum(2).argmin(1)
    reduced=Image.fromarray(index,'P');reduced.putpalette(palette.flatten().tolist()*16)
    reduced.save(DEST/'objects_16colors.png')
    assert len(reduced.getcolors())==16 and index.max()==15
    assert (index[mask]>0).all() and (index[~mask]==0).all(),'alpha/opaque indices mixed'
    assert np.array_equal(rgb5(reduced.convert('RGB')),np.array(reduced.convert('RGB')))
    panel=Image.new('RGB',(640,248),(30,30,30));d=ImageDraw.Draw(panel)
    for n,(im,label) in enumerate(((composite,'Original objects / black background'),(reduced,'16 colors = black + 15 / no dither'))):
        d.text((n*320+5,6),label,fill='white');panel.paste(im.convert('RGB'),(n*320,24))
    panel.resize((1280,496),Image.Resampling.NEAREST).save(DEST/'comparison.png')
    panel=Image.new('RGB',(672,376),(30,30,30));d=ImageDraw.Draw(panel)
    tree=Image.open(DEST/'tree.png').convert('RGBA')
    clean=Image.new('RGB',tree.size);clean.paste(tree,(0,0),tree)
    tree_rgb=np.array(tree)[:,:,:3];tree_mask=np.array(tree)[:,:,3]>0
    tree_index=np.zeros(tree_mask.shape,dtype=np.uint8)
    tree_index[tree_mask]=1+((tree_rgb[tree_mask,None,:].astype(int)-palette[None,1:,:].astype(int))**2).sum(2).argmin(1)
    tree_quantized=Image.fromarray(palette[tree_index])
    for n,(im,label) in enumerate(((Image.open(DEST/'tree_capture.png'),'Recording crop'),(clean,'Cutout / original colors'),(tree_quantized,'Same shared 16-color palette'))):
        d.text((n*224+4,5),label,fill='white');panel.paste(im.resize((224,352),Image.Resampling.NEAREST),(n*224,24))
    panel.save(DEST/'tree_comparison.png')
    swatches=Image.new('RGB',(640,64));d=ImageDraw.Draw(swatches)
    for n,c in enumerate(palette):
        d.rectangle((n*40,0,n*40+39,63),fill=tuple(c));d.text((n*40+3,4),str(n),fill='white' if sum(c)<390 else 'black')
    swatches.save(DEST/'palette.png')
    summary={'videoSha256':hashlib.sha256(args.video.read_bytes()).hexdigest(),'baseSeconds':86.5,
             'nativeCrop':[480,204,960,672],'size':[320,224],'layers':provenance,'baseMask':'boss/flames only; row sky removed; mountain pixels removed at flame edge',
             'excluded':['sky','mountains','ground','HUD','player (dedicated OBJ palette)','occluded ring under player'],
             'foregroundPixels':int(mask.sum()),'totalColors':len(reduced.getcolors()),'foregroundColors':len(np.unique(index[mask])),
             'backgroundRgb':[0,0,0],'backgroundIndex':0,'opaqueIndices':list(range(1,16)),
             'paletteRgb8':palette.tolist(),'paletteRgb5':((palette.astype(int)*31+127)//255).tolist(),
             'trainingBackgroundExcluded':True,'dither':False,'runtimeChanged':False}
    (DEST/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'foregroundPixels':int(mask.sum()),'totalColors':summary['totalColors'],'foregroundColors':summary['foregroundColors'],'dither':False,'directory':str(DEST)}))


if __name__=='__main__':main()
