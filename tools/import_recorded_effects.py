"""録画の実画素から自弾と二枚の遠景を取り出す（AI生成・平滑化なし）。"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'game/v001/assets/recorded_effects'

def rgb5(rgb):
    return np.clip(np.rint(np.asarray(rgb, dtype=float) * 31 / 255), 0, 31).astype(np.uint8)

def indexed(rgba, count=15):
    a=np.asarray(rgba);mask=a[:,:,3]>0
    samples=Image.fromarray(a[:,:,:3][mask][None,:,:]).quantize(count, method=Image.Quantize.MEDIANCUT)
    palette=rgb5(np.array(samples.getpalette(),dtype=np.uint8).reshape(-1,3)[:count])
    palette=np.unique(palette,axis=0)
    rgb=palette.astype(np.int16)*8+(palette.astype(np.int16)>>2)
    dist=((a[:,:,:3,None].astype(np.int32)-rgb.T[None,None,:,:])**2).sum(axis=2)
    ix=np.argmin(dist,axis=2).astype(np.uint8)+1;ix[~mask]=0
    pal=[[0,0,0],*palette.tolist()];pal+= [[0,0,0]]*(16-len(pal))
    out=Image.fromarray(ix).convert('P');out.putpalette([c*8+(c>>2) for p in pal for c in p]+[0]*720)
    out.info['transparency']=0
    return out,pal

def main():
    parser=argparse.ArgumentParser();parser.add_argument('video',type=Path);args=parser.parse_args()
    DEST.mkdir(parents=True,exist_ok=True)
    captures={}
    for frame in (1741,2344):
        raw=subprocess.run(['ffmpeg','-v','error','-i',str(args.video),'-vf',
            f'select=eq(n\\,{frame-1}),crop=960:672:480:204,scale=320:224:flags=neighbor',
            '-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],capture_output=True,check=True).stdout
        captures[frame]=np.array(Image.frombytes('RGB',(320,224),raw))
    # 発射直後は自機が輪の中央を覆う。四象限のうち水色が残る実画素を対称補完。
    # 紫の隙間は透明にし、銃・髪・服を水色の絵へ混入させない。
    src=captures[2344][84:126,209:277];variants=[src,src[:,::-1],src[::-1],src[::-1,::-1]]
    stack=np.stack(variants).astype(np.int16)
    valid=(stack[:,:,:,1]>145)&(stack[:,:,:,2]>155)&(stack[:,:,:,0]<stack[:,:,:,1]+12)
    scores=np.where(valid,stack[:,:,:,1],-1);choice=np.argmax(scores,axis=0)
    pick=np.take_along_axis(stack,choice[None,:,:,None],axis=0)[0].astype(np.uint8)
    mask=valid.sum(axis=0)>=2
    yy,xx=np.indices(mask.shape);radius=np.sqrt(((xx-33.5)/34)**2+((yy-20.5)/21)**2)
    # 中央は全象限に自機が重なる。露出した左側の発光芯の実色で補修する。
    core_samples=src[(radius<.53)&(xx<24)&valid[0]]
    core=np.median(core_samples,axis=0).astype(np.uint8)
    pick[radius<.53]=core;mask[radius<.53]=True
    mask[(radius>.55)&(radius<.68)]=False;mask[radius>1]=False
    bullet=Image.fromarray(np.dstack([pick,mask.astype(np.uint8)*255]))
    bullet.save(DEST/'bullet_source.png');captures_im=Image.fromarray(captures[2344])
    captures_im.crop((209,84,277,126)).save(DEST/'bullet_capture.png')
    im,pal=indexed(bullet.resize((56,32),Image.Resampling.NEAREST));im.save(DEST/'bullet.png')
    (DEST/'bullet_palette.json').write_text(json.dumps({'rgb5':pal},indent=2)+'\n')
    # 空だけの列で背景色を測る。山を含む行全体の中央値では輪郭に穴が開く。
    scene=captures[1741];strip=scene[140:159].astype(np.int16)
    sky=np.median(scene[:153,10:45],axis=1)
    backdrop=np.vstack([sky[140:153],np.repeat(sky[150:151],6,axis=0)])
    diff=((strip-backdrop[:,None,:])**2).sum(axis=2)>625
    green=(strip[:,:,1]>strip[:,:,0]+16)&(strip[:,:,1]>strip[:,:,2]-12)
    observed=diff&~green&(strip[:,:,2]>strip[:,:,1]+12)&(strip[:,:,2]>strip[:,:,0]-12)
    near=green&diff;near[:10]=False
    # 別速度で動く森を除去した跡は透明にしない。山の裾を背後まで延長し、
    # 隠れていた色は同じ録画の最寄りの紫/白/青の画素で補う。
    far=np.zeros_like(observed)
    for x in range(320):
        rows=np.flatnonzero(observed[:,x]);top=min(int(rows[0]) if len(rows) else 12,12)
        far[top:,x]=True
    mountain=strip.copy();known=np.argwhere(observed)
    for y,x in np.argwhere(far&~observed):
        distance=((known-np.array([y,x]))**2).sum(axis=1)
        sy,sx=known[distance.argmin()];mountain[y,x]=strip[sy,sx]
    for name,mask,pixels in [('far',far,mountain),('near',near,strip)]:
        rgba=np.dstack([pixels.astype(np.uint8),mask.astype(np.uint8)*255])
        canvas=Image.new('RGBA',(512,256));patch=Image.fromarray(rgba)
        patch=patch.crop((0,0,256,19));canvas.paste(patch,(0,108))
        # 録画一画面の外側は反転してつなぎ、端の高さと色を連続させる。
        canvas.paste(patch.transpose(Image.Transpose.FLIP_LEFT_RIGHT),(256,108))
        canvas.save(DEST/f'{name}_source.png')
    # 130行の空の基色と131..150行を使い、紫→緑の終端を途中で切らない。
    gradient=rgb5(sky[130:151]).tolist()
    (DEST/'source.json').write_text(json.dumps({'video':str(args.video),'sha256':hashlib.sha256(args.video.read_bytes()).hexdigest(),
        'nativeCrop':[480,204,960,672],'nativeResolution':[320,224],
        'bullet':{'frame':2344,'seconds':78.1,'crop':[209,84,277,126],'output':[56,32],
          'colorPhases':'shot_color_reference/source.json',
          'repair':'自機に隠れた画素を、同一フレームの水色が残る対称象限から補完'},
        'mountains':{'frame':1741,'seconds':58,'crop':[0,140,320,159],'map':[512,256],
          'nativeHorizon':159,'mapHorizon':127,'screenHorizon':104,
          'repair':'森の背後の山裾を不透明に延長し、録画内の最寄りの山の画素で補完'},
        'sceneryDisplay':{'topTrimRows':2,'downPixels':2,'clipAtGround':True},
        'skyNativeStart':130,
        'skyRgb5':gradient},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    preview=Image.new('RGB',(1024,480),(185,123,247));preview.paste(im.convert('RGBA').resize((448,256),Image.Resampling.NEAREST),(20,20),im.convert('RGBA').resize((448,256),Image.Resampling.NEAREST))
    for name in ('far','near'):
        pic=Image.open(DEST/f'{name}_source.png').crop((0,100,512,132)).resize((1024,64),Image.Resampling.NEAREST)
        preview.paste(pic,(0,340),pic)
    preview.save(DEST/'preview.png')

if __name__=='__main__':main()
