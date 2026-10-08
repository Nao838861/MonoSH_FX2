"""自機の録画取り込みと同じ320x224原画から敵・地上物・効果を切り出す。"""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import numpy as np
from PIL import Image, ImageDraw
from build_game import GAME

VIDEO=Path('D:/HomeBrew/MonoSH/tmp/スペースハリアー録画１.mp4')
ASSETS=GAME/'assets'
OUT=ASSETS/'color4'
CUTS={
    0:(10,(219,155,318,194),'green'),
    1:(38,(218,159,309,191),'dry_bush'),
    2:(10,(100,108,143,136),'sky'),
    3:(38,(139,80,214,114),'sky'),
    4:(50,(54,96,110,184),'tree'),
    6:(32.25,(193,105,237,154),'purple'),
    7:(32.5,(207,95,278,149),'blue'),
    8:(34,(88,105,137,142),'red'),
    11:(32.25,(152,54,181,83),'metal'),
    12:(32.8,(80,98,132,146),'metal'),
    13:(94,(106,64,152,90),'dragon'),
    14:(94,(119,8,157,62),'dragon'),
    31:(60,(156,130,180,151),'fire'),
    5:(93.25,(128,110,186,158),'fire'),
    39:(93.3,(109,98,145,131),'fire'),
    40:(93.45,(74,78,125,128),'fire'),
    41:(93.5,(67,70,121,125),'fire'),
    32:(32.3,(78,98,133,161),'metal'),
    33:(32.4,(78,98,133,161),'metal'),
    34:(32.5,(78,98,133,161),'metal'),
    35:(32.6,(78,98,133,161),'metal'),
    36:(32.8,(78,98,133,161),'metal'),
}

