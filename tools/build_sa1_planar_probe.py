"""位置が既知のfixtureで直接planar描画を測る。容量試算とは別の楽観的速度試験。"""
import argparse,hashlib,json,re,struct,subprocess
import numpy as np
from build_sa1_probe import ROOT,GAME,BUILD,CC,assets
from sa1_prescaled import address
from test_sa1_probe import jobs
from analyze_sa1_planar_data import groups


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--native',action='store_true');ap.add_argument('--bitplanes',action='store_true');ap.add_argument('--packed-native',action='store_true');args=ap.parse_args()
    variants=assets();fixtures=jobs();mode='packed_native' if args.packed_native else 'planar_bits' if args.bitplanes else 'planar_native' if args.native else 'planar_data'
    packed=[];dictionary={}
    for job in fixtures:
        commands=[]
        for center,bottom,w,h,asset,flags,*_ in job['draws']:
            if not w or not h:continue
            source=variants.get((asset,flags&3),variants[asset,0])[1];ah,aw=source.shape
            xs=(np.arange(w)*(aw*256//w))
            ys=(np.arange(h)*(ah*256//h))
            if flags&16:xs=aw*256-1-xs
            if flags&32:ys=ah*256-1-ys
            scaled=source[(ys>>8)[:,None],(xs>>8)[None,:]]
            left=center-w//2;top=bottom-h-20
            for dy,row in enumerate(scaled):
                y=top+dy
                if not 0<=y<192:continue
                visible=np.zeros(256,dtype=np.uint8)
                x0=max(left,0);x1=min(left+w,256)
                if x0>=x1:continue
                visible[x0:x1]=row[x0-left:x1-left]
                if args.packed_native:
                    for tx in range(64):
                        pixels=visible[tx*4:tx*4+4]
                        value=sum(int(c)<<(i*4) for i,c in enumerate(pixels))
                        if not value:continue
                        mask=sum((0 if c else 15)<<(i*4) for i,c in enumerate(pixels))
                        commands.append((y*128+tx*2,struct.pack('<HHB',mask,value,0)))
                    continue
                for tx,values in groups(visible,0):
                    dest=(y//8*32+tx)*32+(y%8)*2
                    dictionary.setdefault(values,len(dictionary));commands.append((dest,values))
        packed.append(commands)
    rom=bytearray(0x800000);cursor=0x20000
    def alloc(raw):
        nonlocal cursor
        raw=bytes(raw);boundary=0x8000 if cursor<0x400000 else 0x10000
        if cursor%boundary+len(raw)>boundary:cursor=(cursor+boundary-1)//boundary*boundary
        if 0x400000<=cursor<0x440000:cursor=0x440000
        assert cursor+len(raw)<=0x7f0000
        at=cursor;rom[at:at+len(raw)]=raw;cursor+=len(raw)
        return address(at)
    # 辞書の各bankに同じ実行部を置く。索引・呼出し費用を含む。
    dict_locations={};helpers={}
    for start in range(0,len(dictionary),4096):
        values=list(dictionary)[start:start+4096]
        raw=b''.join(struct.pack('<HHHH',v[0]*257,v[1]|v[2]<<8,v[3]|v[4]<<8,0) for v in values)
        base=alloc(raw)
        code=bytearray()
        for offset in (0,16):
            code+=b'\xb9'+struct.pack('<H',offset)
            code+=b'\x3f'+base.to_bytes(3,'little')
            code+=b'\x1f'+(base+(2 if offset==0 else 4)).to_bytes(3,'little')
            code+=b'\x99'+struct.pack('<H',offset)
        helper=alloc(code+b'\x6b');helpers[start//4096]=helper
        for index,value in enumerate(values):dict_locations[value]=(index*8,helper)
    programs=[]
    for commands in packed:
        parts=[];body=bytearray(b'\xe2\x20' if args.bitplanes else b'')
        for dest,value in commands:
            mask=value[0]*257;a=value[1]|value[2]<<8;b=value[3]|value[4]<<8
            code=bytearray()
            if args.native or args.bitplanes or args.packed_native:
                code+=b'\xa2'+struct.pack('<H',dest)
                planes=((0,value[1]),(1,value[2]),(16,value[3]),(17,value[4])) if args.bitplanes else ((0,a),(16,b))
                size=1 if args.bitplanes else 2;keep=value[0] if args.bitplanes else mask
                if args.packed_native:planes=((0,int.from_bytes(value[2:4],'little')),);keep=int.from_bytes(value[:2],'little')
                for offset,plane in planes:
                    if keep:
                        code+=b'\xbd'+struct.pack('<H',offset)+b'\x29'+keep.to_bytes(size,'little')
                        if plane:code+=b'\x09'+plane.to_bytes(size,'little')
                    else:code+=b'\xa9'+plane.to_bytes(size,'little')
                    code+=b'\x9d'+struct.pack('<H',offset)
            else:
                index,helper=dict_locations[value]
                code+=b'\xa2'+struct.pack('<H',index)+b'\xa0'+struct.pack('<H',dest)+b'\x22'+helper.to_bytes(3,'little')
            if len(body)+len(code)>30000:parts.append(bytes(body));body.clear()
            body+=code
        if args.bitplanes:body+=b'\xc2\x20'
        parts.append(bytes(body));next_address=None
        for part in reversed(parts):
            tail=(b'\x22'+next_address.to_bytes(3,'little') if next_address is not None else b'')+b'\x6b'
            next_address=alloc(part+tail)
        programs.append(next_address)
    table=alloc(b''.join(a.to_bytes(3,'little') for a in programs))
    cfg='MEMORY { BOOT: start=$008000,size=$7FB0,file=%O,fill=yes; HEADER: start=$00FFB0,size=$50,file=%O,fill=yes; IRAM: start=$0200,size=$0600,file="";'
    for bank in range(1,128):cfg+=f' B{bank:02X}: start=${bank:02X}0000,size=$10000,file=%O,fill=yes;'
    cfg+='} SEGMENTS { BOOT: load=BOOT,type=ro; HEADER: load=HEADER,type=ro; SA1: load=BOOT,run=IRAM,type=ro,define=yes; }'
    (BUILD/'probe.cfg').write_text(cfg)
    text=(GAME/'renderer_planar_probe.s').read_text(encoding='utf8').replace('.import planar_probe_programs: far',f'planar_probe_programs=${table:06x}')
    (BUILD/'renderer_planar_probe.s').write_text(text,encoding='utf8')
    objs=[]
    for name,source in [('probe',GAME/'probe.s'),('renderer',BUILD/'renderer_planar_probe.s')]:
        obj=BUILD/(name+'.o');subprocess.run([str(CC/'ca65.exe'),'-D','SA1_PRESCALED=1','-o',str(obj),str(source)],check=True);objs.append(str(obj))
    output=BUILD/f'MonoSHSA1_{mode}_probe.sfc'
    subprocess.run([str(CC/'ld65.exe'),'-C',str(BUILD/'probe.cfg'),'-Ln',str(BUILD/'probe.lbl'),'-o',str(output),*objs],check=True)
    labels={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.([^\s]+)',(BUILD/'probe.lbl').read_text())}
    rom[:65536]=output.read_bytes()[:65536]
    struct.pack_into('<H',rom,0x7ffc,labels['reset']);rom[0x7fdc:0x7fe0]=b'\xff\xff\0\0'
    checksum=sum(rom)&65535;struct.pack_into('<HH',rom,0x7fdc,checksum^65535,checksum);output.write_bytes(rom)
    config=dict(mode=mode,planar=not args.packed_native,fixturePrograms=True,runtimePlacementExcluded=True,gameIntegrated=False,
                fixtureCount=len(fixtures),dictionaryGroups=len(dictionary),fixturePayloadEnd=cursor,
                romSha256=hashlib.sha256(rom).hexdigest(),labelsSha256=hashlib.sha256((BUILD/'probe.lbl').read_bytes()).hexdigest())
    (BUILD/'mode.json').write_text(json.dumps(config,indent=2)+'\n');print(json.dumps(config))


if __name__=='__main__':main()
