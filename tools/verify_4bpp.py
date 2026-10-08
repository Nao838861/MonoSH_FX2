"""独立した画素合成でGSUの4面、左右分割、VRAM世代を全画素照合する。"""
import json
import struct
import sys
import numpy as np
from PIL import Image
from build_game import GAME, BUILD
def prepare_draw(raw):
    center,bottom,w,h,asset,flags,_,_=raw
    if not w or not h:return None
    left=center-w//2;top=bottom-h-20
    width=min(256,left+w)-max(0,left);height=min(192,top+h)-max(0,top)
    if width<=0 or height<=0:return None
    color=json.loads((BUILD/'build_mode.json').read_text()).get('color',False)
    source=GAME/'assets'/('color4' if color else '')/f'{asset:02d}.png'
    aw,ah=Image.open(source).size
    du=aw*256//w;dv=ah*256//h
    u=max(0,-left)*du;v=max(0,-top)*dv
    if flags&16:u=aw*256-1-u;du=-du
    if flags&32:v=ah*256-1-v;dv=-dv
    bank=0x44+asset//2;base=0x600 if asset==43 else 32768 if asset&1 else 0
    if color:
        bank,_,base=struct.unpack_from('<BBH',(BUILD/'assets4/bullet_variants.bin').read_bytes(),asset*12+(flags&3)*4)
    v+=base
    return max(0,left),max(0,top),du,dv,0,height,v,width,u,bank

