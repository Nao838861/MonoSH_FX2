"""固定した元ソースから、単独起動するSNES FX2移植ROMを組み立てる。"""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
from PIL import Image
from smooth_depth import transform as smooth_depth_tables, open_enemy_sizes

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / 'game/v001'
BUILD = ROOT / 'build/game_v001'
UP = GAME / 'upstream'
CC65 = Path(shutil.which('cc65')).resolve().parent
NES = Path(os.environ.get('MONOSH_NES_ROOT','D:/HomeBrew/MonoSH'))

def run(args):
    result = subprocess.run([str(x) for x in args], cwd=BUILD, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if result.returncode:
        print(result.stdout, result.stderr); raise SystemExit(result.returncode)
    if result.stderr: print(result.stderr.strip())

def array(name, data, ctype='unsigned char'):
    return 'const '+ctype+' '+name+'['+str(len(data))+'] = {\n'+''.join(
        ','.join(map(str,data[i:i+32]))+',\n' for i in range(0,len(data),32))+'};\n'

def export_assets():
    dest = GAME/'assets'; dest.mkdir(exist_ok=True)
    filenames = {
      0:'Bush0/Bush0_00.png',1:'Bush1/Bush1_00.png',2:'FlyStone/FlyStone_00.png',
      3:'Em0/Em0_00.png',4:'Tree0/Tree0_00.png',5:'Bom0/Bom0_base_0.png',
      6:'EnemyBullet0/EnemyBullet0_base_0.png',7:'EnemyBullet0/EnemyBullet0_base_1.png',
      8:'EnemyBullet0/EnemyBullet0_base_2.png',11:'Em1/clo/c00.png',
      12:'Em1/open/o10.png',13:'BossBody/BossBody_Base.png',14:'BossFace/BossFace_Base.png',
      31:'BossBullet/BossBullet_Base.png',37:'EnemyBullet0/EnemyBullet0_base_3.png',
      39:'Bom0/Bom0_base_1.png',40:'Bom0/Bom0_base_2.png',41:'Bom0/Bom0_base_3.png',
      42:'Stage1/Stage1.png'}
    # ファイル名は原本のopen画像から、各段階の最大原画を選ぶ。
    opens = sorted((NES/'png/Em1/open').glob('*.png'))
    for i in range(5):
        candidates = [NES/'png/Em1'/f'Em1_{i+1:02d}.png']
        if not candidates: raise RuntimeError(f'missing EM1 open pose {i+1}: {opens}')
        filenames[32+i] = str(max(candidates, key=lambda p: Image.open(p).width)).replace(str(NES/'png')+'\\','')
    imgs = {}
    manifest = {}
    for index, name in filenames.items():
        p = Path(name)
        if not p.is_absolute(): p = NES/'png'/name
        if not p.exists() and index == 42:
            p = next((NES/'png/Stage1').glob('*.png'))
        im = Image.open(p).convert('RGBA')
        # geometry表の原画と同様に、透明余白を除く。ただしEm0はsource canvasを保存。
        if index != 3 and im.getbbox(): im = im.crop(im.getbbox())
        if im.width > 128 or im.height > 128:
            im.thumbnail((128,128),Image.Resampling.NEAREST)
        pix = [[0 if a < 128 else (3 if r+g+b >= 384 else 1)
                for r,g,b,a in [im.getpixel((x,y)) for x in range(im.width)]]
               for y in range(im.height)]
        imgs[index] = pix
        manifest[str(index)] = {'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                                'width':im.width,'height':im.height}
    # 自機はNESのCHRとOAM組立規則から直接生成（32x48）。
    poses = [0,10,11,12,13,14,15,16,4,5,6,7,8,9,1,2,3]
    bases = [1,0,8,0x10,0x18,0x80,0x88,0x90,0x11,0x71,0xd1,0x19,0x59,0x99,9,0x81,0x89]
    ids = [9,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30]
    for pose,base,index in zip(poses,bases,ids):
        data = (NES/'res'/('sprite2.chr' if pose>=10 else 'sprite.chr')).read_bytes()
        pix = [[0]*32 for _ in range(48)]
        for yy in range(48):
            for xx in range(32):
                tile = ((base+(yy//16)*0x20+(xx//8)*2)&0xfe)+(yy%16)//8
                o = tile*16+(yy%8); bit = 7-(xx%8)
                c = ((data[o]>>bit)&1) | (((data[o+8]>>bit)&1)<<1)
                pix[yy][xx] = [0,1,3,1][c]
        if pose in (6,7,8):
            shift = 8 if pose==6 else 16
            pix = [[0]*32 for _ in range(shift)]+pix[:32]+[[0]*32 for _ in range(16-shift)]
        imgs[index] = pix
    data = (NES/'res/sprite.chr').read_bytes()
    shadow = [[0]*32 for _ in range(8)]
    for col,(tile,flip) in enumerate([(0x6e,1),(0x6c,1),(0x6c,0),(0x6e,0)]):
        for y in range(8):
            for x in range(8):
                bit= x if flip else 7-x
                if ((data[tile*16+y] | data[tile*16+y+8])>>bit)&1: shadow[y][col*8+x]=1
    imgs[38] = shadow
    imgs[10] = [[3 if abs(x-7)+abs(y-7)<=5 else 0 for x in range(16)] for y in range(16)]
    imgs[43] = [[0]] # pair padding
    for i in range(44):
        if i not in imgs: raise RuntimeError(f'missing asset {i}')
        pix = imgs[i]; h=len(pix); w=len(pix[0]); assert h<=128 and w<=128, (i,w,h)
        im = Image.new('RGBA',(w,h)); im.putdata([(255,255,255,255) if c==3 else ((0,0,0,255) if c else (0,0,0,0)) for row in pix for c in row]); im.save(dest/f'{i:02d}.png')
    for bank in range(22):
        raw=bytearray(65536)
        for half in range(2):
            i=bank*2+half
            for y,row in enumerate(imgs[i]): raw[half*32768+y*256:half*32768+y*256+len(row)] = bytes(row)
        (dest/f'bank{0x44+bank:02x}.bin').write_bytes(raw)
    (dest/'sources.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    dims = sorted({len(pix[0]) for pix in imgs.values()} | {len(pix) for pix in imgs.values()})
    out=''
    for dim in dims: out+=array(f'fx_steps_{dim}',[0]+[min(65535,(dim*256)//size) for size in range(1,256)],'unsigned int')
    out+=array('fx_asset_width',[len(imgs[i][0]) for i in range(44)])
    out+=array('fx_asset_height',[len(imgs[i]) for i in range(44)])
    out+=array('fx_asset_bank',[0x44+i//2 for i in range(44)])
    out+='const unsigned int * const fx_du_table[44] = {'+','.join(f'fx_steps_{len(imgs[i][0])}' for i in range(44))+'};\n'
    out+='const unsigned int * const fx_dv_table[44] = {'+','.join(f'fx_steps_{len(imgs[i])}' for i in range(44))+'};\n'
    camera=re.findall(r'\d+', (UP/'monosh_ground_camera_table.inc').read_text())
    out+=array('fx_ground_camera',list(map(int,camera)))
    asm=(UP/'monosh_projection_data.asm').read_text()
    depth=asm.split('_monosh_ground_depth_rows:',1)[1]
    nums=[]
    for line in depth.splitlines():
        if line.strip().startswith('defb'): nums.extend(map(int,line.split('defb')[1].strip().split(',')))
        elif nums and line.strip() and not line.lstrip().startswith(';'): break
    assert len(nums)==5265,len(nums)
    out+=array('fx_ground_depth_rows',nums)
    # 14相の奥行き帯。元の7相と境界位置を補間した中間7相を保存。
    import math
    bands=[]
    for phase in range(14):
        phase0=(phase//2)*2/7; phase1=phase0+2/7
        initial = 1 if math.floor(104.4/6.5+(phase0+phase1)/2 if phase&1 else 104.4/6.5+phase0)%2==0 else 0
        edges=[]
        for stripe in range(3,20):
            def boundary(p):
                return (104.4/(stripe-p)-.5-6)/39*93
            edge=(boundary(phase0)+boundary(phase1))/2 if phase&1 else boundary(phase0)
            if 0<edge<=93: edges.append(math.ceil(edge))
        for y in range(94): bands.append(initial ^ (sum(e<=y for e in edges)%2))
    out+=array('fx_ground_bands',bands)
    out+=array('fx_ground_light',[(12+y*19//94)*1057 for y in range(94)],'unsigned int')
    out+=array('fx_ground_dark',[(12+y*19//94)//3*1057 for y in range(94)],'unsigned int')
    out+=array('fx_ground_steps',[93*256//(94-offset) for offset in range(65)],'unsigned int')
    (GAME/'asset_tables.c').write_text(out)
    source=(UP/'monosh_projection.c').read_text()
    scales=list(map(int,re.search(r'full_scale\[111\] = \{(.*?)\}',source,re.S)[1].replace('\n','').split(',')))
    (dest/'projection_rows.bin').write_bytes(bytes(min(255,(x*scale)>>8) for scale in scales for x in range(256)))
    (dest/'projection_scales.bin').write_bytes(struct.pack('<111H',*scales))
    scrolls=bytearray(); rows=bytearray(); scroll_offsets=[]; row_offsets=[]
    for offset in range(65):
        scroll_offsets.append(len(scrolls)); row_offsets.append(len(rows))
        horizon=111+offset; sky_scroll=7-offset; left=horizon
        while left:
            run=min(127,left);scrolls.extend(struct.pack('<BH',run,sky_scroll&65535));left-=run
        count=94-offset;step=93*256//count
        scrolls.append(count|128)
        for n in range(count):
            source=min(93,(n*step)>>8);rows.append(source)
            scrolls.extend(struct.pack('<h',118+source-(horizon+n)))
        scrolls.append(0)
    (dest/'ground_scroll.bin').write_bytes(scrolls)
    (dest/'ground_rows.bin').write_bytes(rows)
    (dest/'ground_scroll_offsets.bin').write_bytes(struct.pack('<65H',*scroll_offsets))
    (dest/'ground_row_offsets.bin').write_bytes(struct.pack('<65H',*row_offsets))
    export_ppu(dest)
    print(f'{len(dims)} UV step rows, {len(out)} table-source bytes')

def export_ppu(dest):
    vram=bytearray(65536)
    for y in range(32):
        for x in range(32): struct.pack_into('<H',vram,0x8000+2*(y*32+x),(x*24+y if y<24 else 0)|0x2000)
    def encode(row):
        data=bytearray()
        for y in range(8):
            for p in range(2): data.append(sum(((row[y][x]>>p)&1)<<(7-x) for x in range(8)))
        return bytes(data)
    tiles={bytes(16):0}
    for ty in range(32):
        for tx in range(32):
            rows=[]
            for y in range(8):
                yy=ty*8+y
                width=2+max(0,yy-118)*40//94
                rows.append([0 if yy<118 or yy>=212 else (1 if ((tx*8+x-128)//width)&1 else 3) for x in range(8)])
            raw=encode(rows)
            if raw not in tiles: tiles[raw]=len(tiles)
            struct.pack_into('<H',vram,0xa000+(ty*32+tx)*2,tiles[raw])
    for raw,index in tiles.items(): vram[0x4000+index*16:0x4010+index*16]=raw
    assert len(tiles)*16<=8192,len(tiles)
    # 元の遠景をBG4へ。256pxに敷き詰め、地面とは別スクロール可能。
    far=Image.new('RGBA',(256,10))
    far.paste(Image.open(NES/'png/BgFarU/BgFarU.png').convert('RGBA').resize((256,8),Image.Resampling.NEAREST),(0,0))
    lower=Image.open(NES/'png/BgFarD/BgFarD.png').convert('RGBA').resize((256,2),Image.Resampling.NEAREST)
    for y in range(2):
        for x in range(256):
            if lower.getpixel((x,y))[3]<128: lower.putpixel((x,y),(0,0,0,255))
    far.paste(lower,(0,8))
    far_tiles={bytes(16):0}
    for ty in range(32):
        for tx in range(32):
            rows=[]
            for y in range(8):
                yy=ty*8+y-108
                row=[]
                for x in range(8):
                    if yy<0 or yy>=10: row.append(0); continue
                    r,g,b,a=far.getpixel(((tx*8+x)%far.width,yy%far.height))
                    row.append(0 if a<128 else (3 if r+g+b>=384 else 1))
                rows.append(row)
            raw=encode(rows)
            if raw not in far_tiles: far_tiles[raw]=len(far_tiles)
            struct.pack_into('<H',vram,0xc000+(ty*32+tx)*2,far_tiles[raw])
    for raw,index in far_tiles.items(): vram[0x6000+index*16:0x6010+index*16]=raw
    (dest/'ppu.bin').write_bytes(vram)
    (dest/'far_map.bin').write_bytes(vram[0xc000:0xc800])
    print(f'BG ground {len(tiles)} tiles, far {len(far_tiles)} tiles')

def pack_assets():
    # 各256byte行の未使用128..159列へ、4画素/byteの同じ原画を置く。
    for bank in range(22):
        path=GAME/'assets'/f'bank{0x44+bank:02x}.bin'
        raw=bytearray(path.read_bytes())
        for half in range(2):
            image=Image.open(GAME/'assets'/f'{bank*2+half:02d}.png')
            for y in range(image.height):
                base=half*32768+y*256
                for x in range(0,image.width,4):
                    raw[base+128+x//4]=sum(raw[base+x+i]<<(i*2) for i in range(min(4,image.width-x)))
                    raw[base+160+x//4]=sum(raw[base+x+i]<<((3-i)*2) for i in range(min(4,image.width-x)))
        if raw!=path.read_bytes():path.write_bytes(raw)

def build_scaled(enabled, limits, row_margins=False):
    # 原画行の後のpaddingだけを利用。既存raw/packed/flip領域へは書かない。
    images=[Image.open(GAME/'assets'/f'{i:02d}.png').convert('RGBA') for i in range(44)]
    banks={b:bytearray((GAME/'assets'/f'bank{b:02x}.bin').read_bytes()) for b in range(0x44,0x5a)}
    holes=[]
    for asset,image in enumerate(images):
        start=(asset&1)*32768+image.height*256;end=(1+(asset&1))*32768
        if start<end:
            bank=0x44+asset//2
            banks[bank][start:end]=bytes(end-start)
            holes.append([bank,start,end])
    table=bytearray(65536)
    bounds=bytearray(2048)
    if row_margins:
        for slot,asset,lo,hi in ((0,0,32,128),(1,1,32,128),(2,4,32,128),(3,36,32,52)):
            image=images[asset];bank=0x44+asset//2
            for width in range(lo,hi+1):
                size=image.height*2;du=image.width*256//width
                hole=next(h for h in holes if h[0]==bank and h[2]-h[1]>=size)
                offset=hole[1];hole[1]+=size
                struct.pack_into('<H',bounds,slot*512+width*2,offset)
                for y in range(image.height):
                    opaque=[x for x in range(width) if image.getpixel(((x*du)>>8,y))[3]>=128]
                    left,right=(opaque[0],opaque[-1]+1) if opaque else (0,0)
                    banks[bank][offset+y*2:offset+y*2+2]=bytes((left,right))
    used=0
    if enabled:
        for asset,limit in limits:
            assert 0 <= asset < len(images) and 1 <= limit <= 255, (asset,limit)
            image=images[asset];source=banks[0x44+asset//2];sourcebase=(asset&1)*32768
            for width in range(1,limit+1):
                stride=(width+3)//4;size=stride*image.height;du=image.width*256//width
                hole=next((h for h in holes if h[2]-h[1]>=size),None)
                assert hole is not None, (asset,width,size)
                bank,offset,_=hole;hole[1]+=size
                data=bytearray(size)
                for y in range(image.height):
                    for x in range(width):
                        color=source[sourcebase+y*256+((x*du)>>8)]
                        data[y*stride+x//4]|=color<<((x&3)*2)
                banks[bank][offset:offset+size]=data
                struct.pack_into('<BBH',table,asset*1024+width*4,bank,stride,offset)
                used+=size
    for bank,data in banks.items():
        path=GAME/'assets'/f'bank{bank:02x}.bin'
        if data!=path.read_bytes():path.write_bytes(data)
    (GAME/'assets/scaled5f.bin').write_bytes(table)
    print(f'Horizontal Q8.8 packed scaling: {used} bytes in original ROM padding')
    return bounds

def prepare_logic(smooth_depth=True):
    reference = '--reference-logic' in sys.argv
    enemy_impl=(GAME/'enemy_impl.inc').read_text(encoding='utf-8')
    (BUILD/'em1_open_sizes.bin').write_bytes(open_enemy_sizes((UP/'monosh_enemy_data.c').read_text()))
    if smooth_depth:
        enemy_impl=enemy_impl.replace('unsigned char pose = e->display & 7, index;', 'unsigned char pose = e->display & 7;')
        enemy_impl=enemy_impl.replace('    index = pose - 1 + (e->z >= 80 ? 0 : (e->z >= 54 ? 5 : 10));\n    return monosh_em1_open_geometry + index*2;', '''    {
        static unsigned char dimensions[2];
        unsigned int size = fx_open_size(((unsigned int)pose << 8) | (e->z > 110 ? 110 : e->z));
        dimensions[0] = (unsigned char)size; dimensions[1] = (unsigned char)(size >> 8);
        return dimensions;
    }''')
        enemy_impl='unsigned int __fastcall__ fx_open_size(unsigned int);\n'+enemy_impl
    if reference: enemy_impl=enemy_impl.replace('fx_em0_geometry(e);', 'update_em0_geometry(e, path);')
    else: enemy_impl=enemy_impl.replace('void fx_enemy_em1_update(', 'void fx_enemy_em1_update_reference(')
    (BUILD/'enemy_impl.inc').write_text(enemy_impl,encoding='utf-8')
    for name in ['monosh_player','monosh_stage','monosh_enemy','monosh_combat',
                 'monosh_boss','monosh_projection','monosh_stage_data','monosh_enemy_data','monosh_boss_data']:
        text=(UP/(name+'.c')).read_text()
        if smooth_depth:
            text=smooth_depth_tables(name,text)
        if name == 'monosh_player':
            for decl in ['unsigned int player_fy','signed char death_vy','unsigned char death_timer',
                         'unsigned char movement_fraction','unsigned char death_accel_fraction',
                         'unsigned char intro_timer','unsigned char player_flip','unsigned char player_run_phase',
                         'const unsigned char pose_x_01','const unsigned char pose_x_12','const unsigned char pose_x_23']:
                text=text.replace('static '+decl,decl)
            if not reference:
                text=text.replace('void monosh_player_update(', 'void monosh_player_update_reference(')
        if name == 'monosh_enemy':
            if not reference:
                text=text.replace('monosh_enemy_fast_render();', 'fx_enemy_render();').replace('monosh_enemy_fast_render_bullets();', 'fx_enemy_render_bullets();')
                text=text.replace('monosh_enemy_fast_check_player_bullets();', 'fx_enemy_collisions();')
            text='void fx_em0_geometry(void *);\nvoid fx_enemy_collisions(void);\nvoid fx_enemy_render(void);\nvoid fx_enemy_render_bullets(void);\n'+text
            text='void fx_enemy_em1_update(void *, unsigned char);\n'+text
            text=text.replace('update_em1(enemy, i);','fx_enemy_em1_update(enemy, i);')
            text=text.replace('unsigned char monosh_enemy_fire_boss_at(', 'unsigned char legacy_enemy_fire_boss_at(')
            text=text.replace('enemy->bottom = sample[1];','enemy->bottom = sample[1] + monosh_ground_screen_delta;')
            start=text.index('    if ((unsigned char)(enemy->frame + 1u) < path->frames)')
            end=text.index('\n}',start)
            text=text[:start]+'    enemy->display = path->fire_frame;'+text[end:]
            text+='\n#include "enemy_impl.inc"\n'
        if name == 'monosh_stage':
            text='#include "port.h"\nvoid fx_stage_render(void);\nvoid fx_stage_update(void);\nunsigned char fx_stage_contact(void);\n'+text
            if not reference:
                text=text.replace('    stage_update(monosh_player_x);','    fx_stage_update();')
                text=text.replace('check_player_contact(monosh_player_x, monosh_player_bottom)', 'fx_stage_contact()')
            text=text.replace('*bottom_y += monosh_ground_screen_delta;',
              '*bottom_y = 207 - monosh_ground_depth_pointer[219-(unsigned char)*bottom_y];')
            text=text.replace('bottom_y += monosh_ground_screen_delta;',
              'bottom_y = 207 - monosh_ground_depth_pointer[219-(unsigned char)bottom_y];')
            text=text.replace('bottom_y += z >> 5;', 'bottom_y += z >= 9 ? 3 : (z >= 6 ? 2 : (z >= 2 ? 1 : 0));')
            # Replace the obsolete command array with a shared depth submission.
            start=text.index('                if (monosh_draw_count != MONOSH_DRAW_MAX)')
            end=text.index('\n            }',start)
            text=text[:start]+'''                unsigned char asset = obj->type == OBJECT_BUSH0 ? MONOSH_DRAW_BUSH0 :
                    (obj->type == OBJECT_BUSH1 ? MONOSH_DRAW_BUSH1 :
                    (obj->type == OBJECT_FLYSTONE ? MONOSH_DRAW_FLYSTONE :
                    (obj->type == OBJECT_TREE0 ? MONOSH_DRAW_TREE0 : MONOSH_DRAW_BOM0)));
                fx_submit(center_x, bottom_y, width, height, asset, 0, z, 0);
                if (obj->type != OBJECT_BOM0 && monosh_stage_need_hitboxes) {
                    StageHitbox *h = &monosh_stage_hitboxes[monosh_stage_hitbox_count++];
                    h->object = &objects[index]; h->z = z; h->width = width;
                    h->height = height; h->center_x = center_x; h->bottom_y = bottom_y;
                }'''+text[end:]
            text=text.replace('    stage_render();\n#ifdef __ROM__','''    monosh_stage_need_hitboxes = monosh_player_bullet_count != 0 && (monosh_runtime_frame_counter & 1u);
    monosh_stage_hitbox_count = 0;
    stage_render();
    if (monosh_stage_need_hitboxes) check_player_bullets();
#ifdef __ROM__''')
            text=text.replace('    stage_render();','    fx_stage_render();')
            text=text.replace('    if (monosh_stage_need_hitboxes) check_player_bullets();','    /* stage.s resolves live shots using the same projected rectangle. */')
        if name == 'monosh_boss':
            text='void fx_boss_project(void);\nvoid fx_boss_hits(void);\n'+text
            if not reference:
                text=text.replace('        dos_project_boss_parts();','        fx_boss_project();')
                text=text.replace('        check_hits();','        fx_boss_hits();')
            text=text.replace('(BOSS_GEOMETRY(monosh_boss_face_geometry, z)[1] >> 2)',
                              '((BOSS_GEOMETRY(monosh_boss_face_geometry, z)[1] >> 3) << 1)')
            text=text.replace('        dos_cache_boss_attributes();','        /* SNES shared draw queue replaces SAT cache. */')
            text=text.replace('((unsigned int)world_y * boss_explosion_scale(z) >> 8)',
                              '((unsigned long)world_y * boss_explosion_scale(z) >> 8)')
        if name == 'monosh_boss_data':
            text=text.replace('#ifdef __ROM__\nconst unsigned char monosh_boss_bullet_velocity',
                              '#if 1\nconst unsigned char monosh_boss_bullet_velocity')
        if name == 'monosh_combat':
            text=text.replace('    upload_bullet_pattern();', '    /* Patterns were installed in the ROM asset banks. */')
        (BUILD/(name+'.c')).write_text(text)

def main():
    BUILD.mkdir(parents=True,exist_ok=True)
    config=json.loads((GAME/'config.json').read_text(encoding='utf-8'))
    smooth_depth=config.get('smoothDepthSizes',True) and '--legacy-depth-sizes' not in sys.argv
    full_transfer=('--full-transfer' in sys.argv or config['fullFramebufferTransfer']) and '--partial-transfer' not in sys.argv
    gsu_uv=('--gsu-uv' in sys.argv or config['gsuUv']) and '--cpu-uv' not in sys.argv
    gsu_clip=('--gsu-clip' in sys.argv or config['gsuClip']) and '--cpu-clip' not in sys.argv
    if gsu_clip:
        gsu_uv=True
    cpu_clip_commands=gsu_clip and config.get('cpuClipCommands',False) and '--no-cpu-clip-commands' not in sys.argv
    stable_cache=gsu_clip and config.get('stableGsuCache',False) and '--no-stable-gsu-cache' not in sys.argv
    scaled=stable_cache and config.get('scaledRows',True) and '--no-scaled-rows' not in sys.argv
    scaled_limits=[(int(asset),limit) for asset,limit in config['scaledAssetWidths'].items()]
    if '--all-scaled-assets' in sys.argv:
        scaled_limits=[(13,96),(14,96),(31,96),(0,96),(1,96),(4,128)]
    bucket_sort='--bucket-sort' in sys.argv
    fast_obj=config.get('fastObj',True) and '--no-fast-obj' not in sys.argv
    scaled_clip=scaled and config.get('scaledClip',True) and '--no-scaled-clip' not in sys.argv
    fast_uv=scaled and config.get('fastUv',True) and '--no-fast-uv' not in sys.argv
    row_margins=fast_uv and (config.get('rowMargins',False) or '--row-margins' in sys.argv) and '--no-row-margins' not in sys.argv
    generic_pipeline=fast_uv and (config.get('genericPipeline',False) or '--generic-pipeline' in sys.argv) and '--no-generic-pipeline' not in sys.argv
    dynamic_dma=(config.get('dynamicDmaDeadline',False) or '--dynamic-dma-deadline' in sys.argv) and '--no-dynamic-dma-deadline' not in sys.argv
    dma_probe='--dma-deadline-probe' in sys.argv
    fine_dma=dynamic_dma and config.get('fineDmaDeadline',False) and '--no-fine-dma-deadline' not in sys.argv
    assert not dma_probe or dynamic_dma
    descriptor_dma=config.get('descriptorDma',True) and '--no-descriptor-dma' not in sys.argv
    dma_admission=9216 if '--legacy-dma-admission' in sys.argv else config.get('dmaAdmissionBytes',9984)
    assert 0 <= dma_admission <= 9984
    lock=json.loads((ROOT/'probes/v001/sources.lock.json').read_text(encoding='utf-8'))['ARM9/casfx']
    from bootstrap_probe import fetch
    fetch('ARM9/casfx',lock['commit'],'gsu/casfx.inc',lock['files']['gsu/casfx.inc']['sha256'])
    if '--import-assets' in sys.argv or not (GAME/'asset_tables.c').exists(): export_assets()
    from build_ground import build as build_ground
    build_ground()
    from build_scenery import build as build_scenery
    build_scenery()
    from build_objects import build as build_objects
    build_objects()
    pack_assets()
    bounds=build_scaled(scaled, scaled_limits, row_margins)
    scale=bytearray(65536)
    dimensions=[Image.open(GAME/'assets'/f'{i:02d}.png').size for i in range(44)]
    for axis in range(2):
        for asset,size in enumerate(dimensions):
            struct.pack_into('<256H',scale,axis*0x5800+asset*512,
                             *[size[axis]*256//n if n else 0 for n in range(256)])
    scale[0xb000:0xb02c]=bytes(w for w,h in dimensions)
    scale[0xb02c:0xb058]=bytes(h for w,h in dimensions)
    if row_margins:
        scale[0xb058:0xb858]=bounds
    (GAME/'assets/scale5e.bin').write_bytes(scale)
    prepare_logic(smooth_depth)
    sources=[p for p in sorted(BUILD.glob('monosh_*.c')) if p.stem != 'monosh_projection']+[GAME/n for n in ['game.c','combat_port.c','asset_tables.c','ground.c']]
    objects=[]
    for source in sources:
        out=BUILD/(source.stem+'.s'); obj=BUILD/(source.stem+'.o')
        run([CC65/'cc65.exe','-Oirs','--cpu','65c02','-D','__z88dk_fastcall=',
             *(['-D','FX_REFERENCE=1'] if '--reference-logic' in sys.argv else []),
             '-I',GAME/'platform','-I',UP,'-I',GAME,'-o',out,source])
        run([CC65/'ca65.exe','-o',obj,out]); objects.append(obj)
    for name in ['cpu','gsu','ground','packet','objects','projection','stage','stage_update','enemy_render','enemy_collision','enemy_geometry','enemy_bullet','enemy_update','player','frame','boss_render','boss_collision','combat','dma','submit','smooth_depth']:
        obj=BUILD/(name+'_asm.o')
        run([CC65/'ca65.exe',*(['-D','FX_REFERENCE=1'] if '--reference-logic' in sys.argv else []),
             *(['-D','FX_FULL_TRANSFER=1'] if full_transfer else []),
             *(['-D','FX_SMOOTH_DEPTH=1'] if smooth_depth else []),
             *(['-D','FX_GSU_UV=1'] if gsu_uv else []),
             *(['-D','FX_GSU_CLIP=1'] if gsu_clip else []),
             *(['-D','FX_CPU_CLIP_COMMANDS=1'] if cpu_clip_commands else []),
             *(['-D','FX_STABLE_GSU_CACHE=1'] if stable_cache else []),
             *(['-D','FX_SCALED_ROWS=1'] if scaled else []),
             *(['-D','FX_BUCKET_SORT=1'] if bucket_sort else []),
             *(['-D','FX_FAST_OBJ=1'] if fast_obj else []),
             *(['-D','FX_SCALED_CLIP=1'] if scaled_clip else []),
             *(['-D','FX_FAST_UV=1'] if fast_uv else []),
             *(['-D','FX_ROW_MARGINS=1'] if row_margins else []),
             *(['-D','FX_GENERIC_PIPELINE=1'] if generic_pipeline else []),
             *(['-D','FX_DYNAMIC_DMA=1'] if dynamic_dma else []),
             *(['-D','FX_FINE_DMA=1'] if fine_dma else []),
             *(['-D','FX_DMA_DEADLINE_PROBE=1'] if dma_probe else []),
             *(['-D','FX_DESCRIPTOR_DMA=1'] if descriptor_dma else []),
             '-D',f'FX_DMA_ADMISSION_BYTES={dma_admission}',
             '-I',ROOT/'.cache/casfx/gsu','-I',GAME,'-o',obj,GAME/(name+'.s')]); objects.append(obj)
    rom=BUILD/'MonoSHFX2_v001.sfc'
    run([CC65/'ld65.exe','-C',GAME/'rom.cfg','-m',BUILD/'game.map','-Ln',BUILD/'game.lbl',
         '-o',rom,*objects,CC65.parent/'lib/none.lib'])
    data=bytearray(rom.read_bytes()); assert len(data)==0x200000,len(data)
    # 標準LoROM reset vectorおよびchecksum。
    data[0x7ffc:0x7ffe]=struct.pack('<H',0x8000)
    data[0x7fdc:0x7fe0]=b'\xff\xff\x00\x00'
    checksum=sum(data)&65535
    data[0x7fdc:0x7fe0]=struct.pack('<HH',checksum^65535,checksum)
    rom.write_bytes(data)
    (BUILD/'build_mode.json').write_text(json.dumps({'fullFramebufferTransfer':full_transfer,'gsuUv':gsu_uv,'gsuClip':gsu_clip,
        'cpuClipCommands':cpu_clip_commands,'stableGsuCache':stable_cache,'scaledRows':scaled,'scaledAssetWidths':dict(scaled_limits) if scaled else {},'scaledClip':scaled_clip,'fastUv':fast_uv,'genericPipeline':generic_pipeline,'rowMargins':row_margins,'dynamicDmaDeadline':dynamic_dma,'fineDmaDeadline':fine_dma,'dmaDeadlineProbe':dma_probe,'fastObj':fast_obj,'descriptorDma':descriptor_dma,'dmaAdmissionBytes':dma_admission,'bucketSort':bucket_sort,'smoothDepthSizes':smooth_depth})+'\n')
    print(f'Built {rom} ({len(data)} bytes)')

if __name__=='__main__': main()
