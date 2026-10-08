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
    from import_4bpp_cutouts import main as import_cutouts
    import_cutouts()

if __name__=="__main__":main()