def encode(pix):
    tiles=pix.reshape(24,8,32,8).transpose(2,0,1,3).reshape(768,8,8)
    out=np.zeros((768,32),dtype=np.uint8)
    for p in range(4):
        values=(((tiles>>p)&1)*np.array([128,64,32,16,8,4,2,1],dtype=np.uint8)).sum(axis=2)
        out[:,(p//2)*16+(p%2)+np.arange(8)*2]=values
    return out.tobytes()

def verify_player(directory,prefix,meta,vram):
    if not (directory/f'{prefix}_oam.bin').exists():return
    oam=(directory/f'{prefix}_oam.bin').read_bytes()
    built=(directory/f'{prefix}_obj.bin').read_bytes()
    assert oam[:24]==built[:24] and oam[512:520]==built[128:136],f'{prefix}: OAM generation differs'
    cgram=(directory/f'{prefix}_cgram.bin').read_bytes()
    assert cgram[32:64]==(BUILD/'assets4/palette4.bin').read_bytes(),f'{prefix}: object palette changed'
    assert cgram[256:288]==(GAME/'assets/obj_palette.bin').read_bytes()[:32],f'{prefix}: player palette changed'
    source=meta['playerObjSource']
    if source:
        rom=(BUILD/'MonoSHFX2_v001.sfc').read_bytes()
        assert vram[0xc800:0xcb80]==rom[0x1f0000+source:0x1f0000+source+896],f'{prefix}: player CHR differs'
    palette=struct.unpack('<16H',cgram[256:288])
    rgb=np.array([[(v>>s&31)*8+((v>>s&31)>>2) for s in (0,5,10)] for v in palette],dtype=np.uint8)
    actual=np.zeros((224,256,4),dtype=np.uint8)
    for n in range(6):
        xx,yy,tile,attr=oam[n*4:n*4+4]
        if oam[512+n//4]>>(n%4*2)&1:xx-=256
        if yy>=240:yy-=256
        tile|=(attr&1)<<8
        pixels=np.zeros((16,16),dtype=np.uint8)
        for ty in range(2):
            for tx in range(2):
                raw=vram[0xc000+(tile+ty*16+tx)*32:0xc000+(tile+ty*16+tx+1)*32]
                for y in range(8):
                    for x in range(8):
                        pixels[ty*8+y,tx*8+x]=sum(((raw[(p//2)*16+y*2+(p&1)]>>(7-x))&1)<<p for p in range(4))
        if attr&64:pixels=pixels[:,::-1]
        if attr&128:pixels=pixels[::-1]
        for y in range(16):
            for x in range(16):
                c=pixels[y,x]
                if c and 0<=xx+x<256 and 0<=yy+y<224:
                    actual[yy+y,xx+x,:3]=rgb[c];actual[yy+y,xx+x,3]=255
    expected=np.zeros_like(actual);inp=meta.get('playerInput')
    if inp and inp['visible']:
        image=np.array(Image.open(GAME/f'assets/obj_color/{inp["asset"]:02d}.png').convert('RGBA'))
        if inp['flags']&16:image=image[:,::-1]
        if inp['flags']&32:image=image[::-1]
        left=inp['center']-16;top=inp['bottom']-56
        x0=max(0,left);x1=min(256,left+32);y0=max(0,top);y1=min(224,top+48)
        if x0<x1 and y0<y1:expected[y0:y1,x0:x1]=image[y0-top:y1-top,x0-left:x1-left]
    if not np.array_equal(expected,actual):
        Image.fromarray(actual).save(directory/f'{prefix}_obj_actual.png')
        Image.fromarray(expected).save(directory/f'{prefix}_obj_expected.png')
        raise AssertionError(f'{prefix}: independently composed player differs')

def verify(directory):
    assets=BUILD/'assets4'
    banks={i:np.frombuffer((assets/f'bank{i:02x}.bin').read_bytes(),dtype=np.uint8) for i in range(0x44,0x5a)}
    backgrounds=np.frombuffer((assets/'background4.bin').read_bytes(),dtype=np.uint8)
    initial_vram=(assets/'ppu.bin').read_bytes()
    files=sorted(directory.glob('frame*_fb.bin'));assert files,'no captured 4bpp framebuffer'
    player_cases=set();bullet_ages=set();asset_cases=set();effect_phases=set()
    for path in files:
        prefix=path.name[:-7]
        packet=(directory/f'{prefix}_packet.bin').read_bytes()
        bg=(directory/f'{prefix}_background.bin').read_bytes()
        pix=np.zeros((192,256),dtype=np.uint8)
        for i in range(2):
            x,top,h,base=struct.unpack_from('<4H',bg,i*8)
            for dy in range(h):
                yy=top+dy
                if yy>=192:continue
                row=backgrounds[base+dy*512+(np.arange(256)+x)%512]
                pix[yy,row!=0]=row[row!=0]
        for i in range(struct.unpack_from('<H',packet)[0]):
            raw=struct.unpack_from('<hh6B',packet,32+i*10)
            if directory.name=='four_assets':asset_cases.add(raw[:6])
            command=prepare_draw(raw)
            if command is None:continue
            left,top,du,dv,_,h,v,w,u,bank=command
            xx=(((u+np.arange(w)*du)&65535)>>8)
            yy=((v+np.arange(h)*dv)&65535)&0xff00
            colors=banks[bank][yy[:,None]+xx[None,:]]
            target=pix[top:top+h,left:left+w]
            target[colors!=0]=colors[colors!=0]
        expected=encode(pix);actual=path.read_bytes()
        if expected!=actual:
            palette=struct.unpack('<16H',(assets/'palette4.bin').read_bytes())
            rgb=[tuple((v>>p&31)*255//31 for p in (0,5,10)) for v in palette]
            Image.fromarray(np.array(rgb,dtype=np.uint8)[pix]).save(directory/f'{prefix}_expected.png')
            raise AssertionError(f'{prefix}: {sum(x!=y for x,y in zip(actual,expected))} framebuffer bytes differ')
        meta=json.loads((directory/f'{prefix}_meta.json').read_text())
        phase=meta.get('effectPhase')
        if directory.name in ('four_effects','four_stage_effects'):assert phase is not None,f'{prefix}: explosion fixture did not reach renderer'
        if phase is not None:
            effect_phases.add(phase)
            draws=[struct.unpack_from('<hh6B',packet,32+i*10) for i in range(struct.unpack_from('<H',packet)[0])]
            expected_asset=(5,39,40,41,40,39)[phase]
            for center in ((128,) if directory.name=='four_stage_effects' else (64,192)):
                assert any(r[0]==center and r[4]==expected_asset for r in draws),f'{prefix}: explosion sequence differs at {center}'
        inp=meta.get('playerInput')
        if inp:player_cases.add((inp['asset'],inp['flags'],inp['center'],inp['bottom']))
        ages=meta.get('bulletAges')
        if ages:
            normal=[struct.unpack_from('<hh6B',packet,32+i*10) for i in range(struct.unpack_from('<H',packet)[0])]
            boss_shots=[r for r in normal if r[4]==31]
            phase=ages[0]%32;boss_hue=0 if phase<16 else 2 if phase<24 else 1
            assert len(boss_shots)==1 and boss_shots[0][5]==boss_hue,f'{prefix}: boss shot hue differs'
            normal=[r for r in normal if r[4] in (6,7,8,37)]
            assert len(normal)==3,f'{prefix}: injected bullets did not reach the renderer'
            for i,age in enumerate(ages):
                draw=next(r for r in normal if r[0]==64+i*64)
                phase=age//4
                asset=[6,7,8,37,37,8,7,6,6,7,8,37,37,8,7,6][phase]
                flip=[0,0,0,0,32,32,32,32,48,48,48,48,16,16,16,16][phase]
                hue=0 if age%32<16 else 2 if age%32<24 else 1
                assert draw[4]==asset and draw[5]==flip|hue,f'{prefix}: bullet phase/color differs'
                bullet_ages.add(age)
        vram=(directory/f'{prefix}_vram.bin').read_bytes();start=meta['page']*2
        assert vram[start:start+24576]==actual,f'{prefix}: visible VRAM has a mixed generation'
        assert vram[0xd000:]==initial_vram[0xd000:],f'{prefix}: ground CHR/map changed'
        verify_player(directory,prefix,meta,vram)
    if directory.name=='four_players':assert len(player_cases)==408,f'player coverage: {len(player_cases)}/408'
    if directory.name=='four_assets':assert len(asset_cases)==880,f'asset coverage: {len(asset_cases)}/880'
    if directory.name=='four_bullets':assert bullet_ages==set(range(64)),f'bullet ages: {len(bullet_ages)}/64'
    if directory.name in ('four_effects','four_stage_effects'):assert effect_phases==set(range(6)),f'explosion phases: {effect_phases}'
    print(f'{directory.name}: {len(files)} frames, all 49,152 indexed pixels and 24KiB visible VRAM match')

if __name__=='__main__':
    for name in sys.argv[1:] or ['play']:verify(BUILD/f'four_{name}')
