"""自機と大きな録画由来自弾を、静的4bpp OBJ 16KiBへ詰める。"""
import json
import struct
from PIL import Image
from build_ground import GAME

PLAYERS=[9,*range(15,31)]
SIZES={1:(1,1),2:(2,2),3:(4,4),4:(6,4),5:(8,6),6:(10,6),7:(12,8),8:(16,12),9:(24,16),10:(32,20),11:(40,24)}
SIZES.update({s:(56,32) for s in range(12,17)})

def bullet_image(size):
    image=Image.open(GAME/'assets/recorded_effects/bullet.png')
    return image.resize(SIZES[size],Image.Resampling.NEAREST)

def build():
    assets=GAME/'assets';vram=bytearray((assets/'ppu.bin').read_bytes());vram[0xc000:]=bytes(0x4000)
    palette=json.loads((assets/'obj_color/palette.json').read_text())['rgb5']
    shot_palette=json.loads((assets/'recorded_effects/bullet_palette.json').read_text())['rgb5']
    occupied=set();cached={};player_tiles=[0]*264;records=bytearray();pointers=[];layouts={}
    def base(slot):return (slot//64)*256+(slot%8)*2+((slot%64)//8)*32
    def encode(image,tile):
        for ty in range(image.height//8):
            for tx in range(image.width//8):
                raw=bytearray(32)
                for y in range(8):
                    for p in range(4):
                        raw[(p//2)*16+y*2+(p&1)]=sum(((image.getpixel((tx*8+x,ty*8+y))>>p)&1)<<(7-x) for x in range(8))
                address=0xc000+(tile+ty*16+tx)*32
                assert address+32<=65536,'OBJ atlas overflow'
                vram[address:address+32]=raw
    def allocate(image,large=False):
        key=(image.size,image.tobytes())
        if key in cached:return cached[key]
        offsets=(0,1,8,9) if large else (0,)
        candidates=(s for s in range(128) if not large or (s%8<7 and s%64<56))
        slot=next((s for s in candidates if all(s+d<128 and s+d not in occupied for d in offsets)),None)
        assert slot is not None,'OBJ atlas exceeds 16KiB'
        occupied.update(slot+d for d in offsets);tile=base(slot);encode(image,tile);cached[key]=tile
        return tile
    # 32x32矩形を先に確保。40x24は大一枚＋小二枚でVRAMとOBJ枠を節約。
    for size in (12,10,11,9,8,7,6,5,4,3,2,1):
        im=bullet_image(size);step=32 if size in (12,10) else 16;layout=[]
        parts=[(x,y,step) for y in range(0,im.height,step) for x in range(0,im.width,step)]
        if size==11:parts=[(0,0,32),(32,0,16),(32,16,16)]
        for x,y,step in parts:
            part=Image.new('P',(step,step));part.paste(im.crop((x,y,min(x+step,im.width),min(y+step,im.height))),(0,0))
            layout.append((x,y,allocate(part,step==32),step))
        layouts[size]=layout
    for asset in PLAYERS:
        im=Image.open(assets/'obj_color'/f'{asset:02d}.png')
        assert im.mode=='P' and im.size==(32,48) and im.info.get('transparency')==0
        assert im.getextrema()[1]<16,'player exceeds 16 colors'
        rgb8=[tuple(c*8+(c>>2) for c in color) for color in palette]
        png_palette=im.getpalette()
        assert all(tuple(png_palette[c*3:c*3+3])==rgb8[c] for _,c in im.getcolors() if c),'player palette differs'
        for y in range(3):
            for x in range(2):player_tiles[asset*6+y*2+x]=allocate(im.crop((x*16,y*16,x*16+16,y*16+16)))
    for size in range(17):
        pointers.append(len(records))
        if not size:records+=bytes(4);continue
        w,h=SIZES[size];layout=layouts[min(size,12)];records+=struct.pack('<4B',w,h,len(layout),0)
        for x,y,tile,step in layout:records+=struct.pack('<BBH',x,y,tile|(0x8000 if step==32 else 0))
    (assets/'obj_tiles.bin').write_bytes(struct.pack('<264H',*player_tiles))
    (assets/'obj_bullets.bin').write_bytes(struct.pack('<17H',*pointers)+records)
    palettes=palette+shot_palette
    assert all(len(p)==3 and all(0<=c<32 for c in p) for p in palettes)
    (assets/'obj_palette.bin').write_bytes(struct.pack('<32H',*[r|(g<<5)|(b<<10) for r,g,b in palettes]))
    (assets/'ppu.bin').write_bytes(vram)
    (assets/'recorded_effects/bullet_layout.json').write_text(json.dumps({'sizes':SIZES,'occupied16pxSlots':len(occupied),
        'vramBytes':len(occupied)*128,'maxBulletObjects':max(map(len,layouts.values()))},indent=2)+'\n')
    print(f'OBJ atlas: {len(occupied)}/128 slots ({len(occupied)*128} bytes); bullet max {max(map(len,layouts.values()))} OBJ')

if __name__=='__main__':build()
