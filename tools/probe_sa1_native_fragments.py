"""爆発fixtureと採取packetを実SA-1で再生し、遮蔽分割の費用を測る。"""
import argparse,hashlib,json,re,struct,subprocess
from pathlib import Path
import numpy as np
from build_sa1_probe import ROOT,CC,assets,BUILD as ASSET_BUILD
from sa1_compiled_rows import word_row
from sa1_patterns import dimensions
from analyze_sa1_opaque_spans import spans
from verify_sa1_native_fragments import execute
from test_sa1_probe import reference
from run_probe import prepare_runtime,MESEN_EXE,lua

BUILD=ROOT/'build/sa1_fragment_probe'
SOURCE=ROOT/'game/sa1/v001'


def fixtures(replay_directory=None):
    patterns=dimensions();out=[]
    for asset in (39,40,41):
        for width in (53,68,79):
            heights=sorted(h for w,h in patterns[asset] if w==width)
            assert heights
            for parity in (0,1,2,3):
                for shift in (-8,0,8):
                    w,h=width,heights[0];fw,fh=next((ww,hh) for ww,hh in sorted(patterns[40]) if ww==91)
                    behind=[128+parity,40+h+20,w,h,asset,0,0,0]
                    front=[128,32+shift+fh+20,fw,fh,40,0,0,0]
                    out.append(dict(name=f'a{asset}_w{width}_p{parity}_s{shift+8}',draws=[behind,front]))
    if replay_directory:
        replay=[]
        for p in sorted(replay_directory.glob('present*_meta.bin')):
            generation=int(p.name[7:12])
            if not 530<=generation<=570:continue
            raw=p.read_bytes();count=struct.unpack_from('<H',raw,6)[0]
            draws=[list(struct.unpack_from('<hh6B',raw,10+i*10)) for i in range(count)]
            replay.append(dict(name=f'replay{generation}',draws=draws))
        assert len(replay)==41
        out.extend(replay)
    return out


