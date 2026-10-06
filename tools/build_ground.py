"""地形と共通のカメラ位置から、通常BGの直線投影と四色の表を生成する。"""
import math
import re
import struct
from pathlib import Path

GAME = Path(__file__).resolve().parents[1] / 'game/v001'

def numbers(text, name):
    body = re.search(name+r'\[\d+\] = \{(.*?)\};', text, re.S)[1]
    return [int(x, 0) for x in re.findall(r'0x[\da-fA-F]+|\b\d+\b', body)]

def array(name, values, ctype='unsigned char'):
    return f'const {ctype} {name}[{len(values)}] = {{\n'+''.join(
        ','.join(map(str, values[i:i+32]))+',\n' for i in range(0,len(values),32))+'};\n'

def build():
    assets=GAME/'assets'
    tables=(GAME/'asset_tables.c').read_text()
    # 地面の境界は消失点からの一次式。幅を整数化してから倍数を
    # 作ると外側ほど丸め誤差が拡大するため、境界位置で量子化する。
    width=[d*51//80 for d in range(81)]
    bands=[]
    for phase in range(14):
        p0=(phase//2)*2/7;p1=p0+2/7
        initial=1 if math.floor(104.4/6.5+((p0+p1)/2 if phase&1 else p0))%2==0 else 0
        edges=[]
        for stripe in range(3,20):
            boundary=lambda p:(104.4/(stripe-p)-.5-6)/39*80
            edge=(boundary(p0)+boundary(p1))/2 if phase&1 else boundary(p0)
            if 0<edge<=80:edges.append(math.ceil(edge))
        bands.extend(initial^(sum(e<=y for e in edges)%2) for y in range(81))
    # 指定RGBを明度順で保存し、RGB5の展開値で最も近い色を選ぶ。
    requested=[(114,193,112),(129,208,127),(145,223,145),(160,241,162)]
    green=[tuple(min(range(32),key=lambda v:abs(v*8+(v>>2)-c)) for c in color)
           for color in requested]
    colors=[r+(g<<5)+(b<<10) for r,g,b in green]
    # UV division is performed by the SNES divider; discard the large C lookup rows.
    tables=re.sub(r'const unsigned int fx_steps_\d+\[\d+\] = \{.*?\};\n','',tables,flags=re.S)
    tables=re.sub(r'const unsigned int \* const fx_d[uv]_table\[44\] = \{[^\n]*\};\n','',tables)
    for name, values, ctype in [('fx_ground_bands',bands,'unsigned char'),
            ('fx_ground_light',[colors[1]]*81,'unsigned int'),
            ('fx_ground_dark',[colors[0]]*81,'unsigned int')]:
        tables=re.sub(r'const '+ctype+' '+name+r'\[\d+\] = \{.*?\};\n',array(name,values,ctype),tables,flags=re.S)
    for name,values,ctype in [('fx_ground_width',width,'unsigned char'),('fx_ground_greens',colors,'unsigned int'),
                             ('fx_sky_color',[24+(14<<5)+(31<<10)],'unsigned int')]:
        tables=re.sub(r'const '+ctype+' '+name+r'\[\d+\] = \{.*?\};\n','',tables,flags=re.S)
        tables+=array(name,values,ctype)
    # 現在は色HDMAを事前生成する。初期C方式の未使用配列をWRAMへ置かない。
    for name,ctype in [('fx_ground_bands','unsigned char'),('fx_ground_light','unsigned int'),
                       ('fx_ground_dark','unsigned int'),('fx_ground_steps','unsigned int')]:
        tables=re.sub(r'const '+ctype+' '+name+r'\[\d+\] = \{.*?\};\n','',tables,flags=re.S)
    (GAME/'asset_tables.c').write_text(tables)
    scrolls=bytearray();rows=bytearray();so=[];ro=[];palette=bytearray();hr=bytearray();hro=[]
    def palette_table(values, address):
        raw=bytearray();start=0
        while start<len(values):
            end=start+1
            while end<len(values) and values[end]==values[start] and end-start<127:end+=1
            raw.extend(struct.pack('<BBBH',end-start,address,address,values[start]));start=end
        raw.append(0)
        assert len(raw)<=128,len(raw)
        return raw+bytes(128-len(raw))
    for offset in range(65):
        so.append(len(scrolls));ro.append(len(rows))
        horizon=104+offset
        left=horizon
        while left:
            run=min(127,left);scrolls.extend(struct.pack('<BH',run,(23-offset)&65535));left-=run
        count=205-horizon;scrolls.append(count|128)
        frame_rows=[]
        for physical in range(horizon,205):
            span=204-horizon
            source_y=127+((physical-horizon)*80+span//2)//span
            rows.append(source_y-127)
            frame_rows.append(source_y-127)
            scrolls.extend(struct.pack('<h',source_y-physical))
        scrolls.append(0)
        hro.append(len(hr))
        start=0
        while start<len(frame_rows):
            end=start+1
            while end<len(frame_rows) and frame_rows[end]==frame_rows[start] and end-start<127:end+=1
            hr.extend(bytes((end-start,frame_rows[start])));start=end
        hr.extend(bytes(2))
        for phase in range(14):
            states=[bands[phase*81+frame_rows[0]]]*horizon+[bands[phase*81+r] for r in frame_rows]
            # 同じ縦列の明度グループを維持する。横は最暗/最明、次の帯は中間二色。
            # pixel index 1（CGRAM65）は明るい列、index 3（67）は暗い列。
            palette+=palette_table([colors[2] if state else colors[3] for state in states],65)
            palette+=palette_table([colors[1] if state else colors[0] for state in states],67)
    for name,value in [('ground_scroll.bin',scrolls),('ground_rows.bin',rows),
            ('ground_scroll_offsets.bin',struct.pack('<65H',*so)),('ground_row_offsets.bin',struct.pack('<65H',*ro))]:
        (assets/name).write_bytes(value)
    (assets/'ground_horizontal.bin').write_bytes(bytes(128+phase*d*51//(64*80) for phase in range(128) for d in range(81)))
    (assets/'ground_horizontal_offsets.bin').write_bytes(struct.pack('<128H',*[phase*81 for phase in range(128)]))
    (assets/'ground_horizontal_runs.bin').write_bytes(hr)
    (assets/'ground_horizontal_run_offsets.bin').write_bytes(struct.pack('<65H',*hro))
    assert len(palette)==65*14*256
    for index in range(4):
        (assets/f'palette{0x5a+index:02x}.bin').write_bytes(palette[index*65536:(index+1)*65536].ljust(65536,b'\0'))
    vram=bytearray((assets/'ppu.bin').read_bytes())
    vram[0x4000:0x6000]=bytes(8192)
    tiles={bytes(16):0}
    for ty in range(32):
        for tx in range(64):
            raw=bytearray()
            for yy in range(8):
                y=ty*8+yy
                d=y-127
                pixels=[0 if not 0<=d<=80 else (3 if d==0 else
                        (1 if ((tx*8+x-256)*80//(d*51))&1 else 3)) for x in range(8)]
                for p in range(2):raw.append(sum(((pixels[x]>>p)&1)<<(7-x) for x in range(8)))
            raw=bytes(raw)
            if raw not in tiles:tiles[raw]=len(tiles)
            address=0xa000+(tx//32)*0x800+(ty*32+tx%32)*2
            struct.pack_into('<H',vram,address,tiles[raw])
    assert len(tiles)*16<=8192,len(tiles)
    for raw,index in tiles.items():vram[0x4000+index*16:0x4010+index*16]=raw
    (assets/'ppu.bin').write_bytes(vram)

if __name__=='__main__':build()
