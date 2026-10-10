"""遠景を非表示CHR行へ移し、近景を8px OBJと48pxのソフト描画で合成する。"""
import json
import struct
import numpy as np
from sa1_native_far import canonical, decode, encode


def build(ppu, raw, dest):
    far_addresses = list(range(0, 1024, 32)) + list(range(0x6000, 0x6400, 32))
    far_pool = {}
    for row in range(2):
        for col in range(64):
            address = 0xc000 + (col//32)*0x800 + (24+row)*64 + (col%32)*2
            entry = struct.unpack_from('<H', ppu, address)[0]
            pixels = decode(ppu[0xc000+(entry&1023)*32:0xc000+(entry&1023)*32+32], 4)
            if entry&0x4000: pixels = pixels[:, ::-1]
            if entry&0x8000: pixels = pixels[::-1]
            key, flip = canonical(pixels)
            if key not in far_pool:
                far_pool[key] = far_addresses[len(far_pool)]
                target = far_pool[key]
                ppu[target:target+32] = encode(np.frombuffer(key, np.uint8).reshape(8,8), 4)
            struct.pack_into('<H', ppu, address, far_pool[key]//32 | 0x0400 | flip)
    assert len(far_pool)==64
    # 二つのbitmapの先頭8行は表示窓外なので、前景DMAから除外する。
    near_addresses = list(range(0xc680, 0xc800, 32)) + list(range(0xcb80, 0xce00, 32))
    near_addresses += list(range(0xce80, 0xd000, 32)) + list(range(0xe900, 0xf000, 32))
    near = np.zeros((16,512), np.uint8)
    near[:9] = np.frombuffer(raw[0x8000:0x8000+9*512], np.uint8).reshape(9,512)
    pool = {}; table = bytearray()
    for row in range(2):
        for col in range(64):
            pixels = near[row*8:row*8+8, col*8:col*8+8]
            key, flip = canonical(pixels)
            if key not in pool:
                pool[key] = near_addresses[len(pool)]
                target = pool[key]
                ppu[target:target+32] = encode(np.frombuffer(key,np.uint8).reshape(8,8),4)
            target=pool[key]
            tile=(target-0xc000)//32
            entry=(tile&255)|((tile>>8)&1)<<8|0x2e00|flip
            table += struct.pack('<H',entry)
    assert len(pool)==62
    (dest/'native_near_table.bin').write_bytes(table)
    oam=bytearray()
    for scroll in range(512):
        low=bytearray();high=bytearray(32);struct.pack_into('<H',high,0,0x0aaa)
        for row in range(2):
            for col in range(33):
                if 14<=col<20:continue
                x=col*8-(scroll&7);y=95+row*8
                if x>=256:y=240
                index=6+len(low)//4
                if x<0:high[index//4]|=1<<(index%4*2)
                entry=struct.unpack_from('<H',table,row*128+((scroll//8+col)&63)*2)[0]
                low+=bytes((x&255,y))+struct.pack('<H',entry)
        assert len(low)==216
        oam+=low+high+bytes(8)
    assert len(oam)==0x20000
    (dest/'native_near_oam.bin').write_bytes(oam)
    report={'farChrAddresses':list(far_pool.values()),'nearChrAddresses':list(pool.values()),
            'nearTiles':len(pool),'nearObjects':54,'softwareHolePixels':48,
            'objTilesPerLineWithPlayer':31,'objObjectsPerLineWithPlayer':29}
    (dest/'native_near_packing.json').write_text(json.dumps(report,indent=2)+'\n')
    return ppu


def transform(name, text):
    if name=='cpu':
        text=text.replace('  lda #$60\n  sta $210b','  lda #0\n  sta $210b')
        text=text.replace('  lda #$63 ', '  lda #$03 ')
        text=text.replace('  bne fx_palette\n', '''  bne fx_palette
  lda #$f0
  sta $2121
  ldx #0
near_obj_palette:
  lda f:fx_palette_data,x
  sta $2122
  inx
  cpx #32
  bne near_obj_palette
''')
    elif name=='renderer':
        text='.setcpu "65816"\n.import sa1_near_patch: far\n'+text
        text=text.replace('background:\n  rtl', 'background:\n  jsl sa1_near_patch\n  rtl')
        text=text.replace('  jsl sa1_background_cache\n', '')
    elif name=='dirty':
        text='.setcpu "65816"\n.import sa1_near_patch_bounds: far\n'+text
        text=text.replace('dirty_bg:\n  jmp dirty_save', 'dirty_bg:\n  jsl sa1_near_patch_bounds\n  jmp dirty_save')
    elif name=='objects':
        text='.import pipe_near_select, pipe_near_present\n'+text
        text=text.replace('oam4:\n', 'oam4:\n  jsr pipe_near_select\n')
        text=text.replace('  lda pipe_obj_pointer\n  clc\n  adc #128','  lda pipe_near_present\n  clc\n  adc #256')
        text=text.replace('  lda pipe_obj_pointer\n', '  lda pipe_near_present\n')
        text=text.replace('  lda #24\n  sta f:$004305','  lda #256\n  sta f:$004305')
        text=text.replace('  lda #8\n  sta f:$004305','  lda #32\n  sta f:$004305')
    return text


def verify(oam_path, vram, source, scroll, ground, software, sprites):
    oam=oam_path.read_bytes();canvas=np.zeros((192,256),np.uint8)
    for index in range(6,60):
        x,y,tile,attr=oam[index*4:index*4+4]
        high=(oam[512+index//4]>>(index%4*2))&3
        assert high&2==0,'near OBJ size changed'
        assert attr&0x3e==0x2e,'near OBJ palette/priority changed'
        x|=(high&1)<<8
        if x>=256:x-=512
        y-=13
        address=0xc000+tile*32+(0x2000 if attr&1 else 0)
        pixels=decode(vram[address:address+32],4)
        if attr&0x40:pixels=pixels[:,::-1]
        if attr&0x80:pixels=pixels[::-1]
        x0=max(0,x);x1=min(256,x+8);y0=max(0,y);y1=min(192,y+8)
        if x0<x1 and y0<y1:
            a=pixels[y0-y:y1-y,x0-x:x1-x];b=canvas[y0:y1,x0:x1];b[a!=0]=a[a!=0]
    expected=np.zeros_like(canvas);top=82+ground
    layer=np.frombuffer(source[0x8000:0x8000+9*512],np.uint8).reshape(9,512)[:,(np.arange(256)+scroll)&511]
    y0=max(0,top);y1=min(192,top+9)
    if y0<y1:expected[y0:y1]=layer[y0-top:y1-top]
    combined=canvas.copy();combined[software!=0]=software[software!=0]
    expected[sprites!=0]=sprites[sprites!=0]
    assert np.array_equal(combined,expected),f'{oam_path.name}: near OBJ/software composite differs ({np.count_nonzero(combined!=expected)} pixels)'
    for y in range(224):
        visible=[]
        for i in range(64):
            oy=oam[i*4+1];ox=oam[i*4]|((oam[512+i//4]>>(i%4*2)&1)<<8)
            size=16 if (oam[512+i//4]>>(i%4*2)&2) else 8
            if oy<=y<oy+size and (ox<256 or ox>=512-size):visible.append(size)
        assert len(visible)<=32 and sum(s//8 for s in visible)<=34,'OBJ scanline limit exceeded'