def build(replay_directory=None):
    BUILD.mkdir(parents=True,exist_ok=True);ASSET_BUILD.mkdir(parents=True,exist_ok=True)
    variants=assets();rom=bytearray(0x800000);cursor=0x440000;pool={};jobs=[];tables=bytearray()
    def alloc(raw):
        nonlocal cursor
        raw=bytes(raw)
        if raw in pool:return pool[raw]
        if cursor%65536+len(raw)>65536:cursor=(cursor+65535)&~65535
        assert cursor+len(raw)<0x7f0000
        pointer=0xc00000+cursor-0x400000;rom[cursor:cursor+len(raw)]=raw;cursor+=len(raw);pool[raw]=pointer
        return pointer
    def group_rows(data):
        """隠蔽のない連続行をnative chainへまとめる。形成費用はこのprobeでは除外。"""
        out=bytearray();chain=bytearray()
        def flush():
            if chain:
                pointer=alloc(chain+b'\x6b')
                out.extend(b'\0\0'+pointer.to_bytes(3,'little')+b'\0\0\0\0');chain.clear()
        for i in range(0,len(data),9):
            record=data[i:i+9]
            if record[5]==record[6]:
                chain+=b'\xa9'+record[:2]+b'\xaa\x22'+record[2:5]
            else:flush();out+=record
        flush()
        return out
    for fixture in fixtures(replay_directory):
        command=bytearray();baseline=bytearray();direct=bytearray()
        hidden_words=0;copied_bytes=0;fragmented_rows=0;direct_hidden=0
        for i,draw in enumerate(fixture['draws']):
            x,bottom,w,h,asset,flags,*_=draw;left=x-w//2;top=bottom-h-20
            phase=(flags&3) if asset in (6,7,8,31,37) else 0
            pix=variants[asset,phase][1];ah,aw=pix.shape
            u=np.arange(w)*(aw*256//w);v=np.arange(h)*(ah*256//h)
            if flags&16:u=aw*256-1-u
            if flags&32:v=ah*256-1-v
            scaled=pix[v>>8][:,u>>8]
            candidates=[]
            for front in fixture['draws'][i+1:]:
                fx,fb,fw,fh,fa,ff,*_=front
                if fa not in (39,40,41) or fw<64:continue
                fl=fx-fw//2;ft=fb-fh-20
                area=max(0,min(left+w,fl+fw)-max(left,fl))*max(0,min(top+h,ft+fh)-max(top,ft))
                candidates.append((area,front))
            best=max(candidates,key=lambda c:c[0])[1] if candidates else None
            if best:
                fx,fb,fw,fh,fa,ff,*_=best;fl=fx-fw//2;ft=fb-fh-20
                front_spans=spans(fa,fw,fh,ff,1)
            native_phase=(left//2*2)%4
            for y,row in enumerate(scaled):
                sy=top+y
                if not 0<=sy<192:continue
                row_phase=0 if sy==0 and left<2 else native_phase
                window=np.zeros(256+row_phase,dtype=np.uint8)
                x0=max(0,left);x1=min(256,left+w)
                if x0<x1:window[x0+row_phase:x1+row_phase]=row[x0-left:x1-left]
                code,blocks=word_row(window,0);assert len(code)<=255
                origin=blocks[0][0] if blocks else 0;code=bytearray(code)
                for pc in range(0,len(code)-1,3):
                    if code[pc] in (0xbd,0x9d):
                        offset=struct.unpack_from('<H',code,pc+1)[0];assert offset>=origin
                        struct.pack_into('<H',code,pc+1,offset-origin)
                code=bytes(code);pointer=alloc(code)
                parsed=[];begin=0;last_a=0;last_mask=0
                for pc in range(0,len(code)-1,3):
                    op=code[pc];arg=struct.unpack_from('<H',code,pc+1)[0]
                    if op==0xa9:last_a=arg;last_mask=0
                    elif op==0x29:last_mask=arg
                    elif op==0x09:last_a=arg
                    elif op==0x9d:parsed.append((arg,begin,pc+3,last_a,last_mask));begin=pc+3
                stop=resume=0;initial=0;fy=sy-ft if best else -1;hidden=[]
                if best and 0<=fy<fh:
                    for off,begin,end,a,m in parsed:
                        px=-row_phase+(off+origin)*2
                        if 0<=px and px+4<=256 and any(fl+l<=px and px+4<=fl+r for l,r in front_spans[fy]):hidden.append((off,begin,end,a,m))
                safe_pc=0;drop_direct_row=False
                if hidden:
                    stop=hidden[0][1];resume=hidden[-1][2];initial=hidden[-1][3]
                    assert [b for b in parsed if stop<=b[1]<resume]==hidden
                    if code[resume]==0x9d:assert not hidden[-1][4]
                    visible=execute(code[:stop]+b'\x6b')|execute(code[resume:],initial)
                    original=execute(code)
                    assert visible=={off:v for off,v in original.items() if off not in {b[0] for b in hidden}}
                    hidden_words+=len(hidden);copied_bytes+=stop;fragmented_rows+=1
                    if stop==0:
                        if resume==len(code)-1:drop_direct_row=True;direct_hidden+=len(hidden)
                        else:
                            safe_pc=resume
                            if code[safe_pc]==0x9d:
                                safe_pc=next(pc for pc in range(safe_pc-3,-1,-3) if code[pc] in (0xa9,0xbd))
                            writes=execute(code[safe_pc:]);original=execute(code)
                            assert all(original[off]==value for off,value in writes.items())
                            assert all(off in writes for off in original if off not in {b[0] for b in hidden})
                            direct_hidden+=len(original)-len(writes)
                    if resume==len(code)-1:resume=255  # 空suffixを呼ばない。全隠蔽行も同時に省く。
                dest=(sy*128-row_phase//2+origin)&65535
                packed=struct.pack('<H',dest)+pointer.to_bytes(3,'little')+bytes((stop,resume))+struct.pack('<H',initial)
                command+=packed;baseline+=packed[:5]+b'\0\0\0\0'
                if not drop_direct_row:
                    direct+=packed[:2]+(pointer+safe_pc).to_bytes(3,'little')+b'\0\0\0\0'
        # 表生成・候補選択の費用は含めない。同じdescriptorのbaselineと比較する。
        for mode,name,data in ((0,'baseline',baseline),(1,'dma',command),(2,'mvn',command),(0,'direct',direct)):
            data=group_rows(data)
            count=len(data)//9;ptr=alloc(data);tables+=struct.pack('<H',count)+ptr.to_bytes(3,'little')+bytes((mode,))
            jobs.append(fixture|dict(name=fixture['name']+'_'+name,mode=name,hiddenWords=hidden_words,
                copiedPrefixBytes=copied_bytes,fragmentedRows=fragmented_rows,directHiddenWords=direct_hidden))
    rom[0x420000:0x420000+len(tables)]=tables
    cfg='''MEMORY {
 BOOT: start=$008000, size=$7FB0, file=%O, fill=yes, fillval=$EA;
 HEADER: start=$00FFB0, size=$0050, file=%O, fill=yes;
 PAD: start=$018000, size=$7F8000, file=%O, fill=yes;
 IRAM: start=$000200, size=$0300, file="";
}
SEGMENTS {
 BOOT: load=BOOT, type=ro;
 HEADER: load=HEADER, type=ro;
 SA1: load=BOOT, run=IRAM, type=ro, define=yes;
}
'''
    (BUILD/'probe.cfg').write_text(cfg)
    objects=[]
    for name in ('probe','renderer_fragment_probe'):
        obj=BUILD/(name+'.o');subprocess.run([str(CC/'ca65.exe'),'-D','SA1_PRESCALED=1','-o',str(obj),str(SOURCE/(name+'.s'))],check=True);objects.append(str(obj))
    target=BUILD/'MonoSHSA1_fragment_probe.sfc'
    subprocess.run([str(CC/'ld65.exe'),'-C',str(BUILD/'probe.cfg'),'-Ln',str(BUILD/'probe.lbl'),'-m',str(BUILD/'probe.map'),'-o',str(target),*objects],check=True)
    linked=target.read_bytes();assert len(linked)==len(rom)
    rom[:65536]=linked[:65536]
    labels={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.([^\s]+)',(BUILD/'probe.lbl').read_text())}
    assert labels['__SA1_SIZE__']<=0x300
    struct.pack_into('<H',rom,0x7ffc,labels['reset']);rom[0x7fdc:0x7fe0]=b'\xff\xff\0\0'
    checksum=sum(rom)&65535;struct.pack_into('<HH',rom,0x7fdc,checksum^65535,checksum);target.write_bytes(rom)
    manifest=dict(romSha256=hashlib.sha256(rom).hexdigest(),sa1WorkerBytes=labels['__SA1_SIZE__'],
        payloadEnd=cursor,jobs=len(jobs),gameIntegrated=False,occlusionSelectionAndTableGenerationCostIncluded=False,
        viewportClippingPrecomputed=True,unoccludedRowRunsPrecompiled=True,
        noCopyVariantPrecompiledOracle=True,noCopyChainFormationCostIncluded=False,
        replayDirectory=str(replay_directory) if replay_directory else None,goal60fpsAchieved=False)
    (BUILD/'jobs.json').write_text(json.dumps(jobs,indent=2)+'\n');(BUILD/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(manifest)


def test():
    jobs=json.loads((BUILD/'jobs.json').read_text());manifest=json.loads((BUILD/'manifest.json').read_text())
    rom=BUILD/'MonoSHSA1_fragment_probe.sfc';assert hashlib.sha256(rom.read_bytes()).hexdigest()==manifest['romSha256']
    for name in ('timings.json','summary.json'):(BUILD/name).unlink(missing_ok=True)
    labels={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.([^\s]+)',(BUILD/'probe.lbl').read_text())}
    script='''local jobs=JOBS
local labels=LABELS
local output=OUTPUT
local index=1
local ready=false
local started,draw=0,0
local drawStarts=0
local results={}
local function cb(name,cpu,fn)
 emu.addMemoryCallback(fn,emu.callbackType.exec,labels[name],labels[name],cpu,cpu==emu.cpuType.sa1 and emu.memType.sa1Memory or emu.memType.snesMemory)
end
cb('probe_ready',emu.cpuType.snes,function()
 if ready then return end
 emu.write16(0x3108,index-1,emu.memType.snesMemory)
 emu.write16(0x3100,1,emu.memType.snesMemory)
 ready=true
end)
cb('sa1_clear_start',emu.cpuType.sa1,function()started=emu.getState().masterClock;drawStarts=0 end)
cb('sa1_draw_start',emu.cpuType.sa1,function()draw=emu.getState().masterClock;drawStarts=drawStarts+1 end)
cb('sa1_draw_done',emu.cpuType.sa1,function()
 assert(drawStarts==1,'draw start callback repeated inside row loop')
 local clock=emu.getState().masterClock
 results[#results+1]=string.format('{"name":"%s","drawClocks":%d,"totalClocks":%d}',jobs[index].name,clock-draw,clock-started)
end)
cb('probe_finished',emu.cpuType.snes,function()
 local f=assert(io.open(output..'/'..jobs[index].name..'.bin','wb'));local bytes={}
 for i=0,24575 do bytes[#bytes+1]=string.char(emu.read(i,emu.memType.snesSaveRam))end
 f:write(table.concat(bytes));f:close()
 if index==#jobs then
  local f=assert(io.open(output..'/timings.json','w'));f:write('['..table.concat(results,',')..']');f:close();emu.stop(0)
 else index=index+1;ready=false end
end)
'''.replace('JOBS',lua(jobs)).replace('LABELS',lua(labels)).replace('OUTPUT',lua(BUILD.as_posix()))
    (BUILD/'test.lua').write_text(script);exe=prepare_runtime(MESEN_EXE)
    r=subprocess.run([str(exe),'--testRunner','--timeout=180','--doNotSaveSettings','--enableStdout',str(rom),str(BUILD/'test.lua')],cwd=exe.parent,capture_output=True,timeout=190,creationflags=subprocess.CREATE_NO_WINDOW)
    (BUILD/'emulator.log').write_bytes(r.stdout+r.stderr)
    assert r.returncode==0, f'Mesen {r.returncode}'
    times=json.loads((BUILD/'timings.json').read_text());assert len(times)==len(jobs)
    for job,row in zip(jobs,times):
        assert row['name']==job['name']
        actual=(BUILD/(job['name']+'.bin')).read_bytes();expected=reference(job)
        if actual!=expected:
            (BUILD/(job['name']+'_expected.bin')).write_bytes(expected)
            raise AssertionError(f'{job["name"]}: {sum(a!=b for a,b in zip(actual,expected))} bytes differ')
        row.update({k:job[k] for k in ('mode','hiddenWords','copiedPrefixBytes','fragmentedRows','directHiddenWords')})
        row['drawMs']=row['drawClocks']/21477.272
    ratios=[]
    for i in range(0,len(times),4):
        base,dma,mvn,direct=times[i:i+4]
        ratios.append(dict(name=base['name'].removesuffix('_baseline'),baselineMs=base['drawMs'],dmaMs=dma['drawMs'],mvnMs=mvn['drawMs'],
            directMs=direct['drawMs'],dmaRatio=dma['drawClocks']/base['drawClocks'],mvnRatio=mvn['drawClocks']/base['drawClocks'],
            directRatio=direct['drawClocks']/base['drawClocks'],hiddenWords=base['hiddenWords'],directHiddenWords=base['directHiddenWords']))
    assert hashlib.sha256(rom.read_bytes()).hexdigest()==manifest['romSha256']
    summary=manifest|dict(pixelMatchedJobs=len(times),timings=times,comparisons=ratios,
        dmaFasterCases=sum(r['dmaRatio']<1 for r in ratios),mvnFasterCases=sum(r['mvnRatio']<1 for r in ratios),
        directFasterCases=sum(r['directRatio']<1 for r in ratios))
    (BUILD/'summary.json').write_text(json.dumps(summary,indent=2)+'\n');print({k:v for k,v in summary.items() if k not in ('timings','comparisons')})


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--test',action='store_true');ap.add_argument('--replay-directory',type=Path);args=ap.parse_args()
    test() if args.test else build(args.replay_directory)
