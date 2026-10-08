"""実録画の敵・地上物を、透明＋3色×8パレットの固定2bpp原画へ取り込む。"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'game/v001/assets'
DEST = ASSETS / 'bg_color'
# RGB5。組0はタイトル・影、組1..7を録画の色相ごとに共有する。
PALETTES = [
    [[0,0,0],[3,3,3],[16,16,16],[31,31,31]],
    [[0,0,0],[1,7,2],[3,21,4],[16,31,12]],
    [[0,0,0],[9,5,3],[22,14,10],[31,25,19]],
    [[0,0,0],[3,3,5],[15,16,18],[29,29,30]],
    [[0,0,0],[15,1,0],[31,8,0],[31,28,5]],
    [[0,0,0],[6,8,18],[13,18,30],[27,30,31]],
    [[0,0,0],[12,3,13],[24,9,24],[31,24,31]],
    [[0,0,0],[1,7,1],[7,23,6],[29,24,17]],
]
# 秒・native320x224のcrop・マスク。既存の寸法は変更しない。
CUTS = {
    0:(11,(163,148,265,196),'green'),
    1:(41,(136,154,238,194),'bush'),
    2:(10,(100,108,143,136),'sky'),
    3:(38,(139,80,214,114),'sky'),
    4:(50,(59,94,100,184),'tree'),
    6:(32.25,(193,105,237,154),'purple'),
    7:(31.75,(239,87,276,116),'blue'),
    8:(34,(88,105,137,142),'red'),
    11:(32.25,(152,54,181,83),'metal'),
    12:(31.5,(146,45,187,82),'metal'),
    13:(63,(144,35,193,75),'dragon'),
    14:(62,(79,101,114,159),'dragon'),
    31:(63,(142,165,191,220),'fire'),
}

def native(video, seconds):
    raw=subprocess.run(['ffmpeg','-v','error','-ss',str(seconds),'-i',str(video),
        '-vf','crop=960:672:480:204,scale=320:224:flags=neighbor',
        '-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],
        capture_output=True,check=True).stdout
    return Image.frombytes('RGB',(320,224),raw)

def video_hash(path):
    digest=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()

def cut(frame, box, kind):
    a=np.array(frame.crop(box));r,g,b=[a[:,:,i].astype(int) for i in range(3)]
    sky=(b>150)&(r>110)&(g<165)&(b>r+25)&(b>g+55)
    mask=~sky
    if kind=='green':mask=(g>r+30)&(g>b+25)&(r<110)
    if kind=='bush':mask=((g>r+25)&(g>b+20)&(r<120))|((r>g*1.15)&(g>b*1.2)&(r<160))
    if kind=='tree':
        yy=np.indices(r.shape)[0]
        mask=((g>r+25)&(g>b+25)&(r<125))|((r>g*1.15)&(g>b*1.2)&(yy>r.shape[0]*.55))
        xx=np.indices(r.shape)[1]
        mask&=(yy<r.shape[0]*.82)|(abs(xx-r.shape[1]*.5)<r.shape[1]*.15)
    if kind=='purple':mask=(((b>r*.8)&(r>g*1.15)&(b>g+20))|(r+g+b>650))&~sky
    if kind=='blue':mask=(((b>r+20)&(b>g+5))|(r+g+b>650))&~sky
    if kind=='red':mask=(r>g+20)&(r>b+5)&~sky
    if kind=='metal':mask=(abs(r-g)<32)&(abs(g-b)<40)&~sky
    if kind=='fire':mask=(r>150)&(((r>g*1.08)&(g>b+35))|(r+g+b>620))
    if kind in ['metal','purple','blue','red','sky']:
        # 輪郭とつながらない隣の弾、圧縮ノイズを除く。葉はこの処理の対象外。
        seen=np.zeros(mask.shape,dtype=bool);largest=[]
        for y,x in zip(*np.nonzero(mask)):
            if seen[y,x]:continue
            todo=[(y,x)];seen[y,x]=True;component=[]
            while todo:
                cy,cx=todo.pop();component.append((cy,cx))
                for dy,dx in [(0,1),(0,-1),(1,0),(-1,0)]:
                    ny,nx=cy+dy,cx+dx
                    if 0<=ny<mask.shape[0] and 0<=nx<mask.shape[1] and mask[ny,nx] and not seen[ny,nx]:
                        seen[ny,nx]=True;todo.append((ny,nx))
            if len(component)>len(largest):largest=component
        mask[:]=False
        for y,x in largest:mask[y,x]=True
    return Image.fromarray(np.dstack([a,mask.astype(np.uint8)*255]))

def quantize(im, candidates):
    a=np.asarray(im);opaque=a[:,:,3]>=128
    rgb=np.array(PALETTES,dtype=np.int32)[:,1:,:]*255/31
    index=np.zeros(opaque.shape,dtype=np.uint8)
    cells=np.full((16,16),255,dtype=np.uint8)
    preview=np.zeros(a.shape,dtype=np.uint8)
    for ty in range((im.height+7)//8):
        for tx in range((im.width+7)//8):
            sl=np.s_[ty*8:min(im.height,ty*8+8),tx*8:min(im.width,tx*8+8)]
            mask=opaque[sl]
            if not mask.any():continue
            src=a[sl][:,:,:3].astype(float)
            errors=((src[:,:,None,None,:]-rgb[None,None,:,:,:])**2).sum(axis=-1)
            scores=[errors[:,:,p,:].min(axis=-1)[mask].sum() for p in candidates]
            pal=candidates[int(np.argmin(scores))]
            ix=errors[:,:,pal,:].argmin(axis=-1).astype(np.uint8)+1
            ix[~mask]=0;index[sl]=ix;cells[ty,tx]=pal
            preview[sl][:,:,:3]=np.rint(rgb[pal][np.maximum(ix.astype(int)-1,0)]).astype(np.uint8)
            preview[sl][:,:,3]=mask*255
    indexed=Image.fromarray(index).convert('P')
    indexed.putpalette([0,0,0,24,24,24,132,132,132,255,255,255]+[0]*756)
    indexed.info['transparency']=0
    return indexed,Image.fromarray(preview),cells

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('video',type=Path);args=p.parse_args()
    DEST.mkdir(exist_ok=True);frames={};manifest={};allcells=bytearray([255])*11264
    sheet=Image.new('RGB',(1024,7*220),(70,50,90));draw=ImageDraw.Draw(sheet)
    sources={**CUTS}
    for n,asset in enumerate([0,1,2,3,4,6,7,8,11,12,13,14,31]):
        seconds,box,kind=sources[asset]
        if seconds not in frames:frames[seconds]=native(args.video,seconds)
        raw=cut(frames[seconds],box,kind);raw.save(DEST/f'{asset:02d}_source.png')
        size=Image.open(ASSETS/f'{asset:02d}.png').size
        im=raw.resize(size,Image.Resampling.NEAREST)
        if asset in [13,14,31]:
            # 連結した隣の節・炎を切り離すため、既存素材の外形をマットに使う。
            a=np.array(im)
            a[:,:,3]=np.minimum(a[:,:,3],np.array(Image.open(ASSETS/f'{asset:02d}.png').convert('RGBA'))[:,:,3])
            im=Image.fromarray(a)
        choices={'green':[1],'bush':[1,2],'tree':[1,2],'sky':[3,4], 'metal':[3],
                 'blue':[5],'purple':[6],'red':[4],'dragon':[1,2,7],'fire':[4]}[kind]
        indexed,colored,cells=quantize(im,choices)
        indexed.save(DEST/f'{asset:02d}.png');colored.save(DEST/f'{asset:02d}_color.png')
        allcells[asset*256:(asset+1)*256]=cells.tobytes()
        manifest[str(asset)]={'seconds':seconds,'crop':box,'mask':kind,'size':size,'palettes':choices,
            'original_outline_matte':asset in [13,14,31],
            'source_sha256':hashlib.sha256((DEST/f'{asset:02d}_source.png').read_bytes()).hexdigest()}
        x=(n%2)*512;y=(n//2)*220
        draw.text((x,y),f'{asset:02d}  t={seconds}s  crop / 2bpp',fill='white')
        for j,pic in enumerate([raw,colored]):
            pic=pic.copy();pic.thumbnail((240,190),Image.Resampling.NEAREST)
            # 表示だけ整数倍で大きくする。
            scale=max(1,min(240//pic.width,190//pic.height));pic=pic.resize((pic.width*scale,pic.height*scale),Image.Resampling.NEAREST)
            sheet.paste(pic,(x+j*250,y+24),pic)
    # 残る爆発は録画の火色、開く砲台は金属色、影と文字はグレー。
    for asset in range(44):
        if str(asset) in manifest:continue
        if asset in [9,10,*range(15,31),43]:continue
        base=Image.open(ASSETS/f'{asset:02d}.png').convert('RGBA');a=np.array(base)
        pal=4 if asset in [5,39,40,41] else 3 if asset in range(32,37) else 0
        ix=np.where(a[:,:,3]<128,0,np.where(a[:,:,:3].sum(axis=2)>384,3,1)).astype(np.uint8)
        # 既存alphaと輪郭は保持し、録画で確認できない開閉中の形を捏造しない。
        im=Image.fromarray(ix).convert('P');im.putpalette([0,0,0,24,24,24,132,132,132,255,255,255]+[0]*756)
        im.save(DEST/f'{asset:02d}.png',transparency=0)
        for ty in range((base.height+7)//8):
            for tx in range((base.width+7)//8):
                if ix[ty*8:ty*8+8,tx*8:tx*8+8].any():allcells[asset*256+ty*16+tx]=pal
    compact=bytearray();offsets=bytearray()
    for asset in range(44):
        offsets.extend(len(compact).to_bytes(2,'little'))
        path=DEST/f'{asset:02d}.png'
        rows=(Image.open(path).height+7)//8 if path.exists() else 0
        data=allcells[asset*256:asset*256+rows*16]
        data=[15 if x==255 else x for x in data]
        compact.extend(data[i]|data[i+1]<<4 for i in range(0,len(data),2))
    (DEST/'cells.bin').write_bytes(compact)
    (DEST/'offsets.bin').write_bytes(offsets)
    data=bytearray()
    for pal in PALETTES:
        for r,g,b in pal:data.extend((r|g<<5|b<<10).to_bytes(2,'little'))
    (DEST/'palette.bin').write_bytes(data)
    (DEST/'source.json').write_text(json.dumps({'video':str(args.video),'video_sha256':video_hash(args.video),
        'native_crop':[480,204,960,672],'native_size':[320,224],'rgb5':PALETTES,'assets':manifest,
        'fallback':'爆発・砲台開閉は既存alphaを保持して録画に近い色組を割当。'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    sheet.save(DEST/'comparison.png')
    print('13 recorded crops, indexed sources, 8 palettes and 44-cell maps written')
    # A video crop supplies color, never replacement animation geometry.
    from repair_color_silhouettes import main as repair_silhouettes
    repair_silhouettes()

if __name__=='__main__':main()
