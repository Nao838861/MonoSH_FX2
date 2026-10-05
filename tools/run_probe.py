"""FX2 ROMをbuildし、Mesenで描画結果・GSU master clocksを検証する。"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / 'probes/v001'
BUILD = ROOT / 'build/v001'
HZ = 21_477_272
NES_ROOT = Path(os.environ.get('MONOSH_NES_ROOT','D:/HomeBrew/MonoSH'))
MESEN_EXE = Path(os.environ.get('MONOSH_FX2_MESEN','D:/HomeBrew/Mesen/Mesen.exe'))


def lua(value):
    if isinstance(value, dict):
        return '{' + ','.join(f'[{lua(k)}]={lua(v)}' for k, v in value.items()) + '}'
    if isinstance(value, list):
        return '{' + ','.join(map(lua, value)) + '}'
    if isinstance(value, str):
        return json.dumps(value)
    return str(value)


def source_image(kind):
    rows = [[0] * 128 for _ in range(192)]
    if kind == 'tree':
        path = NES_ROOT/'png/Tree0/Tree0_00.png'
        im = Image.open(path).convert('RGBA').resize((68, 160), Image.Resampling.NEAREST)
        for y in range(im.height):
            for x in range(im.width):
                r, g, b, a = im.getpixel((x, y))
                rows[y][x] = 0 if a < 128 else (3 if (77*r+150*g+29*b) >> 8 >= 128 else 1)
    elif kind == 'solid':
        rows = [[3] * 128 for _ in range(192)]
    elif kind == 'fragmented':
        rows = [[3 if x % 2 else 0 for x in range(128)] for _ in range(192)]
    else:
        raise ValueError(kind)
    return rows


def export_source(rows, dest):
    pixels = bytearray(65536)
    runs = bytearray(65536)
    bounds = bytearray(65536)
    packed = bytearray(65536)
    for y, row in enumerate(rows):
        pixels[y*256:y*256+128] = bytes(row)
        spans = []
        x = 0
        while x < 128:
            color = row[x]
            start = x
            while x < 128 and row[x] == color:
                x += 1
            if color:
                spans.extend((start, x, color))
        assert len(spans) + 1 <= 256, 'run列が行pitch超過。点参照用アセットへ切り替える必要がある'
        runs[y*256] = len(spans)//3
        runs[y*256+1:y*256+1+len(spans)] = bytes(spans)
        xs=[x for x,c in enumerate(row) if c]
        bounds[y*256:y*256+2]=bytes((min(xs),max(xs)+1)) if xs else bytes((0,0))
        for x,c in enumerate(row):
            packed[y*32+x//4] |= c << ((x%4)*2)
    (dest/'pixels.bin').write_bytes(pixels)
    (dest/'runs.bin').write_bytes(runs)
    (dest/'bounds.bin').write_bytes(bounds)
    (dest/'packed.bin').write_bytes(packed)


def build(dest, rows, gsu_source=None):
    export_source(rows, dest)
    objects=[]
    for stem in ('cpu','gsu'):
        obj=dest/f'{stem}.o'
        subprocess.run(['ca65', '-I', str(ROOT/'.cache/casfx/gsu'), '-I', str(dest),
                        '-o', str(obj), str(gsu_source if stem=='gsu' and gsu_source else PROBE/f'{stem}.s')], cwd=dest, check=True)
        objects.append(str(obj))
    rom=dest/'probe.sfc'
    subprocess.run(['ld65','-C',str(PROBE/'rom.cfg'),'-o',str(rom),'-Ln',str(dest/'labels.txt'),*objects],check=True)
    labels={name:int(address,16) for address,name in re.findall(r'al ([0-9A-Fa-f]+) \.([^\s]+)',(dest/'labels.txt').read_text())}
    data=bytearray(rom.read_bytes())
    struct.pack_into('<H',data,0x7FFC,labels['reset'] & 0xFFFF)
    data[0x7FDC:0x7FE0]=b'\xff\xff\x00\x00'
    checksum=sum(data) & 0xFFFF
    struct.pack_into('<HH',data,0x7FDC,checksum ^ 0xFFFF,checksum)
    rom.write_bytes(data)
    return rom,labels


def framebuffer(rows, job, initial=None):
    out=bytearray(initial if initial is not None else [job['seed']]*12288)
    if job['kernel']=='clear':
        return bytes(12288)
    r=job['regs']
    x0,y0=r[5],r[2]
    width,height=job['width'],r[6]
    full_width=job['full_width']
    for dy in range(height):
        sy=(r[7]+dy*r[4]) >> 8
        for dx in range(width):
            if job['kernel'].startswith('runs'):
                sx=dx*128//full_width
            else:
                du=r[3] if r[3]<32768 else r[3]-65536
                sx=r[10]+dx*du if job['kernel']=='integer' or job['kernel'].startswith('packed') else (r[10]+dx*du) >> 8
            color=rows[sy][sx]
            if not color:
                continue
            x,y=x0+dx,y0+dy
            offset=((x//8)*24+y//8)*16+(y%8)*2
            bit=1 << (7-x%8)
            for plane in range(2):
                out[offset+plane] = (out[offset+plane] & (255 ^ bit)) | (bit if color & (1 << plane) else 0)
    return bytes(out)


def jobs(labels, cropped=False, sweep=False):
    result=[dict(name='clear',kernel='clear',seed=165,regs=[0]*15+[labels['clear_entry'] & 0xFFFF])]
    for width,height in ((128,192),(96,144),(64,96),(32,48),(16,24),(8,12),(31,47)):
        for kernel in ('nearest','nearest_unroll','runs','integer','bounded','runs_copy','runs_half','runs_quarter','packed_copy','packed_half','packed_quarter'):
            if kernel=='nearest_unroll' and width%8:
                continue
            if kernel=='integer' and 128%width:
                continue
            if kernel in ('runs_copy','runs_half','runs_quarter') and width!={'runs_copy':128,'runs_half':64,'runs_quarter':32}[kernel]:
                continue
            if kernel.startswith('packed') and width!={'packed_copy':128,'packed_half':64,'packed_quarter':32}[kernel]:continue
            r=[0]*16
            r[3]=128*256//width;r[4]=192*256//height
            if kernel=='integer' or kernel.startswith('packed'):
                r[3]=128//width
            r[6]=height;r[9]=width//8 if kernel=='nearest_unroll' else width
            if kernel.startswith('packed'):r[9]=width//{'packed_copy':4,'packed_half':2,'packed_quarter':1}[kernel]
            r[15]=labels[kernel+'_entry'] & 0xFFFF
            result.append(dict(name=f'{kernel}_{width}x{height}',kernel=kernel,seed=0,
                               regs=r,width=width,full_width=width))
    # 木の透明paddingを除いた領域でも比較し、RLEだけが有利な比較にしない。
    for full_width,height in (((128,160),(64,80),(32,40),(16,20),(8,10)) if cropped else ()):
        visible_width=(68*full_width+127)//128
        for kernel in ('nearest','runs','integer','runs_copy','runs_half','runs_quarter','packed_copy','packed_half','packed_quarter'):
            if kernel in ('runs_copy','runs_half','runs_quarter') and full_width!={'runs_copy':128,'runs_half':64,'runs_quarter':32}[kernel]:
                continue
            if kernel.startswith('packed') and full_width!={'packed_copy':128,'packed_half':64,'packed_quarter':32}[kernel]:continue
            r=[0]*16;r[3]=128*256//full_width;r[4]=192*256//(height*192//160)
            r[6]=height;r[9]=full_width if kernel.startswith('runs') else visible_width
            if kernel=='integer' or kernel.startswith('packed'):r[3]=128//full_width
            if kernel.startswith('packed'):r[9]=visible_width//{'packed_copy':4,'packed_half':2,'packed_quarter':1}[kernel]
            r[15]=labels[kernel+'_entry']&65535
            result.append(dict(name=f'cropped_{kernel}_{full_width}',kernel=kernel,seed=0,
                               regs=r,width=visible_width,full_width=full_width))
    for name,x,y,width,height,u,v,flip in (
        ('clip_left_top',0,0,57,85,7*512,11*512,False),
        ('clip_right_bottom',240,180,16,12,0,0,False),
        ('flip',10,20,64,96,63*512,0,True),
        ('transparent_overwrite',10,20,64,96,0,0,False),
    ):
        r=[0]*16;r[1]=x;r[2]=y;r[3]=(-512 if flip else 512)&65535;r[4]=512
        r[5]=x;r[6]=height;r[7]=v;r[9]=width;r[10]=u;r[15]=labels['nearest_entry']&65535
        result.append(dict(name=name,kernel='nearest',seed=85 if name=='transparent_overwrite' else 0,
                           regs=r,width=width,full_width=64))
    if sweep:
        for width in range(1,129):
            height=max(1,192*width//128)
            for kernel in ('nearest','bounded','runs'):
                r=[0]*16;r[3]=128*256//width;r[4]=192*256//height
                r[6]=height;r[9]=width;r[15]=labels[kernel+'_entry']&65535
                result.append(dict(name=f'sweep_{kernel}_{width}',kernel=kernel,seed=0,
                                   regs=r,width=width,full_width=width))
    return result


def prepare_runtime(mesen):
    runtime=ROOT/'.cache/mesen_runtime'
    runtime.mkdir(parents=True,exist_ok=True)
    (runtime/'settings.json').write_text(json.dumps({'Debug':{'ScriptWindow':{'AllowIoOsAccess':True}},
                                                  'Snes':{'GsuClockSpeed':100}}))
    for path in mesen.parent.iterdir():
        if path.is_file() and (path.suffix.lower()=='.dll' or path.name in ('Mesen.exe','MesenNesDB.txt')):
            target=runtime/path.name
            if not target.exists() or hashlib.sha256(target.read_bytes()).digest()!=hashlib.sha256(path.read_bytes()).digest():
                shutil.copy2(path,target)
    return runtime/mesen.name


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mesen',type=Path,default=MESEN_EXE)
    parser.add_argument('--source',choices=('tree','solid','fragmented','all'),default='all')
    parser.add_argument('--sweep',action='store_true',help='木の全出力幅1〜128で汎用3経路を検証する')
    args=parser.parse_args()
    BUILD.mkdir(parents=True,exist_ok=True)
    mesen=prepare_runtime(args.mesen)
    kinds=('tree','solid','fragmented') if args.source=='all' else (args.source,)
    summary=[]
    for kind in kinds:
        dest=BUILD/kind;dest.mkdir(exist_ok=True)
        rows=source_image(kind)
        rom,labels=build(dest,rows)
        cases=jobs(labels,kind=='tree',args.sweep and kind=='tree')
        code=(PROBE/'measure.lua').read_text(encoding='utf-8')
        code=code.replace('JOBS',lua(cases)).replace('LABELS',lua(labels)).replace('REPORT',lua((dest/'clocks.tsv').as_posix())).replace('OUTDIR',lua(dest.as_posix()))
        code='local ok,err=pcall(function()\n'+code+'\nend)\nif not ok then local f=io.open('+lua((dest/'error.txt').as_posix())+',"w");f:write(tostring(err));f:close();emu.stop(1) end\n'
        script=dest/'measure.lua';script.write_text(code,encoding='utf-8')
        run=subprocess.run([str(mesen),'--testRunner','--timeout=90','--doNotSaveSettings',
                            '--enableStdout',str(rom),str(script)],
                           cwd=mesen.parent,capture_output=True,timeout=100,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (dest/'emulator.log').write_bytes(run.stdout+run.stderr)
        report=dest/'clocks.tsv'
        if run.returncode or not report.exists():
            raise RuntimeError(f'Mesen failed ({run.returncode}): {dest}/emulator.log')
        records={}
        for line in report.read_text().splitlines():
            fields=line.split('\t')
            if len(fields)==3:
                records[fields[0]]=(int(fields[1]),fields[2]=='true')
        for job in cases:
            clocks,guard=records[job['name']]
            actual=(dest/(job['name']+'.bin')).read_bytes()
            expected=framebuffer(rows,job)
            assert len(actual)==len(expected)==12288,'framebuffer dump length differs'
            mismatches=sum(a!=b for a,b in zip(actual,expected))
            entry=dict(source=kind,case=job['name'],kernel=job['kernel'],master_clocks=clocks,
                       ms=clocks/HZ*1000,guard=guard,mismatched_bytes=mismatches)
            summary.append(entry)
            print(f"{kind:10} {job['name']:28} {entry['ms']:8.4f}ms mismatches={mismatches} guard={guard}")
            if mismatches or not guard:
                raise AssertionError(entry)
    result=dict(emulator_sha256=hashlib.sha256(mesen.read_bytes()).hexdigest(),
                master_hz=HZ,framebuffer='256x192 2bpp',cases=summary)
    (BUILD/'results.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    main()
