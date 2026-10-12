"""ホストで用意した二面bitmapを実CC1/PPU DMAで連結する転送だけの試験。"""
import hashlib,json,re,struct,subprocess,zipfile
from pathlib import Path
import numpy as np
from build_sa1_probe import ROOT,CC
from test_sa1_probe import reference
from run_probe import prepare_runtime,MESEN_EXE,lua

BUILD=ROOT/'build/sa1_split_cc1'
DEST=ROOT/'game/sa1/v001/results/20261013_split_viewport'
SOURCE=ROOT/'build/sa1_game/movestress_detinput_captureburst_directleft_currentbase_tracepalette'


def planar(packed):
    data=np.frombuffer(packed,dtype=np.uint8).reshape(192,128)
    pixels=np.empty((192,256),dtype=np.uint8);pixels[:,::2]=data&15;pixels[:,1::2]=data>>4
    out=bytearray()
    for ty in range(24):
        for tx in range(32):
            p=pixels[ty*8:ty*8+8,tx*8:tx*8+8]
            tile=bytearray(32)
            for y in range(8):
                for bit in range(4):tile[(bit//2)*16+y*2+(bit&1)]=sum(int(p[y,x]>>bit&1)<<(7-x) for x in range(8))
            out+=tile
    return bytes(out)


def main():
    BUILD.mkdir(parents=True,exist_ok=True)
    jobs=[]
    for path in sorted(SOURCE.glob('present*_meta.bin')):
        g=int(path.name[7:12])
        if not 530<=g<=570:continue
        raw=path.read_bytes();n=struct.unpack_from('<H',raw,6)[0]
        draws=[list(struct.unpack_from('<hh6B',raw,10+i*10)) for i in range(n)]
        parts=[]
        for lo in (0,128):
            selected=[]
            for d in draws:
                x,b,w,h,a,f,*_=d;left=x-w//2
                if left+w>lo and left<lo+128:selected.append([x+64-lo,*d[1:]])
            parts.append(reference(dict(draws=selected)))
        expected=reference(dict(draws=draws))
        assert expected==b''.join(parts[0][y*128+32:y*128+96]+parts[1][y*128+32:y*128+96] for y in range(192))
        jobs.append(dict(name=f'game{g}',parts=parts,expected=planar(expected)))
    assert len(jobs)==41
    # 全16色・行・tile・左右が異なるパターン。読み出しのずれを疎な実画像だけで見逃さない。
    y,x=np.indices((192,256));p=((x^(y*3)^(x//8*7)^(y//8*11))&15).astype(np.uint8)
    packed=(p[:,::2]|p[:,1::2]<<4).tobytes()
    parts=[]
    for lo in (0,128):
        padded=np.full((192,256),13,dtype=np.uint8);padded[:,64:192]=p[:,lo:lo+128]
        parts.append((padded[:,::2]|padded[:,1::2]<<4).tobytes())
    jobs.append(dict(name='all_colors_pattern',parts=parts,expected=planar(packed)))
    records=[]
    for i,j in enumerate(jobs):
        name=j['name'];(BUILD/(name+'_source.bin')).write_bytes(b''.join(j['parts']))
        (BUILD/(name+'_expected.bin')).write_bytes(j['expected'])
        records.append(dict(name=name,bank=0x40+i%3))
    cfg='''MEMORY {
 BOOT: start=$008000, size=$7FB0, file=%O, fill=yes, fillval=$EA;
 HEADER: start=$00FFB0, size=$0050, file=%O, fill=yes;
 PAD: start=$018000, size=$7F8000, file=%O, fill=yes;
 IRAM: start=$000200, size=$0300, file="";
}
SEGMENTS { BOOT: load=BOOT, type=ro; HEADER: load=HEADER, type=ro;
 SA1: load=BOOT, run=IRAM, type=ro, define=yes; }
'''
    (BUILD/'probe.cfg').write_text(cfg)
    subprocess.run([str(CC/'ca65.exe'),'-o',str(BUILD/'probe.o'),str(ROOT/'game/sa1/v001/split_cc1_probe.s')],check=True)
    rom_path=BUILD/'MonoSHSA1_split_cc1_probe.sfc'
    subprocess.run([str(CC/'ld65.exe'),'-C',str(BUILD/'probe.cfg'),'-Ln',str(BUILD/'probe.lbl'),'-m',str(BUILD/'probe.map'),'-o',str(rom_path),str(BUILD/'probe.o')],check=True)
    rom=bytearray(rom_path.read_bytes());assert len(rom)==0x800000
    labels={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.([^\s]+)',(BUILD/'probe.lbl').read_text())}
    struct.pack_into('<H',rom,0x7ffc,labels['reset']);rom[0x7fdc:0x7fe0]=b'\xff\xff\0\0'
    checksum=sum(rom)&65535;struct.pack_into('<HH',rom,0x7fdc,checksum^65535,checksum);rom_path.write_bytes(rom)
    for name in ('timings.json','emulator.log'):(BUILD/name).unlink(missing_ok=True)
    script='''local jobs=JOBS
local labels=LABELS
local output=OUTPUT
local index=1;local ready=false;local start=0;local rows={}
local function cb(name,fn)
 emu.addMemoryCallback(fn,emu.callbackType.exec,labels[name],labels[name],emu.cpuType.snes,emu.memType.snesMemory)
end
cb('probe_ready',function()
 if ready then return end
 local j=jobs[index];local f=assert(io.open(output..'/'..j.name..'_source.bin','rb'));local s=f:read('*a');f:close()
 assert(#s==49152)
 local bank=(j.bank-0x40)*65536
 for i=0,24575 do
  emu.write(bank+0x400+i,s:byte(i+1),emu.memType.snesSaveRam)
  emu.write(bank+0x8400+i,s:byte(24577+i),emu.memType.snesSaveRam)
 end
 for _,a in ipairs({0x6a00,0xea00})do for i=0,63 do emu.write(bank+a+i,(i*71+37)&255,emu.memType.snesSaveRam)end end
 emu.write16(0x3108,j.bank,emu.memType.snesMemory);emu.write16(0x3100,1,emu.memType.snesMemory);ready=true
end)
cb('split_transfer_begin',function()start=emu.getState().masterClock end)
cb('probe_finished',function()
 local j=jobs[index];local t={}
 for i=0,24575 do t[#t+1]=string.char(emu.read(i,emu.memType.snesVideoRam))end
 local f=assert(io.open(output..'/'..j.name..'_actual.bin','wb'));f:write(table.concat(t));f:close()
 local bank=(j.bank-0x40)*65536
 for _,a in ipairs({0x6a00,0xea00})do for i=0,63 do assert(emu.read(bank+a+i,emu.memType.snesSaveRam)==((i*71+37)&255),'prefix metadata changed')end end
 local s=emu.getState();assert(not s['cart.coprocessor.charConvDmaActive'])
 rows[#rows+1]=string.format('{"name":"%s","bank":%d,"clocks":%d}',j.name,j.bank,s.masterClock-start)
 if index==#jobs then
  local f=assert(io.open(output..'/timings.json','w'));f:write('['..table.concat(rows,',')..']');f:close();emu.stop(0)
 else index=index+1;ready=false end
end)
'''.replace('JOBS',lua(records)).replace('LABELS',lua(labels)).replace('OUTPUT',lua(BUILD.as_posix()))
    (BUILD/'test.lua').write_text(script);exe=prepare_runtime(MESEN_EXE)
    r=subprocess.run([str(exe),'--testRunner','--timeout=120','--doNotSaveSettings','--enableStdout',str(rom_path),str(BUILD/'test.lua')],cwd=exe.parent,capture_output=True,timeout=130,creationflags=subprocess.CREATE_NO_WINDOW)
    (BUILD/'emulator.log').write_bytes(r.stdout+r.stderr)
    assert r.returncode==0,(r.returncode,r.stdout,r.stderr)
    times=json.loads((BUILD/'timings.json').read_text());assert len(times)==len(jobs)
    for job,row in zip(jobs,times):
        assert row['name']==job['name']
        assert (BUILD/(job['name']+'_actual.bin')).read_bytes()==job['expected'],job['name']
    result=dict(romSha256=hashlib.sha256(rom).hexdigest(),jobs=len(jobs),pixelMatchedJobs=len(jobs),
        sourceBanks=sorted({r['bank'] for r in records}),dmaBytesPerJob=24576,dmaDescriptorsPerJob=48,
        sourceBitmapsPreparedByHost=True,gameIntegrated=False,sa1DrawingBenchmarked=False,
        hardwareTransferVerified=True,forcedBlankDuringTransfer=True,visibleRasterTimingVerified=False,
        cC1WidthPixels=256,conversionBaseOffset=0x400,secondBitmapOffset=0x8400,
        noCentralBitmapCopy=True,prefixMetadataGuardBytesPerJob=128,
        goal60fpsAchieved=False,timings=times)
    (DEST/'cc1_transfer.json').write_text(json.dumps(result,indent=2)+'\n')
    archive=DEST/'cc1_transfer_evidence.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(BUILD.iterdir()):
            if p.is_file() and p.suffix not in ('.o',):z.write(p,p.name)
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    (DEST/'cc1_transfer_archive.json').write_text(json.dumps(dict(bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest()),indent=2)+'\n')
    print({k:v for k,v in result.items() if k!='timings'})


if __name__=='__main__':main()
