"""元の白黒原画と、カラー原画・ROMへ詰めた画素の形を独立に比較する。"""
import hashlib
import json
import struct
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'game/v001/assets'
PACK=ROOT/'build/game_v001/assets4'
DEST=ROOT/'game/v001/results/legacy_shapes_20261008'

def main():
    mode=json.loads((PACK.parent/'build_mode.json').read_text())
    assert mode['bitsPerPixel']==4 and mode['color']
    rom=(PACK.parent/'MonoSHFX2_v001.sfc').read_bytes()
    policy=json.loads((ASSETS/'color4/source.json').read_text())['shapePolicy']
    palette=struct.unpack('<16H',(PACK/'palette4.bin').read_bytes())
    rgb=np.array([[(v>>s&31)*255//31 for s in (0,5,10)] for v in palette])
    records=[];cards=[]
    for i in policy['assets']:
        path=ASSETS/f'{i:02d}.png';old=np.array(Image.open(path).convert('RGBA'))
        color=np.array(Image.open(ASSETS/f'color4/{i:02d}.png').convert('RGBA'))
        assert color.shape==old.shape,f'{i}: dimensions changed'
        alpha=old[:,:,3]>=128
        binary=(old[:,:,:3].astype(int).sum(2)>=384)&alpha
        restored=(color[:,:,:3].astype(int).sum(2)>=384)&(color[:,:,3]>=128)
        bank=0x44+i//2;start=(bank-0x40)*65536
        raw_bytes=rom[start:start+65536]
        assert raw_bytes==(PACK/f'bank{bank:02x}.bin').read_bytes(),f'{i}: linked ROM bank differs'
        raw=np.frombuffer(raw_bytes,dtype=np.uint8)
        packed=np.stack([raw[(i&1)*32768+y*256:(i&1)*32768+y*256+old.shape[1]] for y in range(old.shape[0])])
        packed_binary=(rgb[packed].sum(2)>=384)&(packed!=0)
        gray=np.array(Image.fromarray(color).convert('L'))>=128
        packed_gray=np.array(Image.fromarray(rgb[packed].astype(np.uint8)).convert('L'))>=128
        changes={'alpha':int((old[:,:,3]!=color[:,:,3]).sum()),
                 'twoTone':int((binary!=restored).sum()),
                 'packedAlpha':int((alpha!=(packed!=0)).sum()),
                 'packedTwoTone':int((binary!=packed_binary).sum()),
                 'grayscaleTwoTone':int((binary!=(gray&alpha)).sum()),
                 'packedGrayscaleTwoTone':int((binary!=(packed_gray&alpha)).sum())}
        assert not any(changes.values()),f'{i}: legacy image differs: {changes}'
        records.append({'asset':i,'size':[old.shape[1],old.shape[0]],'referenceSha256':hashlib.sha256(path.read_bytes()).hexdigest(),**changes})
        mono=color.copy();mono[:,:,:3]=np.where(restored[:,:,None],255,0)
        cards.append((i,Image.fromarray(old),Image.fromarray(color),Image.fromarray(mono)))
    DEST.mkdir(parents=True,exist_ok=True)
    panel=Image.new('RGB',(1280,((len(cards)+2)//3)*156),(65,65,65));draw=ImageDraw.Draw(panel)
    for n,(i,*images) in enumerate(cards):
        x=(n%3)*426;y=(n//3)*156
        draw.text((x+4,y+3),f'{i:02d} / reference | color | restored mono',fill='white')
        for col,im in enumerate(images):
            im.thumbnail((130,128),Image.Resampling.NEAREST)
            panel.paste(im,(x+col*140+4,y+23),im)
    panel.save(DEST/'comparison.png')
    summary={'romSha256':hashlib.sha256(rom).hexdigest(),
             'assetsVerified':len(records),'changedAlphaPixels':0,'changedTwoTonePixels':0,'assets':records}
    (DEST/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(f'Legacy shapes: {len(records)} assets, alpha/two-tone/packed pixels all identical')

if __name__=='__main__':main()
