"""原画を保護し、横縮小表の全画素・配置・ROM一致を独立に検査する。"""
import hashlib
import json
from pathlib import Path
import struct
from PIL import Image
from build_game import BUILD, GAME


def verify():
    images=[]
    for asset in range(44):
        color=GAME/'assets/bg_color'/f'{asset:02d}.png'
        image=Image.open(color if color.exists() else GAME/'assets'/f'{asset:02d}.png')
        images.append(image if color.exists() else image.convert('RGBA'))
    def source_index(image,x,y):
        value=image.getpixel((x,y))
        if isinstance(value,int):
            assert 0 <= value <= 3
            return value
        r,g,b,alpha=value
        return 0 if alpha<128 else 3 if r+g+b>=384 else 1
    banks={b:(GAME/'assets'/f'bank{b:02x}.bin').read_bytes() for b in range(0x44,0x5a)}
    protected={b:[] for b in banks}
    source_pixels=0
    for asset,image in enumerate(images):
        bank=0x44+asset//2;base=(asset&1)*32768
        protected[bank].append((base,base+image.height*256))
        for y in range(image.height):
            row=[]
            for x in range(image.width):
                expected=source_index(image,x,y)
                assert banks[bank][base+y*256+x]==expected,(asset,x,y)
                row.append(expected);source_pixels+=1
            for x in range(0,image.width,4):
                values=(row[x:x+4]+[0]*4)[:4]
                assert banks[bank][base+y*256+128+x//4]==sum(v<<(2*i) for i,v in enumerate(values))
                assert banks[bank][base+y*256+160+x//4]==sum(v<<(2*(3-i)) for i,v in enumerate(values))
    table=(GAME/'assets/scaled5f.bin').read_bytes()
    mode=json.loads((BUILD/'build_mode.json').read_text())
    limits={int(a):n for a,n in mode['scaledAssetWidths'].items()}
    used={b:[] for b in banks};scales=0;pixels=0;size=0
    scale=(GAME/'assets/scale5e.bin').read_bytes()
    margin_rows=0
    if mode.get('rowMargins'):
        for slot,asset,lo,hi in ((0,0,32,128),(1,1,32,128),(2,4,32,128),(3,36,32,52)):
            image=images[asset];bank=0x44+asset//2
            for width in range(256):
                offset=struct.unpack_from('<H',scale,0xb058+slot*512+width*2)[0]
                assert bool(offset)==(lo<=width<=hi),(asset,width)
                if not offset:
                    continue
                end=offset+image.height*2
                assert end<=65536
                assert all(end<=left or offset>=right for left,right in protected[bank])
                assert all(end<=left or offset>=right for left,right in used[bank])
                used[bank].append((offset,end))
                du=image.width*256//width
                for y in range(image.height):
                    nonzero=[x for x in range(width) if source_index(image,(x*du)>>8,y)!=0]
                    expected=bytes((nonzero[0],nonzero[-1]+1)) if nonzero else bytes(2)
                    assert banks[bank][offset+y*2:offset+y*2+2]==expected,(asset,width,y)
                    margin_rows+=1
    for asset,image in enumerate(images):
        for width in range(256):
            bank,stride,offset=struct.unpack_from('<BBH',table,asset*1024+width*4)
            assert bool(bank)==(1 <= width <= limits.get(asset,0)),(asset,width,bank)
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
                    expected=source_index(image,(x*du)>>8,y)
                    assert value==expected,(asset,width,x,y)
                    pixels+=1
    rom=(BUILD/'MonoSHFX2_v001.sfc').read_bytes()
    assert rom[0x1e0000:0x1f0000]==scale
    for bank,data in banks.items():assert rom[(bank-0x40)*65536:(bank-0x3f)*65536]==data
    assert rom[0x1f0000:0x200000]==table
    result={'romSha256':hashlib.sha256(rom).hexdigest(),'sourcePixels':source_pixels,
            'scaledAssetWidths':limits,'scaledWidths':scales,'scaledPixels':pixels,'packedBytes':size,'romBytes':len(rom),
            'transparentMarginRows':margin_rows,'transparentMarginBytes':margin_rows*2,
            'sourceProtected':True,'allocationsDoNotOverlap':True,'romMatchesAssets':True}
    (BUILD/'scaled_assets_verified.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
    return result


if __name__=='__main__':verify()
