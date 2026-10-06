"""原画を保護し、横縮小表の全画素・配置・ROM一致を独立に検査する。"""
import hashlib
import json
from pathlib import Path
import struct
from PIL import Image
from build_game import BUILD, GAME


def verify():
    images=[Image.open(GAME/'assets'/f'{a:02d}.png').convert('RGBA') for a in range(44)]
    banks={b:(GAME/'assets'/f'bank{b:02x}.bin').read_bytes() for b in range(0x44,0x5a)}
    protected={b:[] for b in banks}
    source_pixels=0
    for asset,image in enumerate(images):
        bank=0x44+asset//2;base=(asset&1)*32768
        protected[bank].append((base,base+image.height*256))
        for y in range(image.height):
            row=[]
            for x in range(image.width):
                r,g,b,alpha=image.getpixel((x,y))
                expected=0 if alpha<128 else 3 if r+g+b>=384 else 1
                assert banks[bank][base+y*256+x]==expected,(asset,x,y)
                row.append(expected);source_pixels+=1
            for x in range(0,image.width,4):
                values=(row[x:x+4]+[0]*4)[:4]
                assert banks[bank][base+y*256+128+x//4]==sum(v<<(2*i) for i,v in enumerate(values))
                assert banks[bank][base+y*256+160+x//4]==sum(v<<(2*(3-i)) for i,v in enumerate(values))
    table=(GAME/'assets/scaled5f.bin').read_bytes()
    used={b:[] for b in banks};scales=0;pixels=0;size=0
    for asset,image in enumerate(images):
        for width in range(256):
            bank,stride,offset=struct.unpack_from('<BBH',table,asset*1024+width*4)
            if not bank:
                assert stride==offset==0
                continue
            assert width and stride==(width+3)//4
            end=offset+stride*image.height;assert end<=65536
            assert all(end<=left or offset>=right for left,right in protected[bank])
            assert all(end<=left or offset>=right for left,right in used[bank])
            used[bank].append((offset,end));scales+=1;size+=end-offset
            du=image.width*256//width
            for y in range(image.height):
                for x in range(width):
                    value=(banks[bank][offset+y*stride+x//4]>>(2*(x%4)))&3
                    r,g,b,alpha=image.getpixel(((x*du)>>8,y))
                    expected=0 if alpha<128 else 3 if r+g+b>=384 else 1
                    assert value==expected,(asset,width,x,y)
                    pixels+=1
    rom=(BUILD/'MonoSHFX2_v001.sfc').read_bytes()
    for bank,data in banks.items():assert rom[(bank-0x40)*65536:(bank-0x3f)*65536]==data
    assert rom[0x1f0000:0x200000]==table
    result={'romSha256':hashlib.sha256(rom).hexdigest(),'sourcePixels':source_pixels,
            'scaledWidths':scales,'scaledPixels':pixels,'packedBytes':size,'romBytes':len(rom),
            'sourceProtected':True,'allocationsDoNotOverlap':True,'romMatchesAssets':True}
    (BUILD/'scaled_assets_verified.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
    return result


if __name__=='__main__':verify()