def frame(seconds):
    r=subprocess.run(['ffmpeg','-v','error','-ss',str(seconds),'-i',str(VIDEO),'-vf',
        'crop=960:672:480:204,scale=320:224:flags=neighbor','-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],capture_output=True,check=True)
    return Image.frombytes('RGB',(320,224),r.stdout)

def largest_component(mask):
    """背景の地平線と、対象物の輪郭を8近傍の連結領域で分離する。"""
    seen=np.zeros_like(mask);best=[];height,width=mask.shape
    for y,x in zip(*np.nonzero(mask)):
        if seen[y,x]:continue
        seen[y,x]=True;stack=[(y,x)];group=[]
        while stack:
            yy,xx=stack.pop();group.append((yy,xx))
            for dy in (-1,0,1):
                for dx in (-1,0,1):
                    ny,nx=yy+dy,xx+dx
                    if 0<=ny<height and 0<=nx<width and mask[ny,nx] and not seen[ny,nx]:
                        seen[ny,nx]=True;stack.append((ny,nx))
        if len(group)>len(best):best=group
    out=np.zeros_like(mask)
    for y,x in best:out[y,x]=True
    return out

def hull_mask(mask):
    # 炎の白い中心と黒い内部模様も、着色部分が囲む領域として残す。
    points=sorted((int(x),int(y)) for y,x in zip(*np.nonzero(mask)))
    if len(points)<3:return mask
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    lower=[];upper=[]
    for p in points:
        while len(lower)>1 and cross(lower[-2],lower[-1],p)<=0:lower.pop()
        lower.append(p)
    for p in reversed(points):
        while len(upper)>1 and cross(upper[-2],upper[-1],p)<=0:upper.pop()
        upper.append(p)
    im=Image.new('L',(mask.shape[1],mask.shape[0]));ImageDraw.Draw(im).polygon(lower[:-1]+upper[:-1],fill=255)
    return np.array(im)>0

def cut(image,box,kind):
    a=np.array(image.crop(box)).astype(np.int32);r,g,b=a.transpose(2,0,1)
    sky=(b>150)&(r>110)&(g<165)&(b>r+25)&(b>g+55)
    mask=~sky
    if kind=='green':mask=(g>r+30)&(g>b+25)&(r<110)
    if kind=='dry_bush':mask=((r>g*.8)&(g>b*1.2)|(r+g+b<100))&~sky
    if kind=='tree':
        yy=np.indices(r.shape)[0]
        mask=((g>r+25)&(g>b+25)&(r<125))|((r>g*1.15)&(g>b*1.2)&(yy>r.shape[0]*.55))
    if kind=='purple':mask=(((b>r*.8)&(r>g*1.15)&(b>g+20))|(r+g+b>650))&~sky
    if kind=='blue':mask=(((b>r+20)&(b>g+5))|(r+g+b>650))&~sky
    if kind=='red':mask=(r>g+20)&(r>b+5)&~sky
    if kind=='metal':mask=largest_component((abs(r-g)<32)&(abs(g-b)<40)&~sky)
    if kind=='fire':mask=hull_mask((r>150)&(r>g*1.08)&(g>b+35))&~sky&~((g>r+25)&(g>b+25))
    return Image.fromarray(np.dstack((a.astype(np.uint8),mask.astype(np.uint8)*255)))

def main():
    global VIDEO
    p=argparse.ArgumentParser();p.add_argument('--video',type=Path,default=VIDEO);args=p.parse_args()
    VIDEO=args.video
    OUT.mkdir(exist_ok=True)
    images={i:Image.open(ASSETS/f'{i:02d}.png').convert('RGBA') for i in range(44)}
    samples=[];manifest={}
    for i,(seconds,box,kind) in CUTS.items():
        native=frame(seconds);raw=native.crop(box);im=cut(native,box,kind)
        raw.save(OUT/f'{i:02d}_capture.png');im.save(OUT/f'{i:02d}_source.png')
        im=im.resize(images[i].size,Image.Resampling.NEAREST)
        if i in (13,5,39,40,41):
            # 重なった隣の胴・炎を既存素材の輪郭で除く。RGBは録画由来のまま。
            a=np.array(im);a[:,:,3]=np.minimum(a[:,:,3],np.array(images[i])[:,:,3]);im=Image.fromarray(a)
        images[i]=im
        manifest[str(i)]={'seconds':seconds,'crop':box,'mask':kind,'size':im.size}
        if i in (13,5,39,40,41):manifest[str(i)]['alphaMatte']='recording mask intersected with legacy silhouette after resize'
        samples.append((i,raw,im))
    images[37]=images[6].resize(images[37].size,Image.Resampling.NEAREST)
    # 自機は現在の録画版を継承する。死亡など未採取姿勢は対応する輪郭に着色する。
    pose_map={9:0,28:1,29:2,30:3,15:10,16:11,17:12,18:13}
    for i,pose in pose_map.items():images[i]=Image.open(ASSETS/f'player_recording/native16_pose{pose:02d}.png').convert('RGBA').resize((32,48),Image.Resampling.NEAREST)
    for i in range(19,28):
        src=np.array(images[i]);yy=np.indices(src.shape[:2])[0]
        # 録画にない転倒姿勢は既存の輪郭・陰影を保ち、採取済みの服の色を使う。
        rgb=np.zeros_like(src[:,:,:3]);rgb[:]=(25,72,215)
        rgb[yy<24]=(218,38,12);rgb[yy<11]=(220,150,90)
        rgb[src[:,:,:3].sum(axis=2)<128]=(8,8,8)
        src[:,:,:3]=rgb;images[i]=Image.fromarray(src)
    images[10]=Image.open(ASSETS/'recorded_effects/bullet.png').convert('RGBA')
    for i,im in images.items():im.save(OUT/f'{i:02d}.png')
    # 空と地面は別のRGB5 HDMA。物体には輪郭、肌、植物、炎、弾を残す15色。
    palette=[[0,0,0],[1,1,1],[31,31,31],[17,17,18],[7,7,8],
             [2,10,0],[9,23,0],[21,31,12],[10,4,1],[26,17,12],
             [28,3,1],[31,29,3],[3,10,27],[12,25,31],[21,8,26],[31,16,1]]
    (OUT/'palette.json').write_text(json.dumps({'rgb5':palette},indent=2)+'\n')
    provenance={'capturedPlayer':pose_map,'derivedPlayerDeath':list(range(19,28)),
                'existingMonochrome':[38,42,43],'recordedBullet':10,'derivedEnemyBullet':37}
    (OUT/'source.json').write_text(json.dumps({'video':str(VIDEO),'sha256':hashlib.sha256(VIDEO.read_bytes()).hexdigest(),'nativeCrop':[480,204,960,672],'nativeSize':[320,224],'assets':manifest,'otherAssets':provenance},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    preview=Image.new('RGB',(640,((len(samples)+3)//4)*160),(65,65,65));draw=ImageDraw.Draw(preview)
    for n,(i,raw,im) in enumerate(samples):
        x=n%4*160;y=n//4*160;draw.text((x+4,y+2),f'{i:02d}',fill='white');raw.thumbnail((150,65));preview.paste(raw,(x+4,y+20));im.thumbnail((150,65));preview.paste(im,(x+4,y+88),im)
    preview.save(OUT/'captures.png')

if __name__=='__main__':main()
