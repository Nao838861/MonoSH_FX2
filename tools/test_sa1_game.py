"""実SA-1とPPUが動く統合ROMの計測。画面・転送後のVRAMも保存する。"""
import argparse,hashlib,json,re,subprocess,struct
from pathlib import Path
import numpy as np
from PIL import Image
from build_sa1_game import BUILD
from run_probe import prepare_runtime,MESEN_EXE,lua
from test_sa1_probe import reference
from build_sa1_game import BASE

def verify_game_state_audit(dest,logic,scenario):
    audit=[json.loads(x) for x in (dest/'game_state_audit.jsonl').read_text().splitlines()]
    first=audit[0]['logic'];assert first in (1,2)
    # 初期packetを用意するboot内の最初の_fx_frameはlogic_finishedを通らない。
    # 中途の欠落を許容せず、外側loopに入った後の全更新を確認する。
    last=audit[-1]['logic'];assert last in (logic-1,logic)
    # field終了で停止するため、最後の_fx_frameが実行途中の場合は未完了1件を区別する。
    assert [x['logic'] for x in audit]==list(range(first,last+1))
    assert all(a['clock']<b['clock'] for a,b in zip(audit,audit[1:]))
    return dict(logicUpdates=len(audit),firstLogicGeneration=first,lastCompletedLogicGeneration=last,
        initialBootUpdateNotCaptured=first-1,startedButNotCompletedAtStop=logic-last,
        playerStates=sorted({x['playerState'] for x in audit}),bossStates=sorted({x['bossState'] for x in audit}),
        minimumBossHp=min(x['bossHp'] for x in audit),maximumStageFrame=max(x['stageFrame'] for x in audit),
        maximumEnemies=max(x['enemies'] for x in audit),maximumPlayerBullets=max(x['playerBullets'] for x in audit),
        runtimeCounterResets=sum(b['runtimeFrame']<a['runtimeFrame'] for a,b in zip(audit,audit[1:])),
        observationalOnly=True,invulnerabilityInjected='stress' in scenario)

def verify_mask_bounds(dest,exact):
    """各帯の左右端が転送tile集合を含むことを再確認。新方式は厳密一致。"""
    data=(dest/'mask_bounds_trace.bin').read_bytes()
    assert len(data)%194==0
    count=len(data)//194
    empty_aliases=0;conservative=0
    for i in range(count):
        record=data[i*194:(i+1)*194]
        generation,=struct.unpack_from('<H',record)
        assert generation==i+1,(i,generation)
        for band in range(24):
            mask,=struct.unpack_from('<I',record,2+4*band)
            left,right=struct.unpack_from('<HH',record,98+4*band)
            expected=((((mask&-mask).bit_length()-1)*4,mask.bit_length()*4) if mask else (128,0))
            if not mask and left>=right:
                empty_aliases+=int((left,right)!=(128,0))
                if exact:assert (left,right)==(128,0)
            else:
                assert left<=expected[0] and right>=expected[1],(generation,band,hex(mask),(left,right),expected)
                conservative+=int((left,right)!=expected)
                if exact:assert (left,right)==expected
    fb=(dest/'mask_bounds_frames.bin').stat().st_size
    assert fb%24578==0
    return dict(jobs=count,bands=count*24,recordBytes=194,equivalentEmptyBounds=empty_aliases,conservativeBounds=conservative,fullFramebufferJobs=fb//24578,exact=exact)

def verify_clip_cache_coverage(dest):
    """上書きと再利用を実行ログから確認し、fixtureの見かけだけの合格を避ける。"""
    from collections import Counter
    events=[json.loads(line) for line in (dest/'clip_cache.jsonl').read_text().splitlines()]
    counts=Counter(e['event'] for e in events)
    for key in ('clip_left_cache_hit','clip_left_cache_miss','clip_reverse_cache_hit','clip_reverse_cache_miss'):
        assert counts[key]>=120, f'clip fixture did not exercise {key}'
    for e in events:
        if e['event']=='clip_left_cache_hit':assert e['tag']==1
        if e['event']=='clip_reverse_cache_hit':assert e['tag']==2
    evictions=Counter(e['event'] for e in events if e['tag'] in (1,2) and e['event'].endswith('_invalidate'))
    assert evictions['clip_cache_edge_invalidate']>=120 and evictions['clip_cache_bullet_invalidate']>=120
    return dict(events=dict(counts),evictionsOfResidentHelper=dict(evictions))


def opaque_prefix_coverage(dest):
    from collections import Counter
    events=[json.loads(line) for line in (dest/'opaque_prefix.jsonl').read_text().splitlines()]
    selected=[e for e in events if e['kind']=='select'];patched=[e for e in events if e['kind']=='patch']
    return dict(selectedObjects=len(selected),patchedRows=len(patched),advancedRows=sum(e['new']>e['old'] for e in patched),
        allHiddenRows=sum(e['allHidden'] for e in patched),hintFormats=dict(Counter(str(e['format']) for e in patched)))


def verify_opaque_fixture_coverage(dest):
    from sa1_patterns import dimensions
    patterns=dimensions();targets=set();fronts=set();centers=set();tops=set();count=0
    for path in dest.glob('present*_meta.bin'):
        raw=path.read_bytes();n=struct.unpack_from('<H',raw,6)[0]
        if n!=5:continue  # 最初の通常ゲーム画面は全画素照合するがfixtureの組合せには数えない。
        draws=[struct.unpack_from('<hh6B',raw,10+i*10) for i in range(n)]
        assert draws[0][4]==39 and draws[1][4]==40 and draws[2][4]==7 and draws[3][4]==40
        for draw in (draws[1],draws[3]):
            x,b,w,h,a,flags,*_=draw;assert flags==0
            targets.add((w,h));centers.add(x);tops.add(b-h-20)
        fronts.add((draws[4][4],draws[4][2],draws[4][3]));count+=1
    assert targets=={(w,h) for w,h in patterns[40] if 49<=w<=79}
    assert fronts=={(a,w,h) for a in (39,40,41) for w,h in patterns[a] if w>=64}
    assert centers=={40,41,128,129,216,217,16,250} and tops=={-20,0,30,55,120,180,191}
    return dict(fixturePresents=count,targetGeometries=len(targets),frontGeometries=len(fronts),centers=len(centers),tops=len(tops),
        everyListedComponentCovered=True,fullCartesianProductClaimed=False)


def verify_flame_fixture_coverage(dest):
    from sa1_patterns import dimensions
    patterns=dimensions();actual=set()
    for path in dest.glob('present*_meta.bin'):
        raw=path.read_bytes();count=struct.unpack_from('<H',raw,6)[0]
        for i in range(count):
            x,b,w,h,a,flags,*_=struct.unpack_from('<hh6B',raw,10+i*10)
            if a==31:actual.add((w,h,x,b,flags))
    expected={(w,h,x,b,phase) for w,h in patterns[31] if w>=64 for x in (-40,0,16,30,64,128,250) for b in (40,120,205) for phase in range(3)}
    assert actual==expected,(len(expected-actual),len(actual-expected))
    return dict(cases=len(actual),fullCartesianProductVerified=True)


def verify_direct_left_fixture_coverage(dest):
    from sa1_patterns import dimensions
    patterns=dimensions();actual=set()
    for path in dest.glob('present*_meta.bin'):
        if path.name=='present00001_meta.bin':continue  # 通常の初回画面も画素照合するがfixture集合には含めない。
        raw=path.read_bytes();count=struct.unpack_from('<H',raw,6)[0]
        if count!=2:continue
        for i in range(count):
            x,b,w,h,a,flags,*_=struct.unpack_from('<hh6B',raw,10+i*10)
            assert a in (0,2,3,5) and flags==0
            actual.add((a,w,h,x,b-h-20))
    expected={(a,w,h,x,top) for a in (0,2,3,5) for w,h in patterns[a] if w>=64
        for x in (-40,-39,0,1,16,17,30,31,64,65,128,129,250,251) for top in (-20,30,180)}
    assert actual==expected,(len(expected-actual),len(actual-expected))
    return dict(cases=len(actual),fullCartesianProductVerified=True)

def verify_minimum_clip_coverage(dest,config):
    """表示済みmetaから対象寸法・左右位置・上下位置の全組合せを確認する。"""
    from sa1_patterns import dimensions
    patterns=dimensions()
    geometries=sorted(g for g in set(patterns[40])&set(patterns[41]) if g[0]==config['reverseExplosionsMinWidth'])
    centers=(0,47,48,49,128,182,222,265,266,267,268,286,300)
    tops=(-20,0,30,55,56,120,180)
    expected={(asset,w,h,x,top) for asset in (40,41) for w,h in geometries for x in centers for top in tops}
    actual=set()
    for path in dest.glob('present*_meta.bin'):
        raw=path.read_bytes();count=struct.unpack_from('<H',raw,6)[0]
        for i in range(count):
            x,bottom,w,h,asset,flags,z,priority=struct.unpack_from('<hh6B',raw,10+i*10)
            if asset in (40,41):
                assert flags==0
                actual.add((asset,w,h,x,bottom-h-20))
    assert actual==expected, f'minimum clipping coverage missing={len(expected-actual)} extra={len(actual-expected)}'
    return dict(cases=len(actual),geometries=geometries,assets=[40,41],centers=len(centers),tops=len(tops))

def verify_pixels(dest,labels,config):
    source=(BASE/'assets4/background4.bin').read_bytes()
    checked=0
    for path in sorted(dest.glob('present*_meta.bin')):
        prefix=path.name[:-9]
        raw=path.read_bytes();far,near,ground,count,page=struct.unpack_from('<5H',raw)
        draws=[list(struct.unpack_from('<hh6B',raw,10+i*10)) for i in range(count)]
        sprite=np.frombuffer(reference({'draws':draws}),dtype=np.uint8).reshape(192,128)
        sprite=np.stack((sprite&15,sprite>>4),axis=2).reshape(192,256)
        pix=np.zeros((192,256),dtype=np.uint8)
        if config.get('nativeNear'):
            fine=near&7;left=(112-fine)&~3;right=(163-fine)&~3
            layer=np.frombuffer(source[0x8000:0x8000+9*512],np.uint8).reshape(9,512)[:,(np.arange(256)+near)&511]
            top=82+ground;y0=max(0,top);y1=min(192,top+9)
            if y0<y1:pix[y0:y1,left:right]=layer[y0-top:y1-top,left:right]
        for offset,scroll,top,height in ((0,far,77+ground,14),(0x8000,near,82+ground,9)):
            if config.get('nativeBackground') or (config.get('nativeFar') and offset==0):continue
            layer=np.frombuffer(source[offset:offset+height*512],dtype=np.uint8).reshape(height,512)[:,(np.arange(256)+scroll)&511]
            y0=max(0,top);y1=min(192,top+height)
            if y0<y1:
                p=layer[y0-top:y1-top];d=pix[y0:y1];d[p!=0]=p[p!=0]
        pix[sprite!=0]=sprite[sprite!=0]
        expected=(pix[:,::2]|pix[:,1::2]<<4).tobytes()
        actual=(dest/(prefix+'_fb.bin')).read_bytes()
        if actual!=expected:
            (dest/(prefix+'_expected.bin')).write_bytes(expected)
            raise AssertionError(f'{prefix}: framebuffer {sum(a!=b for a,b in zip(actual,expected))} bytes differ')
        tiles=pix.reshape(24,8,32,8).transpose(0,2,1,3).reshape(768,8,8)
        planar=np.zeros((768,32),dtype=np.uint8)
        for plane in range(4):planar[:,plane//2*16+plane%2+np.arange(8)*2]=(((tiles>>plane)&1)*np.array([128,64,32,16,8,4,2,1])).sum(axis=2)
        vram=(dest/(prefix+'_vram.bin')).read_bytes()[page*2:page*2+24576]
        state_path=dest/(prefix+'_ppu.json')
        ppu_state=json.loads(state_path.read_text()) if state_path.exists() else None
        start=1024 if config.get('visibleMask') else 0
        if (config.get('denseTiles') or config.get('cpuPack') or config.get('directSparse')):
            whole=(dest/(prefix+'_vram.bin')).read_bytes()
            converted=bytearray()
            for tile in range(32,768):
                map_base=page*2+0x2800 if config.get('vramFourOwned') else 0xc000 if config.get('fixedMap') else 0xc000 if config.get('vramFourShared') else page*2+0x800 if config.get('vramPrefetch3') else 0xc000
                entry=struct.unpack_from('<H',whole,map_base+tile*2)[0]
                assert entry&0xfc00==0x2400,f'{prefix}: dense tile attributes differ'
                address=((ppu_state['bg1Chr'] if ppu_state else page*2)+(entry&1023)*32)&65535
                converted+=whole[address:address+32]
            assert converted==planar.tobytes()[1024:],f'{prefix}: dense converted visible VRAM differs'
        else:
            assert vram[start:]==planar.tobytes()[start:],f'{prefix}: converted visible VRAM differs'
        if config.get('nativeFar'):
            from sa1_native_far import decode
            whole=(dest/(prefix+'_vram.bin')).read_bytes()
            width=256 if config.get('nativeBackground') and not config.get('nativeNear') else 512
            bg=np.zeros((16,width),dtype=np.uint8)
            for row in range(2):
                for col in range(width//8):
                    address=(0xc000 if config.get('fixedMap') else 0xc000)+(col//32)*0x800+(24+row)*64+(col%32)*2
                    entry=struct.unpack_from('<H',whole,address)[0]
                    tile=(ppu_state['bg2Chr'] if ppu_state else 0xa000 if config.get('fixedMap') else 0x8000 if config.get('vramFourShared') else 0 if config.get('nativeNear') else 0xc000)+(entry&1023)*32
                    a=decode(whole[tile:tile+32],4)
                    if entry&0x4000:a=a[:,::-1]
                    if entry&0x8000:a=a[::-1]
                    bg[row*8:row*8+8,col*8:col*8+8]=a
            bg_reference=np.zeros((16,width),dtype=np.uint8)
            indices=(np.arange(width)+(far if config.get('nativeBackground') and not config.get('nativeNear') else 0))&511
            bg_reference[:14]=np.frombuffer(source[:14*512],dtype=np.uint8).reshape(14,512)[:,indices]
            if config.get('nativeBackground') and not config.get('nativeNear'):
                near_pixels=np.frombuffer(source[0x8000:0x8000+9*512],dtype=np.uint8).reshape(9,512)[:,(np.arange(width)+near)&511]
                region=bg_reference[5:14];region[near_pixels!=0]=near_pixels[near_pixels!=0]
            assert np.array_equal(bg,bg_reference),f'{prefix}: BG2 converted pixels differ'
            initial=(BUILD/'ppu_sa1.bin').read_bytes()
            ground_end=int(json.loads((BUILD/'native_far_packing.json').read_text())['groundEnd'],16)
            assert whole[0xd000:ground_end]==initial[0xd000:ground_end],f'{prefix}: ground CHR overwritten'
            assert whole[0xf000:]==initial[0xf000:],f'{prefix}: ground map overwritten'
            if config.get('nativeNear'):
                from sa1_native_near import verify
                verify(dest/(prefix+'_oam.bin'),whole,source,near,ground,pix,sprite)
                packing=json.loads((BUILD/'native_near_packing.json').read_text())
                for address in packing['farChrAddresses']+packing['nearChrAddresses']:
                    assert whole[address:address+32]==initial[address:address+32],f'{prefix}: static background CHR overwritten'
                palette_path=dest/(prefix+'_palette.bin')
                if palette_path.exists():
                    palette=palette_path.read_bytes()
                    assert palette[480:512]==palette[32:64]==(BASE/'assets4/palette4.bin').read_bytes(),f'{prefix}: near OBJ palette changed'
            if config.get('compiledGround'):
                from build_sa1_game import GAME
                record=(dest/(prefix+'_record.bin')).read_bytes()
                height=struct.unpack_from('<H',record,14)[0]
                phase=struct.unpack_from('<H',record,58)[0]&127
                assets=GAME/'assets'
                run_offsets=struct.unpack('<65H',(assets/'ground_horizontal_run_offsets.bin').read_bytes())
                value_offsets=struct.unpack('<128H',(assets/'ground_horizontal_offsets.bin').read_bytes())
                runs=(assets/'ground_horizontal_runs.bin').read_bytes();values=(assets/'ground_horizontal.bin').read_bytes()
                horizon=104+height;headers=(127,horizon-127) if horizon>=128 else (horizon,)
                expected_ground=bytearray()
                for length in headers:expected_ground+=bytes((length,128,0))
                position=run_offsets[height]
                while runs[position]:
                    length,index=runs[position:position+2]
                    expected_ground+=bytes((length,values[value_offsets[phase]+index],0));position+=2
                expected_ground+=b'\x00'
                actual_ground=(dest/(prefix+'_ground_h.bin')).read_bytes()
                assert actual_ground[:len(expected_ground)]==expected_ground,f'{prefix}: horizontal ground HDMA differs'
        checked+=1
    return checked

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--frames',type=int,default=600);ap.add_argument('--scenario',default='play');ap.add_argument('--presents',type=int,default=0);ap.add_argument('--timeout',type=int,default=180);ap.add_argument('--split-fixture-source',type=Path);args=ap.parse_args()
    assert bool(args.split_fixture_source)==args.scenario.startswith('splitfixture')
    split_jobs=[]
    if args.split_fixture_source:
        from sa1_split_fixture import load
        split_jobs,split_sources=load(args.split_fixture_source)
    dest=BUILD/args.scenario;dest.mkdir(exist_ok=True)
    (dest/'failure.txt').unlink(missing_ok=True)
    (dest/'summary.json').unlink(missing_ok=True)
    for path in dest.glob('present*'):path.unlink()
    for path in dest.glob('frame*'):
        if re.fullmatch(r'frame\d+\.(png|rgb)',path.name):path.unlink()
    labels={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.([^\s]+)',(BUILD/'game.lbl').read_text())}
    config=json.loads((BUILD/'manifest.json').read_text())
    if split_jobs:(dest/'split_fixture_source.json').write_text(json.dumps(dict(source=str(args.split_fixture_source),sources=split_sources,jobs=split_jobs),indent=2)+'\n')
    (dest/'manifest.json').write_text(json.dumps(config,indent=2)+'\n')
    (dest/'game.lbl').write_bytes((BUILD/'game.lbl').read_bytes())
    assert hashlib.sha256((BUILD/'MonoSHSA1_4bpp_game.sfc').read_bytes()).hexdigest()==config['romSha256']
    rom=(BUILD/'MonoSHSA1_4bpp_game.sfc').read_bytes()
    if config.get('dmaBudgetTable'):
        from sa1_left_hints import physical
        assert 'blank_table' in labels and labels['blank_table']<labels['__CODE_SIZE__']<=65536
        table=physical(0xc10000+labels['blank_table'])
        assert rom[table:table+13]==bytes([21,128,1,0,127,15,53,15,22,128,1,128,0]),'blank HDMA table left S-CPU CODE'
    frame_module='frame_game_rom.o' if config.get('sa1Game') else 'frame_asm.o'
    frame_size=int(re.search(re.escape(frame_module)+r':\s+CODE\s+Offs=[0-9A-F]+\s+Size=([0-9A-F]+)',(BUILD/'game.map').read_text())[1],16)
    frame_start=labels['_fx_frame'];frame_code=rom[0x410000+frame_start:0x410000+frame_start+frame_size]
    calls={}
    for name in ('_fx_read_input','_monosh_combat_fast_frame','_monosh_combat_render','_monosh_enemy_frame','_monosh_stage_frame','_monosh_boss_frame','_monosh_boss_prepare_render','_monosh_boss_render_only','_fx_build_packet','_fx_build_ground'):
        needle=b'\x20'+struct.pack('<H',labels[name])
        calls[name]=[frame_start+i for i in range(len(frame_code)-2) if frame_code[i:i+3]==needle]
    script='''local labels=LABELS
local output=OUTDIR
local maxframe=MAXFRAME
local targetPresents=TARGETPRESENTS
local scenario=SCENARIO
local exactMaskBounds=EXACTMASKBOUNDS
local splitFixtures=SPLITFIXTURES
local function captureGeneration(g)
 return scenario:match('^transferfixture') or scenario:match('^splitfixture') or scenario:match('^opaquefixture') or scenario:match('^clipfixture') or scenario:match('^stackfixture') or scenario:match('^leftfixtureindexed') or scenario:match('^leftfixtureexplosion') or scenario:match('^leftfixtureflame') or g<=120 or g%60==0 or (scenario:match('captureburst') and g>=530 and g<=570)
end
local padded=PADDED
local pipeline=PIPELINE
local vramPrefetch3=VRAMPREFETCH3
local vramFourShared=VRAMFOURSHARED
local vramFifo=VRAMFIFO
local vramFourOwned=VRAMFOUROWNED
local fixedMap=FIXEDMAP
local prebankDma=PREBANKDMA
local dmaShortIo=DMASHORTIO
local prefixRefreshSixteenth=PREFIXREFRESHSIXTEENTH
local splitViewports=SPLITVIEWPORTS
local fixedMapDelta=FIXEDMAPDELTA
local fixedMapDeltaDma=FIXEDMAPDELTADMA
local packetOffload=PACKETOFFLOAD
local packetIramArrays=PACKETIRAMARRAYS
local packetRunning=false
local cpuCodeBase=CPUCODEBASE
local field,logic,presents=0,0,0
local finishedCapture=false
local begin,sa1begin,drawbegin=0,0,0
local flipBegin=0
local dirtyDone,clearDone,nativeDone=0,0,0
local dirtyMs,clearMs,bgMs,nativeMs,logicMs=0,0,0,0,0
local times={}
local presentationTimes={}
local pageCommit=nil
local readyLine,startClock,waitMs=0,0,0
local cpuParts,cpuEntries={},{}
local cpuActiveParts,cpuActiveEntries={},{}
local irqTicks,irqClock,irqDepth=0,0,0
local requestLine,prearmLine=TRANSFERREQUESTLINE,PREARMTRANSFERLINE
local configuredRequestLine=nil
local requestLog=(requestLine~=197 or prearmLine>0) and assert(io.open(output..'/transfer_request_verified.jsonl','w')) or nil
if requestLog then
 emu.addMemoryCallback(function(address,value)
  if value~=requestLine and value~=prearmLine and value~=197 then
   local f=assert(io.open(output..'/failure.txt','w'));f:write('unexpected transfer IRQ line '..value);f:close();emu.stop(1)
  end
  configuredRequestLine=value
  local s=emu.getState();requestLog:write(string.format('{"event":"configure","field":%d,"line":%d,"value":%d}\\n',field,s['ppu.scanline'],value));requestLog:flush()
 end,emu.callbackType.write,0x4209,0x4209,emu.cpuType.snes,emu.memType.snesMemory)
end
local activeBegin=0
local function activeClock()local c=emu.getState().masterClock;return c-irqTicks-(irqClock>0 and c-irqClock or 0)end
local cpuJobs={}
local sortReference=nil
local packetTrace=assert(io.open(output..'/packet_trace.bin','wb'))
local gameAudit=scenario:match('auditgame') and assert(io.open(output..'/game_state_audit.jsonl','w')) or nil
local boundsFrames=scenario:match('tracebounds') and assert(io.open(output..'/mask_bounds_frames.bin','wb')) or nil
local completedFrames={}
local expectedPalette=EXPECTEDPALETTE
if scenario:match('tracepalette') then
 local z=assert(io.open(output..'/palette_writes.jsonl','w'))
 emu.addMemoryCallback(function(address,value)
  if field>90 then
   local s=emu.getState()
   z:write(string.format('{"field":%d,"line":%d,"hclock":%d,"address":%d,"value":%d,"cgadd":%d,"pc":%d}\\n',field,s['ppu.scanline'],s['memoryManager.hClock'],address,value,s['ppu.cgramAddress'],s['cpu.pc']));z:flush()
  end
 end,emu.callbackType.write,32,63,emu.cpuType.snes,emu.memType.snesCgRam)
end
if scenario:match('tracedma') then
 local z=assert(io.open(output..'/sa1_dma_writes.jsonl','w'))
 local blankLog=assert(io.open(output..'/blank_writes.jsonl','w'))
 emu.addMemoryCallback(function(address,value)
  local st=emu.getState()
  blankLog:write(string.format('{"field":%d,"line":%d,"value":%d,"pc":%d,"hdmaAddress":%d,"hdmaCount":%d}\\n',field,st['ppu.scanline'],value,st['cpu.pc'],st['dmaController.channel[1].hdmaTableAddress'],st['dmaController.channel[1].hdmaLineCounterAndRepeat']));blankLog:flush()
 end,emu.callbackType.write,0x2100,0x2100,emu.cpuType.snes,emu.memType.snesMemory)
 local reads=assert(io.open(output..'/cpu_dma_reads.jsonl','w'));local readCount=0
 emu.addMemoryCallback(function(address,value)
  if presents==0 and emu.read16(0x311e,emu.memType.snesMemory)==1 and readCount<800 then
   readCount=readCount+1;local s=emu.getState()
   reads:write(string.format('{"address":%d,"value":%d,"source":%d,"dest":%d,"active":%s,"blank":%s,"line":%d}\\n',address,value,s['cart.coprocessor.dmaSrcAddr'],s['cart.coprocessor.dmaDestAddr'],tostring(s['cart.coprocessor.charConvDmaActive']),tostring(s['ppu.forcedBlank']),s['ppu.scanline']));reads:flush()
  end
 end,emu.callbackType.read,0x400000,0x43ffff,emu.cpuType.snes,emu.memType.snesMemory)
 emu.addMemoryCallback(function(address,value)
  if emu.read16(0x11e,emu.memType.sa1Memory)==1 then
   local s=emu.getState()
   z:write(string.format('{"gen":%d,"address":%d,"value":%d,"pc":%d}\\n',emu.read16(0x198,emu.memType.sa1Memory),address,value,(s['cart.coprocessor.cpu.k'] or 0)*65536+(s['cart.coprocessor.cpu.pc'] or 0)));z:flush()
  end
 end,emu.callbackType.write,0x2230,0x2239,emu.cpuType.sa1,emu.memType.sa1Memory)
end
if scenario:match('tracezero') then
 local z=assert(io.open(output..'/rowzero.jsonl','w'))
 emu.addMemoryCallback(function(address,value)
  local s=emu.getState();local m=emu.memType.sa1Memory
  z:write(string.format('{"gen":%d,"address":%d,"value":%d,"pc":%d}\\n',emu.read16(0x198,m),address,value,(s['cart.coprocessor.cpu.k'] or 0)*65536+(s['cart.coprocessor.cpu.pc'] or 0)));z:flush()
 end,emu.callbackType.write,0x420000,0x42007f,emu.cpuType.sa1,emu.memType.sa1Memory)
end
local completedPackets={}
local jobSequence=0
local outputJobs={}
local cpuStageJobs={}
local queueSamples={}
local objectJobs={}
local dmaJobs={}
local dmaClock,dmaLength,dmaLine=0,0,0
local objectBegin=0
local function word(name,value)
 emu.write16(0x7e0000+labels[name],value,emu.memType.snesMemory)
 if GAMEOFFLOAD and name:match('^_monosh') then emu.write16(GAMEBWBASE+labels[name],value,emu.memType.snesMemory)end
end
for name,sites in pairs(CALLS)do
 for _,site in ipairs(sites)do
  emu.addMemoryCallback(function()cpuEntries[name]=emu.getState().masterClock;cpuActiveEntries[name]=activeClock() end,emu.callbackType.exec,cpuCodeBase+site,cpuCodeBase+site)
  emu.addMemoryCallback(function()
   cpuParts[name]=(cpuParts[name] or 0)+(emu.getState().masterClock-cpuEntries[name])/21477.272
   cpuActiveParts[name]=(cpuActiveParts[name] or 0)+(activeClock()-cpuActiveEntries[name])/21477.272
   if name=='_fx_read_input' and scenario:match('detinput') then
    local phase=logic%240
    local value=0x80
    if scenario:match('move') then
     value=value+(phase<60 and 0x100 or phase<120 and 0x800 or phase<180 and 0x200 or 0x400)
    end
    emu.write16(0x7e0000+labels._fx_buttons,value,emu.memType.snesMemory)
   end
  end,emu.callbackType.exec,cpuCodeBase+site+3,cpuCodeBase+site+3)
 end
end
local function byte(name,value)
 emu.write(0x7e0000+labels[name],value,emu.memType.snesMemory)
 if GAMEOFFLOAD and name:match('^_monosh') then emu.write(GAMEBWBASE+labels[name],value,emu.memType.snesMemory)end
end
local function cb(name,fn,cpu)
 cpu=cpu or emu.cpuType.snes
 local gameHook=GAMEOFFLOAD and (name=='_fx_build_packet' or name=='initialized' or name=='sorted' or name=='packet_done' or name=='sa1_list_sort')
 local packetHook=packetOffload and (name=='initialized' or name=='sorted' or name=='packet_done' or name=='sa1_list_sort')
 if gameHook or packetHook then cpu=emu.cpuType.sa1 end
 if packetHook then local run=fn;fn=function()if packetRunning then run()end end end
 local irqName=name:match('^pipe_') or name=='p3PumpBlank' or name=='p3Complete' or name=='p3Flip' or name=='stage_time_ok' or name=='stage_converted' or name=='stage_too_large' or name=='fx_obj_upload_done' or name=='dma_started' or name=='dma_finished' or name=='half_dma_finished' or name=='prefetch_finished' or name=='transfer_chunk' or name=='dma_chunk_ready'
 local a=labels[name]+(packetHook and 0 or gameHook and 0xc10000 or cpu==emu.cpuType.snes and labels[name]<65536 and (irqName and IRQCODEBASE or cpuCodeBase) or 0)
 emu.addMemoryCallback(function()if finishedCapture then return end;local ok,err=pcall(fn);if not ok then finishedCapture=true;local f=assert(io.open(output..'/failure.txt','w'));f:write(tostring(err));f:close();local g=assert(io.open(output..'/failure_state.txt','w'));for k,v in pairs(emu.getState())do g:write(tostring(k)..'='..tostring(v)..'\\n')end;g:close();emu.stop(1)end end,emu.callbackType.exec,a,a,cpu,cpu==emu.cpuType.snes and emu.memType.snesMemory or emu.memType.sa1Memory)
end
if prearmLine>0 then
 local function check(event,phase,nextLine)
  local s=emu.getState();local m=emu.memType.snesMemory;local line=s['ppu.scanline']
  assert(irqDepth>0 and emu.read16(0x7e0000+labels.pipe_prearm_phase,m)==phase,'prearm phase/IRQ mismatch')
  assert(configuredRequestLine==nextLine and emu.read16(0x311e,m)==1,'prearm lost request or next IRQ')
  if event=='issued' then assert(line>=prearmLine and line<197,'prearm issued too late')else assert(line>=197,'prearm transfer too early')end
  requestLog:write(string.format('{"event":"%s","field":%d,"line":%d,"grant":%d}\\n',event,field,line,emu.read16(0x311c,m)));requestLog:flush()
 end
 cb('pipe_prearm_issued',function()check('issued',1,197)end)
 cb('pipe_prearm_transfer',function()check('transfer',0,prearmLine)end)
 cb('pipe_prearm_late',function()check('late',0,prearmLine)end)
end
if scenario:match('tracedmacost') then
 local first,last=labels.pipe_fast_unroll_start,labels.pipe_fast_unroll_end
 local count=DMAUNROLLCOUNT;local stride=(last-first)//count
 assert(DMAWORDSTART and (stride==26 or stride==23),'DMA timing trace requires verified word-start block')
 local f=assert(io.open(output..'/dma_cost_verified.jsonl','w'));local pending=nil
 for i=0,count-1 do
  local name='pipe_dma_cost_start_'..i;labels[name]=IRQCODEBASE+first+i*stride+stride-2
  cb(name,function()
   if field<660 or field>720 then return end
   assert(not pending,'overlapping DMA timing samples')
   local s=emu.getState();local m=emu.memType.snesMemory
   assert(s['cpu.d']==0x4200 and emu.read(0x4301,m)==0x18,'DMA timing mode mismatch')
   local r=0x7e0000+labels.pipe_records+emu.read16(0x7e0000+labels.pipe_record_offset,m)
   pending={clock=s.masterClock,field=field,line=s['ppu.scanline'],hclock=s['memoryManager.hClock'],bytes=emu.read16(0x4305,m),source=emu.read16(0x4302,m)+emu.read(0x4304,m)*65536,generation=emu.read16(r+8,m)}
  end)
  local after=i==count-1 and last+3 or first+(i+1)*stride+(stride==23 and 4 or 3)
  name='pipe_dma_cost_end_'..i;labels[name]=IRQCODEBASE+after
  cb(name,function()
   if not pending then return end
   local s=emu.getState();local ticks=s.masterClock-pending.clock
   assert(ticks>=pending.bytes*8,'DMA sample ended before transfer')
   f:write(string.format('{"clock":%d,"generation":%d,"field":%d,"line":%d,"hclock":%d,"endLine":%d,"bytes":%d,"source":%d,"elapsedTicks":%d,"extraTicks":%d}\\n',pending.clock,pending.generation,pending.field,pending.line,pending.hclock,s['ppu.scanline'],pending.bytes,pending.source,ticks,ticks-pending.bytes*8));f:flush();pending=nil
  end)
 end
end
if labels.pipe_collect_skipped then
 local f=assert(io.open(output..'/collect_scheduling.jsonl','w'))
 local lastClock,lastGeneration=0,0
 local function log(event,gen,duration)
  local s=emu.getState();local m=emu.memType.snesMemory;local b=0x7e0000
  local target=emu.read16(b+labels.pipe_target_slot,m);local read=emu.read16(b+labels.pipe_read_slot,m)
  f:write(string.format('{"event":"%s","generation":%d,"field":%d,"line":%d,"irq":%d,"target":%d,"readStatus":%d,"pending":%d,"done":%d,"durationMs":%.6f}\\n',event,gen,field,s['ppu.scanline'],irqDepth>0 and 1 or 0,target,emu.read16(b+labels.pipe_status+read*2,m),emu.read16(b+labels.pipe_pending,m),emu.read16(0x3104,m),duration));f:flush()
 end
 cb('pipe_collect_skipped',function()
  local m=emu.memType.snesMemory;local b=0x7e0000
  local target=emu.read16(b+labels.pipe_target_slot,m);local read=emu.read16(b+labels.pipe_read_slot,m)
  assert(irqDepth>0 and (target~=65535 or emu.read16(b+labels.pipe_status+read*2,m)==2),'collect skipped without transfer candidate')
  log('skipped',0,0)
 end)
 cb('pipe_collect_urgent',function()
  local m=emu.memType.snesMemory;local b=0x7e0000;local read=emu.read16(b+labels.pipe_read_slot,m)
  assert(irqDepth>0 and emu.read16(b+labels.pipe_target_slot,m)==65535 and emu.read16(b+labels.pipe_status+read*2,m)~=2,'urgent collect had a transfer candidate')
  log('urgent',0,0)
 end)
 local function begin()lastClock=emu.getState().masterClock end
 local function publish()
  local m=emu.memType.snesMemory;local b=0x7e0000;local slot=emu.read16(b+labels.pipe_render_slot,m)
  local gen=emu.read16(b+labels.pipe_records+slot*512+8,m)
  assert(gen==lastGeneration+1,'collect scheduling skipped or duplicated a generation')
  assert(emu.read16(b+labels.pipe_pending,m)==1 and emu.read16(0x3104,m)==1,'collect published without pending completion')
  assert(emu.read16(0x3198,m)==gen,'collect published another SA-1 generation')
  log('publish',gen,(emu.getState().masterClock-lastClock)/21477.272);lastGeneration=gen
 end
 cb('pipe_collect',begin);cb('pipe_collect_main',begin)
 cb('pipe_collect_publish',publish);cb('pipe_collect_main_publish',publish)
end
if labels.fp_probe_begin then
 local f=assert(io.open(output..'/fixed_front_probe.jsonl','w'))
 local sample=FRONTPROBEGEN
 local history={[0]={}};for i=0,95 do history[0][i]=0 end
 if sample>0 then
  cb('sa1_occupancy_capture',function()
   local gen=emu.read16(0x198,emu.memType.sa1Memory);local m={}
   for i=0,95 do m[i]=emu.read(0x432800+i,emu.memType.sa1Memory)end
   history[gen]=m
  end,emu.cpuType.sa1)
 end
 local begin,masksClock,readyClock,entry,result=nil,0,0,nil,nil
 local previous={};for i=0,95 do previous[i]=0 end
 local current=nil;local lastGeneration=0
 cb('fp_probe_begin',function()
  local s=emu.getState();assert(not begin,'nested front probe')
  begin=s.masterClock;entry={a=s['cpu.a'],x=s['cpu.x'],y=s['cpu.y'],d=s['cpu.d'],db=s['cpu.dbr'],sp=s['cpu.sp'],line=s['ppu.scanline'],irq=irqDepth>0 and 1 or 0}
 end)
 cb('fp_probe_masks',function()
  local mt=emu.memType.snesMemory;local b=0x7e0000
  assert(begin,'front masks before begin');masksClock=emu.getState().masterClock
  local gen=emu.read16(labels.fp_generation,mt)
  if sample>0 then
   assert(gen==sample and history[gen] and history[gen-1],'front sample lacks mask history')
   previous=history[gen-1]
  else assert(gen==lastGeneration+1,'front probe skipped or repeated a generation')end
  current={}
  for i=0,95 do
   current[i]=emu.read(b+labels.fp_current+i,mt)
   if sample>0 then assert(current[i]==history[gen][i],'front sample differs from occupancy capture')end
   assert(current[i]==emu.read(0x432800+i,mt),string.format('front probe copied wrong current mask: gen=%d offset=%d got=%d expected=%d dma=%s',gen,i,current[i],emu.read(0x432800+i,mt),tostring(emu.getState()['dmaController.channel[0].dmaActive'])))
   assert(emu.read(b+labels.fp_previous+i,mt)==previous[i],'front probe previous mask changed')
  end
 end)
 cb('fp_probe_ready',function()
  local mt=emu.memType.snesMemory;local b=0x7e0000;local gap=1;local runs
  assert(begin and current,'front probe ready before mask copy')
  readyClock=emu.getState().masterClock
  repeat
   runs={}
   for tile=32,767 do
    if ((current[tile//8]|previous[tile//8])>>(tile%8))&1~=0 then
     local start=tile*32;local finish=start+32
     if #runs>0 and start-runs[#runs][2]<gap then runs[#runs][2]=finish
     else runs[#runs+1]={start,finish}end
    end
   end
   if #runs>48 then gap=gap+64 end
  until #runs<=48
  assert(emu.read16(labels.fp_count,mt)==#runs and emu.read16(labels.fp_gap,mt)==gap,'front probe run count/gap differs')
  local bytes,cost=0,0;local base=emu.read16(labels.fp_source_base,mt)
  for i,r in ipairs(runs)do
   local length=r[2]-r[1];local a=b+labels.fp_descriptors+(i-1)*6
   assert(emu.read16(a,mt)==length and emu.read16(a+2,mt)==r[1]+base and emu.read16(a+4,mt)==r[1]//2-496,'front probe descriptor differs')
   bytes=bytes+length;cost=cost+length+length//32+length//128+57
   local p=b+labels.fp_prefix+(i-1)*4
   assert(emu.read16(p,mt)==bytes and emu.read16(p+2,mt)==cost,'front probe cumulative prefix differs')
  end
  assert(emu.read16(labels.fp_bytes,mt)==bytes and emu.read16(labels.fp_cost,mt)==cost,'front probe totals differ')
  result={gen=emu.read16(labels.fp_generation,mt),bytes=bytes,cost=cost,count=#runs,gap=gap}
 end)
 cb('fp_probe_return',function()
  local s=emu.getState();assert(begin and result,'front probe returned before verification')
  assert(s['cpu.a']==entry.a and s['cpu.x']==entry.x and s['cpu.y']==entry.y and s['cpu.d']==entry.d and s['cpu.dbr']==entry.db and s['cpu.sp']==entry.sp,'front probe did not restore CPU registers/stack')
  local mt=emu.memType.snesMemory
  for i=0,95 do assert(emu.read(0x7e0000+labels.fp_previous+i,mt)==current[i],'front probe did not remember current mask')end
  f:write(string.format('{"generation":%d,"field":%d,"irq":%d,"bytes":%d,"cost":%d,"count":%d,"gap":%d,"beginLine":%d,"endLine":%d,"totalMs":%.6f,"copyMs":%.6f,"planningMs":%.6f,"rememberMs":%.6f}\\n',result.gen,field,entry.irq,result.bytes,result.cost,result.count,result.gap,entry.line,s['ppu.scanline'],(s.masterClock-begin)/21477.272,(masksClock-begin)/21477.272,(readyClock-masksClock)/21477.272,(s.masterClock-readyClock)/21477.272));f:flush()
  if sample>0 then finishedCapture=true;emu.stop(0)end
  previous=current;current=nil;lastGeneration=result.gen;result=nil;begin=nil
 end)
end
if scenario:match('tracebounds') then
 local f=assert(io.open(output..'/mask_bounds_trace.bin','wb'))
 cb('sa1_occupancy_capture',function()
  local mt=emu.memType.sa1Memory
  local data={}
  local function append16(v)data[#data+1]=string.char(v%256,math.floor(v/256)%256)end
  append16(emu.read16(0x198,mt))
  for i=0,95 do data[#data+1]=string.char(emu.read(0x432800+i,mt))end
  for band=0,23 do
   local first,last=128,0
   for bit=0,31 do
    local b=emu.read(0x432800+band*4+math.floor(bit/8),mt)
    if math.floor(b/2^(bit%8))%2==1 then first=math.min(first,bit*4);last=(bit+1)*4 end
   end
   local left=emu.read16(0x120+band*4,mt);local right=emu.read16(0x122+band*4,mt)
   local exact=left==first and right==last
   assert(exact or (not exactMaskBounds and ((last==0 and left>=right) or (last>0 and left<=first and right>=last))),string.format('mask bounds job %d band %d: %d..%d expected %d..%d',emu.read16(0x198,mt),band,left,right,first,last))
   append16(left);append16(right)
  end
  f:write(table.concat(data));f:flush()
 end,emu.cpuType.sa1)
end
if scenario:match('traceedge') then
 local f=assert(io.open(output..'/edge_cache.jsonl','w'))
 local current=nil;local begin=0;local restoreBegin=0;local saved=0
 cb('sa1_edge_save',function()
  local mt=emu.memType.sa1Memory
  begin=emu.getState().masterClock;current=nil
  local width=emu.read16(0xc4,mt)
  if width>0 then
   local function s16(v)return v>=32768 and v-65536 or v end
   current={job=emu.read16(0x198,mt),field=field,asset=emu.read16(0x3e,mt),width=emu.read16(0x34,mt),height=emu.read16(0x36,mt),left=s16(emu.read16(0x38,mt)),top=s16(emu.read16(0x3a,mt)),flags=emu.read16(0x3c,mt),first=emu.read16(0xa0,mt),count=emu.read16(0xa8,mt),cacheWidth=width,saveConversionBusy=emu.read16(0x11e,mt)}
  end
 end,emu.cpuType.sa1)
 cb('edge_save_completed',function()
  if current then
   local mt=emu.memType.sa1Memory
   saved=emu.getState().masterClock;current.saveMs=(saved-begin)/21477.272
   current.cacheRows=emu.read16(0xca,mt);current.cacheFirst=emu.read16(0xc8,mt);current.cacheBytes=current.cacheWidth*current.cacheRows
   assert(current.cacheBytes<=1024,'edge guard exceeds IRAM cache')
   if current.cacheWidth<=EDGEJITMAX then assert(current.cacheBytes<=512,'edge guard overwrites small JIT')end
  end
 end,emu.cpuType.sa1)
 cb('sa1_edge_restore',function()restoreBegin=emu.getState().masterClock;if current then current.restoreConversionBusy=emu.read16(0x11e,emu.memType.sa1Memory)end end,emu.cpuType.sa1)
 for _,kind in ipairs({'save','restore'})do
  for name,mode in pairs({sa1_small_edge_='jit',sa1_edge_cpu_='mvn'})do
   cb(name..kind,function()if current then current[kind..'Mode']=mode end end,emu.cpuType.sa1)
  end
 end
 cb('edge_restore_completed',function()
  if current then
   current.restoreMs=(emu.getState().masterClock-restoreBegin)/21477.272
   current.chunkDrawAndCodeMs=(restoreBegin-saved)/21477.272
   local parts={};for k,v in pairs(current)do parts[#parts+1]=string.format('"%s":%s',k,type(v)=='string' and string.format('%q',v) or tostring(v))end
   f:write('{',table.concat(parts,','),'}\\n');f:flush();current=nil
  end
 end,emu.cpuType.sa1)
 if labels.sa1_small_edge_load then
  local jit=assert(io.open(output..'/edge_jit.jsonl','w'))
  local start=0;local cpu=false
  cb('sa1_small_edge_load',function()start=emu.getState().masterClock;cpu=false end,emu.cpuType.sa1)
  cb('small_prepare_cpu',function()cpu=true end,emu.cpuType.sa1)
  cb('small_prepare_done',function()
   if start>0 then
    local mt=emu.memType.sa1Memory
    jit:write(string.format('{"job":%d,"asset":%d,"cacheWidth":%d,"cpuCopy":%s,"ms":%.6f}\\n',emu.read16(0x198,mt),emu.read16(0x3e,mt),emu.read16(0xc4,mt),tostring(cpu),(emu.getState().masterClock-start)/21477.272));jit:flush();start=0
   end
  end,emu.cpuType.sa1)
  if labels.save_jit_ready then
   local t=assert(io.open(EDGETEMPLATES,'rb'));local original=t:read('*a');t:close()
   local uses=assert(io.open(output..'/edge_jit_uses.jsonl','w'))
   for _,kind in ipairs({'save','restore'})do
    cb(kind..'_jit_ready',function()
     local mt=emu.memType.sa1Memory
     local width=emu.read16(0xc4,mt);local bank=emu.read16(0x102,mt)&255
     assert(width>0 and width<=32 and width%2==0,'invalid small edge width')
     assert(emu.read16(0x1b0,mt)==(EDGEWIDTHTAG and width or 1),'edge JIT used before lazy load')
     for i=0,511 do
      local expect=original:byte((width//2-1)*512+i+1)
      if (i>=7 and i<=127 and (i-7)%8==0) or (i>=266 and i<=386 and (i-266)%8==0) then expect=bank end
      assert(emu.read(0x500+i,mt)==expect,'edge JIT code/bank differs at '..i)
     end
     uses:write(string.format('{"job":%d,"kind":"%s","bank":%d,"cacheWidth":%d}\\n',emu.read16(0x198,mt),kind,bank,width));uses:flush()
    end,emu.cpuType.sa1)
   end
  end
 end
 if labels.edge_band_chunk_ready then
  local bands=EDGEBANDS
  local log=assert(io.open(output..'/edge_band.jsonl','w'))
  cb('edge_band_chunk_ready',function()
   local mt=emu.memType.sa1Memory
   if emu.read16(0x1b4,mt)>0 then
    local asset=emu.read16(0x3e,mt);local w=emu.read16(0x34,mt);local h=emu.read16(0x36,mt)
    local rows=assert(bands[asset..'_'..w..'_'..h],'band guard shape missing')
    local first=emu.read16(0xa0,mt);local count=emu.read16(0xa8,mt);local right=0
    for b=first//8+1,(first+count+7)//8 do right=math.max(right,rows[b])end
    local left=emu.read16(0x38,mt);local expected=right>0 and math.max(0,(right+left-255)//2) or 0
    expected=(expected+1)&0xfffe
    local actual=emu.read16(0xc4,mt);local old=emu.read16(0x1b2,mt)
    assert(actual==expected and actual<=old and old<=32,'band guard width differs from ROM alpha table')
    log:write(string.format('{"job":%d,"asset":%d,"width":%d,"height":%d,"left":%d,"top":%d,"first":%d,"count":%d,"oldWidth":%d,"newWidth":%d}\\n',emu.read16(0x198,mt),asset,w,h,left,emu.read16(0x3a,mt),first,count,old,actual));log:flush()
   end
  end,emu.cpuType.sa1)
 end
end
if labels.clip_left_cache_hit then
 local log=assert(io.open(output..'/clip_cache.jsonl','w'))
 for _,name in ipairs({'clip_left_cache_hit','clip_left_cache_miss','clip_reverse_cache_hit','clip_reverse_cache_miss','clip_cache_edge_invalidate','clip_cache_bullet_invalidate'})do
  cb(name,function()
   local mt=emu.memType.sa1Memory
   log:write(string.format('{"event":"%s","field":%d,"job":%d,"tag":%d,"asset":%d}\\n',name,field,#times+1,emu.read16(0x07fc,mt),emu.read16(0x3e,mt)));log:flush()
  end,emu.cpuType.sa1)
 end
end
if COMPACTGAME then
 local log=assert(io.open(output..'/game_offload.jsonl','w'))
 local active=false;local begin=0
 cb('sa1_game_begin',function()active=true;begin=emu.getState().masterClock end,emu.cpuType.sa1)
 cb('sa1_game_end',function()
  active=false
  local mt=emu.memType.sa1Memory
  assert(emu.read16(0x435100+labels.c_sp,mt)==0x7c00,'game software stack did not balance')
  for i=0,62,2 do
   assert(emu.read16(0x437b00+i,mt)==0xa55a,'game software stack crossed scratch boundary')
   assert(emu.read16(0x437e00+i,mt)==0xa55a,'game hardware stack crossed software stack boundary')
  end
  log:write(string.format('{"field":%d,"logic":%d,"ms":%.6f}\\n',field,logic,(emu.getState().masterClock-begin)/21477.272));log:flush()
 end,emu.cpuType.sa1)
 emu.addMemoryCallback(function()
  if active then local f=assert(io.open(output..'/failure.txt','w'));f:write('SA-1 game accessed S-CPU arithmetic registers');f:close();emu.stop(1)end
 end,emu.callbackType.write,0x4202,0x4206,emu.cpuType.sa1,emu.memType.sa1Memory)
end
if labels.fallback_publish and scenario:match('tracefallback') then
 local f=assert(io.open(output..'/fallback_debug.jsonl','w'))
 cb('fallback_publish',function()
  local mt=emu.memType.snesMemory;local slot=emu.read16(0x7e0000+labels.pipe_target_slot,mt)
  local record=0x7e0000+labels.pipe_records+slot*512
  local gen=emu.read16(record+8,mt);local page=emu.read16(record+6,mt)*2
  local outside={}
  for tile=32,767 do
   local mask=emu.read(0x7e0000+labels.fbMasks+slot*128+math.floor(tile/8),mt)
   if (mask & (1<<(tile%8)))==0 then
    for b=0,31 do
     if emu.read(page+tile*32+b,emu.memType.snesVideoRam)~=0 then outside[#outside+1]=tile;break end
    end
   end
  end
  f:write(string.format('{"generation":%d,"page":%d,"outside":[%s]}\\n',gen,page,table.concat(outside,',')));f:flush()
 end)
 if labels.sa1_fallback_build then cb('sa1_fallback_build',function()
  local s=emu.getState()
  f:write(string.format('{"field":%d,"sa1Stack":%d}\\n',field,s['cart.coprocessor.cpu.sp'] or -1));f:flush()
 end,emu.cpuType.sa1)end
end
emu.addMemoryCallback(function(address,value)
 local line=emu.getState()['ppu.scanline']
 if requestLog and field>90 and line>=22 and line<202 and (value&0x80)~=0 then
  local f=assert(io.open(output..'/failure.txt','w'));f:write('early request shortened visible region field='..field..' line='..line);f:close();emu.stop(1)
 end
 if field>85 and (line>=203 or line<21) and line<225 and (value&0x80)==0 then
  local f=assert(io.open(output..'/failure.txt','w'));f:write('HDMA unblanked reserved DMA lines field='..field..' line='..line..' value='..value);f:close()
  local g=assert(io.open(output..'/failure_state.txt','w'));for k,v in pairs(emu.getState())do g:write(tostring(k)..'='..tostring(v)..'\\n')end;g:close();emu.stop(1)
 end
end,emu.callbackType.write,0x2100,0x2100,emu.cpuType.snes,emu.memType.snesMemory)
-- VRAM/OAM DMAは実際のforced blankまたはVBLANK中に開始する。
emu.addMemoryCallback(function(address,value)
 if field>90 and (value&1)~=0 then
  local bb=emu.read(0x4301,emu.memType.snesMemory)
  if bb==0x18 or bb==4 then
   local st=emu.getState()
   if emu.read16(0x4305,emu.memType.snesMemory)==0 then
    local f=assert(io.open(output..'/failure.txt','w'))
    f:write('zero-length VRAM/OAM DMA would transfer 65536 bytes field='..field);f:close();emu.stop(1)
   end
   if vramPrefetch3 and bb==0x18 then
    local first=(st['ppu.vramAddress']&0x7fff)*2
    local last=first+emu.read16(0x4305,emu.memType.snesMemory)
    local fixedOverlap=(first<1024 and last>0) or (first<0x4400 and last>0x4000)
    if vramFourShared then fixedOverlap=(first<0x9000 and last>0x8c00) or (first<0xc000 and last>0xbc00) end
    if vramFifo then
     local playerUpload=first==0xc800 and last==0xcb80 and emu.read(0x4304,emu.memType.snesMemory)==0xdf
     local mapUpload=first==0xc040 and last==0xc600
     fixedOverlap=not (playerUpload or mapUpload or (first>=0x20 and last<=0xbc20))
     if first<0xbc20 then
      for zero=0,0xa000,0x2000 do assert(not (first<zero+32 and last>zero),'FIFO overwrites reserved zero tile')end
     end
    end
    if vramFourOwned then
     local base=math.floor(first/0x3000)*0x3000
     local a=first-base;local b=last-base
     local playerUpload=first==0xc800 and last==0xcb80 and emu.read(0x4304,emu.memType.snesMemory)==0xdf
     fixedOverlap=not (playerUpload or (base<0xc000 and ((a>=0x20 and b<=0x2800) or (a>=0x2840 and b<=0x2e00) or (a>=0x2e00 and b<=0x3000))))
    end
    if fixedMap then
     local playerUpload=first==0xc800 and last==0xcb80 and emu.read(0x4304,emu.memType.snesMemory)==0xdf
     local mapUpload=fixedMapDelta and first==0xc040 and last==0xc600 and emu.read(0x4304,emu.memType.snesMemory)==0x7e
     if fixedMapDeltaDma and first>=0xc040 and last<=0xc600 and emu.read(0x4304,emu.memType.snesMemory)==1 then mapUpload=true end
     fixedOverlap=not (playerUpload or mapUpload or (first>=0x20 and last<=0x5c20) or (first>=0x6020 and last<=0xbc20))
    end
    if fixedOverlap then
     local f=assert(io.open(output..'/failure.txt','w'))
     f:write('frame DMA overwrites fixed BG2 CHR field='..field..' first='..first..' last='..last);f:close();emu.stop(1)
    end
   end
   if not st['ppu.forcedBlank'] and st['ppu.scanline']<225 then
    local f=assert(io.open(output..'/failure.txt','w'))
    f:write('VRAM/OAM DMA started outside actual blank field='..field..' line='..st['ppu.scanline']);f:close();emu.stop(1)
   end
  end
 end
end,emu.callbackType.write,0x420b,0x420b,emu.cpuType.snes,emu.memType.snesMemory)
emu.addMemoryCallback(function(address,value)
 if field>90 then
  local st=emu.getState()
  if not st['ppu.forcedBlank'] and st['ppu.scanline']<225 then
   local f=assert(io.open(output..'/failure.txt','w'))
   f:write('BG1 page changed outside actual blank field='..field..' line='..st['ppu.scanline']);f:close();emu.stop(1)
  end
  pageCommit={field=field,line=st['ppu.scanline'],clock=st.masterClock}
 end
end,emu.callbackType.write,0x210b,0x210b,emu.cpuType.snes,emu.memType.snesMemory)
local packetClock=0
if pipeline then
 local function irqEntry()if irqDepth==0 then irqClock=emu.getState().masterClock end;irqDepth=irqDepth+1 end
 cb('pipe_irq',irqEntry)
 if labels.p3PumpBlank then cb('p3PumpBlank',irqEntry)end
 cb('pipe_irq_exit',function()irqDepth=irqDepth-1;assert(irqDepth>=0,'IRQ accounting underflow');if irqDepth==0 then irqTicks=irqTicks+emu.getState().masterClock-irqClock;irqClock=0 end end)
 emu.addMemoryCallback(function(address,value)
  if irqDepth>0 then
   local f=assert(io.open(output..'/failure.txt','w'))
   f:write(string.format('IRQ modified game math register $%04x at field %d',address,field));f:close()
   emu.stop(1)
  end
 end,emu.callbackType.write,0x4202,0x4206,emu.cpuType.snes,emu.memType.snesMemory)
end
cb('_fx_build_packet',function()packetClock=activeClock() end)
if packetOffload and labels.sa1_packet_finished then
 local packetLog=assert(io.open(output..'/packet_prepare.jsonl','w'))
 local packetBegin=0
 cb('sa1_packet_prepare',function()packetRunning=true;packetBegin=emu.getState().masterClock end,emu.cpuType.sa1)
 cb('sa1_packet_finished',function()
  packetLog:write(string.format('{"field":%d,"ms":%.6f,"inputCount":%d,"outputCount":%d}\\n',field,(emu.getState().masterClock-packetBegin)/21477.272,emu.read16(0x431404,emu.memType.sa1Memory),emu.read16(0x431402,emu.memType.sa1Memory)));packetLog:flush()
  packetRunning=false
 end,emu.cpuType.sa1)
end
if not packetOffload then for _,name in ipairs({'initialized','sorted','packet_done'})do
 cb(name,function()local c=activeClock();cpuParts['packet_'..name]=(c-packetClock)/21477.272;packetClock=c end)
end end
if pipeline then
 cb('dma_started',function()
  local state=emu.getState();dmaClock=state.masterClock;dmaLine=state['ppu.scanline'];dmaLength=emu.read16(0x4305,emu.memType.snesMemory)
 end)
 cb('pipe_dma_measured_end',function()
  local state=emu.getState();dmaJobs[#dmaJobs+1]=string.format('{"field":%d,"line":%d,"endLine":%d,"length":%d,"ms":%.6f}',field,dmaLine,state['ppu.scanline'],dmaLength,(state.masterClock-dmaClock)/21477.272)
 end)
 local diag=assert(io.open(output..'/pipeline_trace.jsonl','w'))
 for _,name in ipairs({'pipe_irq','pipe_irq_transfer','pipe_wait_dma','dma_started','half_dma_finished','prefetch_finished','pipe_irq_done','pipe_prefix_plan','pipe_fast_begin','pipe_fast_partial_done','pipe_collect','pipe_flip'})do
 if labels[name] then
  cb(name,function()
   if presents<10 or (scenario:match('timing') and field>=620 and field<=650) then
    local s=emu.getState();local mt=emu.memType.snesMemory
    diag:write(string.format('{\"label\":\"%s\",\"field\":%d,\"present\":%d,\"line\":%d,\"clock\":%d,\"src\":%d,\"len\":%d,\"grant\":%d}\\n',name,field,presents,s['ppu.scanline'],s.masterClock,emu.read16(0x4302,mt)+65536*emu.read(0x4304,mt),emu.read16(0x4305,mt),emu.read16(0x311c,mt)));diag:flush()
   end
  end)
 end
 end
 cb('prefetch_finished',function()
  if DENSE_TILES then return end
  local mt=emu.memType.snesMemory
  local slot=emu.read16(0x7e0000+labels.pipe_target_slot,mt)
  local record=0x7e0000+labels.pipe_records+slot*512
  local gen=emu.read16(record+8,mt)
  if captureGeneration(gen) then
   local bank=emu.read16(record,mt);local t={}
   for i=0,24575 do t[#t+1]=string.char(emu.read(((bank&255)-0x40)*65536+(bank&0xff00)+i,emu.memType.snesSaveRam))end
   completedFrames[gen]=table.concat(t)
  end
 end)
 if scenario:match('tracedeadline') then
  local f=assert(io.open(output..'/transfer_deadline.jsonl','w'))
  local function log(name,extra)
   -- 197行IRQが重い世代を転送する前後を捕捉する。
   if field<660 or field>720 then return end
   local s=emu.getState();local mt=emu.memType.snesMemory;local base=0x7e0000
   local offset=emu.read16(base+labels.pipe_record_offset,mt);local r=base+labels.pipe_records+offset
   local e={event=name,field=field,present=presents,clock=s.masterClock,line=s['ppu.scanline'],hclock=s['memoryManager.hClock'],a=s['cpu.a'],x=s['cpu.x'],d=s['cpu.d'],slot=emu.read16(base+labels.pipe_target_slot,mt),generation=emu.read16(r+8,mt),remaining=emu.read16(r+34,mt),cursor=emu.read16(r+4,mt),descriptors=emu.read16(r+2,mt),available=emu.read16(base+labels.pipe_available,mt),cost=emu.read16(base+labels.pipe_dma_chunk,mt),flipped=emu.read16(base+labels.pipe_presented_irq,mt),complete=emu.read16(base+labels.pipe_complete,mt),request=emu.read16(0x311e,mt),grant=emu.read16(0x311c,mt),blank=s['ppu.forcedBlank']}
   if extra then for k,v in pairs(extra)do e[k]=v end end
   local parts={};for k,v in pairs(e)do parts[#parts+1]=string.format('"%s":%s',k,type(v)=='string' and string.format('%q',v) or tostring(v))end
   f:write('{',table.concat(parts,','),'}\\n');f:flush()
  end
  for _,name in ipairs({'pipe_irq_transfer','pipe_collect','pipe_wait_dma','pipe_choose_target','pipe_setup_transfer','pipe_time_left','pipe_reserved','pipe_no_time','pipe_prefix_plan','pipe_fast_begin','pipe_fast_group','pipe_fast_groups_done','pipe_fast_partial_done','pipe_fast_empty','pipe_fast_unavailable','pipe_descriptor','pipe_full_descriptor','pipe_set_chunk','pipe_transfer_complete','pipe_transfer_pause','pipe_flip','dma_finished','p3Complete','p3Flip','pipe_irq_checked'})do
   assert(labels[name],'missing deadline trace label '..name)
   cb(name,function()log(name)end)
  end
  if labels.pfTables then
   local checked=assert(io.open(output..'/prefix_search_verified.jsonl','w'))
   cb('pipe_fast_begin',function()
    local mt=emu.memType.snesMemory;local b=0x7e0000
    if not PREFIXONEPASS and emu.read16(b+labels.pfPartial,mt)==0 then return end
    local offset=emu.read16(b+labels.pipe_record_offset,mt);local r=b+labels.pipe_records+offset
    local start=emu.read16(r+4,mt)//6;local count=emu.read16(r+2,mt)//6
    assert(start<count and count<=48,'invalid prefix table extent')
    local table=b+labels.pfTables+(offset//512)*256;local beforeBytes,beforeCost=0,0
    if start>0 then beforeBytes=emu.read16(table+(start-1)*4,mt);beforeCost=emu.read16(table+(start-1)*4+2,mt)end
    local originalLength=emu.read16(table+start*4,mt)-beforeBytes
    local partial=originalLength-emu.read16(r+208+start*6,mt)
    assert(partial>=0,'prefix partial length negative')
    beforeBytes=beforeBytes+partial;beforeCost=beforeCost+partial+partial//32+partial//128+(prefixRefreshSixteenth and partial//16 or 0)
    local available=emu.read16(b+labels.pipe_available,mt);local limit=available-384+beforeCost
    local last=start
    for i=start+1,count do if emu.read16(table+(i-1)*4+2,mt)<limit then last=i else break end end
    if PREFIXONEPASS and emu.read16(table+(count-1)*4+2,mt)<limit+384-PREFIXFULLRESERVE then last=count end
    if PARTIALTRANSFERRESERVE>0 then
     local hold=emu.read16(b+labels.pfHoldLast,mt)
     if last==count then assert(hold==0,'partial budget completed a frame')
     else
      assert(hold==1,'partial budget flag missing')
      limit=emu.read16(b+labels.pipe_unreserved,mt)-PARTIALTRANSFERRESERVE-384+beforeCost
      last=start
      for i=start+1,count-1 do if emu.read16(table+(i-1)*4+2,mt)<limit then last=i else break end end
      assert(last<count and emu.read16(b+labels.pfPartial,mt)==1,'partial budget selected the final descriptor')
     end
    end
    assert(last>start,'empty prefix executed')
    local bytes=emu.read16(table+(last-1)*4,mt)-beforeBytes
    assert(emu.read16(b+labels.pfDesc,mt)==(last-start)*6,'prefix search chose wrong descriptor count')
    assert(emu.read16(b+labels.pfBytes,mt)==bytes,'prefix search chose wrong byte count')
    checked:write(string.format('{"field":%d,"start":%d,"last":%d,"count":%d,"partial":%d,"bytes":%d,"limit":%d}\\n',field,start,last,count,partial,bytes,limit));checked:flush()
   end)
  end
  emu.addMemoryCallback(function(address,value)
   if value==1 then
    local mt=emu.memType.snesMemory
    log('dma_420b',{dmaBytes=emu.read16(0x4305,mt),dmaSource=emu.read16(0x4302,mt)+emu.read(0x4304,mt)*65536,dmaDestination=emu.getState()['ppu.vramAddress'],dmaMode=emu.read(0x4301,mt)})
   end
  end,emu.callbackType.write,0x420b,0x420b,emu.cpuType.snes,emu.memType.snesMemory)
 end
 cb(labels.pipe_irq_checked and 'pipe_irq_checked' or 'pipe_irq_done',function()
  -- IRQ末尾のキュー管理は表示中も実行できる。PPUの実転送・切替位置を別々に検査する。
  local line=emu.getState()['ppu.scanline']
  local mt=emu.memType.snesMemory;local ready=0;local rendering=0
  for i=0,DEPTH-1 do local s=emu.read16(0x7e0000+labels.pipe_status+i*2,mt);if s==2 then ready=ready+1 elseif s==1 then rendering=rendering+1 end end
  queueSamples[#queueSamples+1]=string.format('{\"field\":%d,\"line\":%d,\"ready\":%d,\"rendering\":%d,\"complete\":%d,\"flipped\":%d,\"target\":%d}',field,line,ready,rendering,emu.read16(0x7e0000+labels.pipe_complete,mt),emu.read16(0x7e0000+labels.pipe_presented_irq,mt),emu.read16(0x7e0000+labels.pipe_target_slot,mt))
 end)
end
if labels.sa1_list_sort or labels.sa1_sort_packet or labels.sa1_temporal_prepare or labels.sa1_radix_sort or labels.sa1_key_buckets then
 cb(labels.sa1_list_sort and 'sa1_list_sort' or labels.sa1_key_buckets and 'sa1_key_buckets' or labels.sa1_radix_sort and 'sa1_radix_sort' or (labels.sa1_sort_packet and 'sa1_sort_packet' or 'sa1_temporal_prepare'),function()
  local mt=(GAMEOFFLOAD or packetOffload) and emu.memType.sa1Memory or emu.memType.snesMemory;local base=packetOffload and (packetIramArrays and 0 or 0x430000) or GAMEOFFLOAD and GAMEBWBASE or 0x7e0000
  local n=packetOffload and emu.read16(0x700+labels.packet_work+8,mt) or GAMEOFFLOAD and emu.read16(labels.packet_work+8,emu.memType.sa1Memory) or emu.read16(base+labels.packet_work+8,mt)
  sortReference={}
  for i=0,n-2,2 do sortReference[#sortReference+1]={key=emu.read16(base+labels.keys+i,mt),value=emu.read16(base+labels.order+i,mt),index=i}end
  table.sort(sortReference,function(a,b)return a.key<b.key or (a.key==b.key and a.index<b.index)end)
 end)
 cb('sorted',function()
  if sortReference then
   local base=packetOffload and (packetIramArrays and 0 or 0x430000) or GAMEOFFLOAD and GAMEBWBASE or 0x7e0000
   local mt=(GAMEOFFLOAD or packetOffload) and emu.memType.sa1Memory or emu.memType.snesMemory
   for i,v in ipairs(sortReference)do assert(emu.read16(base+labels.order+(i-1)*2,mt)==v.value,'packet sort changed depth/priority/stability field='..field..' index='..i..' expected='..v.value..' key='..v.key..' actual='..emu.read16(base+labels.order+(i-1)*2,mt))end
   sortReference=nil
  end
 end)
end
local function dump(name,mem,a,n)
 local f=assert(io.open(output..'/'..name,'wb'));local t={}
 for i=0,n-1 do t[#t+1]=string.char(emu.read(a+i,mem)) end
 f:write(table.concat(t));f:close()
end
if labels.sparse_direct_overflow then cb('sparse_direct_overflow',function()error('direct sparse VRAM capacity exceeded field='..field)end,emu.cpuType.sa1)end
if labels.idle_clear_dma then
 local f=assert(io.open(output..'/idle_clear.jsonl','w'));local started,slot,band=0,0,0
 cb('idle_clear_dma',function()
  started=emu.getState().masterClock
  slot=emu.read16(0xa0,emu.memType.sa1InternalRam)//2
  band=emu.read16(0xac,emu.memType.sa1InternalRam)
 end,emu.cpuType.sa1)
 cb('idle_clear_done',function()
  f:write(string.format('{"field":%d,"slot":%d,"band":%d,"ms":%.6f}\\n',field,slot,band,(emu.getState().masterClock-started)/21477.272));f:flush()
 end,emu.cpuType.sa1)
end
if labels.pipe_fast_partial_done then
 local f=assert(io.open(output..'/prefix_dma.jsonl','w'));local started=0
 local planClock,planMs=0,0
 cb('pipe_prefix_plan',function()planClock=emu.getState().masterClock end)
 cb('pipe_fast_begin',function()
  started=emu.getState().masterClock
  planMs=planClock>0 and (started-planClock)/21477.272 or 0
  planClock=0
 end)
 cb('pipe_fast_partial_done',function()
  local st=emu.getState();local mt=emu.memType.snesMemory;local base=0x7e0000
  f:write(string.format('{"field":%d,"line":%d,"bytes":%d,"descriptors":%d,"ms":%.6f,"planMs":%.6f}\\n',field,st['ppu.scanline'],emu.read16(base+labels.pfBytes,mt),emu.read16(base+labels.pfDesc,mt)//6,(st.masterClock-started)/21477.272,planMs));f:flush()
 end)
end
if labels.stage_too_large then cb('stage_too_large',function()error('compact WRAM staging capacity exceeded field='..field)end)end
if labels.stage_time_ok then
 local started=0;local bytes=0;local count=0;local line=0
 cb('stage_time_ok',function()
  local st=emu.getState();local mt=emu.memType.snesMemory
  local record=0x7e0000+labels.pipe_records+emu.read16(0x7e0000+labels.stage_record,mt)
  started=st.masterClock;line=st['ppu.scanline'];bytes=emu.read16(record+34,mt);count=emu.read16(record+2,mt)//6
 end)
 cb('stage_converted',function()
  local st=emu.getState()
  cpuStageJobs[#cpuStageJobs+1]=string.format('{"field":%d,"bytes":%d,"count":%d,"line":%d,"endLine":%d,"ms":%.6f}',field,bytes,count,line,st['ppu.scanline'],(st.masterClock-started)/21477.272)
 end)
end
if labels.fast_base_ready then
 local debug=assert(io.open(output..'/fast_debug.txt','w'))
 for _,name in ipairs({'sa1_try_fast','fast_tiles','fast_fail','fast_base_ready','invoke_row'})do
  cb(name,function()
   if presents==0 then
    local mt=emu.memType.sa1Memory
    debug:write(name)
    for _,a in ipairs({0x34,0x36,0x38,0x3a,0x44,0x48,0xa0,0xa2,0xb0,0xb2,0xb4,0xc0,0xc2,0xf8})do debug:write(string.format(' %02x=%04x',a,emu.read16(a,mt)))end
    debug:write('\\n');debug:flush()
   end
  end,emu.cpuType.sa1)
 end
end
if labels.invoke_row then
 local recent=assert(io.open(output..'/native_trace.jsonl','w'))
 cb('invoke_row',function()
  local mt=emu.memType.sa1Memory
  local entry=emu.read16(0x7f1,mt)+65536*emu.read(0x7f3,mt)
  local n=emu.read16(0x8c,mt)
  if presents>=24 and presents<26 then
   recent:write(string.format('{"present":%d,"entry":%d,"len":%d,"dy":%d,"asset":%d,"wordstart":%d,"initialA":%d,"edge":%d}\\n',presents,entry,n,emu.read16(0x40,mt),emu.read16(0x3e,mt),emu.read16(0xd4,mt),emu.read16(0xd6,mt),emu.read16(0x90,mt)));recent:flush()
   dump('latest_jit.bin',emu.memType.sa1InternalRam,0x700,256)
  end
 end,emu.cpuType.sa1)
end
if labels.right_narrow_entry then
 local f=assert(io.open(output..'/right_narrow.jsonl','w'))
 for _,name in ipairs({'right_narrow_entry','right_narrow_ready'})do
  cb(name,function()
   local mt=emu.memType.sa1Memory
   f:write(string.format('{"event":"%s","job":%d,"field":%d,"asset":%d,"width":%d,"height":%d,"left":%d,"row":%d,"length":%d}\\n',
    name,#times+1,field,emu.read16(0x3e,mt),emu.read16(0x34,mt),emu.read16(0x36,mt),emu.read16(0x38,mt),emu.read16(0xa0,mt),emu.read16(0x8c,mt)));f:flush()
  end,emu.cpuType.sa1)
 end
end
cb('_fx_frame',function()
 logic=logic+1
 begin=emu.getState().masterClock
 if scenario:match('stress') then byte('_monosh_player_invuln',255)end
 if scenario:match('^boss') then
  byte('_monosh_player_invuln',255)
  if field>=90 then
   byte('_monosh_enemy_stage_complete_flag',1)
   byte('_monosh_enemy_active_count_value',0)
   byte('_monosh_stage_object_count',0)
   word('_monosh_stage_frame_counter',3900)
  end
 end
end)
if labels.opaque_prefix_selected and labels.opaque_prefix_patch_done then
 local f=assert(io.open(output..'/opaque_prefix.jsonl','w'))
 local opaqueActive=false
 cb('opaque_prefix_selected',function()
  opaqueActive=true
  local mt=emu.memType.sa1Memory
  f:write(string.format('{"kind":"select","job":%d,"index":%d,"width":%d,"height":%d,"frontAsset":%d}\\n',#times+1,emu.read16(0x2c,mt),emu.read16(0x34,mt),emu.read16(0x36,mt),emu.read16(0xb8,mt)));f:flush()
 end,emu.cpuType.sa1)
 cb('opaque_prefix_patch_done',function()
  if not opaqueActive then return end
  local mt=emu.memType.sa1Memory;local slot=emu.read16(0x8c,mt)
  local bank=emu.read(0x94,mt);local old=bank*65536+emu.read16(0x92,mt)
  assert(emu.read(0x70a+slot,mt)==bank,'opaque prefix changed native bank')
  local new=bank*65536+emu.read16(0x708+slot,mt);local op=emu.read(new,mt)
  assert(new>=old and (op==0xa9 or op==0xbd or op==0x6b),'opaque prefix resumed without accumulator load')
  local format=0
  if not OPAQUEINLINERAW then
   local hint=emu.read(old-5,mt)+emu.read(old-4,mt)*256+emu.read(old-3,mt)*65536
   local marker=emu.read(hint,mt);format=marker>=128 and marker or 0
  end
  f:write(string.format('{"kind":"patch","job":%d,"row":%d,"old":%d,"new":%d,"format":%d,"allHidden":%s}\\n',#times+1,emu.read16(0x8e,mt),old,new,format,op==0x6b and 'true' or 'false'));f:flush()
 end,emu.cpuType.sa1)
 cb('opaque_prefix_finished',function()opaqueActive=false end,emu.cpuType.sa1)
end
if labels.cache_miss then
 local f=assert(io.open(output..'/bullet_cache.jsonl','w'));local start=0;local missed=false
 cb('sa1_bullet_cache_prepare',function()start=emu.getState().masterClock;missed=false end,emu.cpuType.sa1)
 cb('cache_miss',function()missed=true end,emu.cpuType.sa1)
 cb('cache_ready',function()
  local mt=emu.memType.sa1Memory
  f:write(string.format('{"job":%d,"field":%d,"asset":%d,"width":%d,"height":%d,"flags":%d,"miss":%s,"ms":%.6f}\\n',#times+1,field,emu.read16(0x3e,mt),emu.read16(0x34,mt),emu.read16(0x36,mt),emu.read16(0x3c,mt),missed and 'true' or 'false',(emu.getState().masterClock-start)/21477.272));f:flush()
 end,emu.cpuType.sa1)
end
cb('render_started',function()begin=emu.getState().masterClock;activeBegin=activeClock();cpuParts={};cpuActiveParts={} end)
cb('logic_finished',function()
 if gameAudit then
  local mt=GAMEOFFLOAD and emu.memType.sa1Memory or emu.memType.snesMemory
  local base=GAMEOFFLOAD and GAMEBWBASE or 0x7e0000
  local function read(name,wide)
   assert(labels[name], 'missing game audit label '..name)
   return wide and emu.read16(base+labels[name],mt) or emu.read(base+labels[name],mt)
  end
  gameAudit:write(string.format('{"logic":%d,"field":%d,"clock":%d,"runtimeFrame":%d,"stageFrame":%d,"playerState":%d,"playerInvuln":%d,"bossState":%d,"bossHp":%d,"enemies":%d,"playerBullets":%d}\\n',
   logic,field,emu.getState().masterClock,read('_monosh_runtime_frame_counter',true),read('_monosh_stage_frame_counter',true),
   read('_monosh_player_state'),read('_monosh_player_invuln'),read('_monosh_boss_state'),read('_monosh_boss_hp'),
   read('_monosh_enemy_active_count_value'),read('_monosh_player_bullet_count')));gameAudit:flush()
 end
 if scenario:match('^splitfixture') then
  local objects=splitFixtures[(logic-1)%#splitFixtures+1]
  word('_fx_packet_count',#objects)
  for i,o in ipairs(objects)do
   local a=0x7e0000+labels._fx_packet+(i-1)*10;local mt=emu.memType.snesMemory
   emu.write16(a,o[1]&65535,mt);emu.write16(a+2,o[2]&65535,mt)
   for j=3,8 do emu.write(a+j+1,o[j],mt)end
  end
 end
 if scenario:match('^opaquefixture') then
  local targets=OPAQUETARGETS;local fronts=OPAQUEFRONTS
  local g=targets[(logic-1)%#targets+1];local f=fronts[(logic-1)%#fronts+1]
  local centers={40,41,128,129,216,217,16,250};local tops={-20,0,30,55,120,180,191}
  local center=centers[(logic-1)%#centers+1];local top=tops[(logic-1)%#tops+1]
  local shifts={-24,0,24};local shift=shifts[math.floor((logic-1)/#centers)%3+1]
  local objects={{16,130,79,62,39},{center,top+g[2]+20,g[1],g[2],40},{128,120,12,12,7},{center,top+g[2]+20,g[1],g[2],40},{center+shift,top-8+f[3]+20,f[2],f[3],f[1]}}
  word('_fx_packet_count',#objects)
  for i,o in ipairs(objects)do
   local a=0x7e0000+labels._fx_packet+(i-1)*10;local mt=emu.memType.snesMemory
   emu.write16(a,o[1]&65535,mt);emu.write16(a+2,o[2]&65535,mt)
   emu.write(a+4,o[3],mt);emu.write(a+5,o[4],mt);emu.write(a+6,o[5],mt);emu.write(a+7,0,mt);emu.write16(a+8,i,mt)
  end
 end
 if scenario:match('^clipfixture') then
  local objects={{16,110,79,62,39},{16,150,79,62,39},{128,120,12,12,7},{16,130,79,62,39},{-10,155,88,38,42},{16,160,79,62,39},{250,165,91,71,40},{250,110,91,71,41}}
  word('_fx_packet_count',#objects)
  for i,g in ipairs(objects)do
   local a=0x7e0000+labels._fx_packet+(i-1)*10;local mt=emu.memType.snesMemory
   emu.write16(a,g[1]&65535,mt);emu.write16(a+2,g[2],mt)
   emu.write(a+4,g[3],mt);emu.write(a+5,g[4],mt);emu.write(a+6,g[5],mt);emu.write(a+7,0,mt);emu.write16(a+8,i,mt)
  end
 end
 if scenario:match('^transferfixture') then
  -- 実際のassetと縮小表を9個描き、記述子の途中分割・翌IRQ再開を通す。
  word('_fx_packet_count',9)
  for i=0,8 do
   local a=0x7e0000+labels._fx_packet+i*10;local mt=emu.memType.snesMemory
   emu.write16(a,48+(i%3)*80,mt);emu.write16(a+2,94+math.floor(i/3)*58,mt)
   emu.write(a+4,94,mt);emu.write(a+5,74,mt);emu.write(a+6,40+(logic+i)%2,mt);emu.write(a+7,0,mt);emu.write16(a+8,i+1,mt)
  end
 end
 if scenario:match('^stackfixture') then
  local centers={0,47,48,49,128,182,222,265,266,267,268,286,300}
  local tops={-20,0,30,55,56,120,180}
  local h=73+math.floor((logic-1)/(#centers*#tops))%2
  local w=94
  if scenario:match('wide') then
   local g=math.floor((logic-1)/(#centers*#tops))%3
   if g==2 then w=91;h=71 else h=73+g end
  end
  if scenario:match('^stackfixturemin') then
   local geometries=STACKMINGEOMETRIES
   local g=geometries[math.floor((logic-1)/(#centers*#tops))%#geometries+1]
   w=g[1];h=g[2]
  end
  local top=tops[math.floor((logic-1)/#centers)%#tops+1]
  word('_fx_packet_count',2)
  for i=1,2 do
   local a=0x7e0000+labels._fx_packet+(i-1)*10;local mt=emu.memType.snesMemory
   emu.write16(a,centers[(logic+i-2)%#centers+1],mt)
   emu.write16(a+2,(top+h+20)&65535,mt)
   emu.write(a+4,w,mt);emu.write(a+5,h,mt);emu.write(a+6,39+i,mt);emu.write(a+7,0,mt);emu.write16(a+8,i,mt)
  end
 end
 if scenario:match('^leftfixture') then
  local geometries=LEFTFIXTUREGEOMETRIES
  if scenario:match('^leftfixtureindexed') then
   local centers={-40,-39,0,1,16,17,30,31,64,65,128,129,250,251}
   local tops={-20,30,180}
   word('_fx_packet_count',2)
   for i=1,2 do
    local n=((logic-1)*2+i-1)%(#geometries*#centers*#tops)
    local g=geometries[n%#geometries+1]
    local x=centers[math.floor(n/#geometries)%#centers+1]
    local top=tops[math.floor(n/(#geometries*#centers))%#tops+1]
    local a=0x7e0000+labels._fx_packet+(i-1)*10;local mt=emu.memType.snesMemory
    emu.write16(a,x&65535,mt);emu.write16(a+2,(top+g[3]+20)&65535,mt)
    emu.write(a+4,g[2],mt);emu.write(a+5,g[3],mt);emu.write(a+6,g[1],mt);emu.write(a+7,0,mt);emu.write16(a+8,i,mt)
   end
  else
  local centers={-40,0,16,30,64,128,250}
  local bottoms={40,120,205}
  word('_fx_packet_count',2)
  for i=1,2 do
   local g=geometries[math.floor((logic-1)/7)*2%#geometries+i]
   local a=0x7e0000+labels._fx_packet+(i-1)*10;local mt=emu.memType.snesMemory
   emu.write16(a,centers[(logic+i-2)%#centers+1]&65535,mt)
   local bottomIndex=math.floor((logic-1)/#centers)
   if scenario:match('^leftfixtureexplosion') then bottomIndex=bottomIndex+math.floor((logic-1)/(#centers*(#geometries/2))) end
   if scenario:match('^leftfixtureflame') then bottomIndex=math.floor((logic-1)/(#centers*3)) end
   emu.write16(a+2,bottoms[bottomIndex%#bottoms+1],mt)
   local phase=(scenario:match('^leftfixtureflame') and g[1]==31) and math.floor((logic-1)/#centers)%3 or 0
   emu.write(a+4,g[2],mt);emu.write(a+5,g[3],mt);emu.write(a+6,g[1],mt);emu.write(a+7,phase,mt);emu.write16(a+8,i,mt)
  end
  end
 end
 if scenario:match('^flipfixture') then
  local assets={6,7,8,37};local sizes={6,16,32,48,62}
  local size=sizes[math.floor((logic-1)/12)%5+1]
  local flags=(math.floor((logic-1)/3)%4)*16+(logic-1)%3
  local centers={-2,254,128,64};local bottoms={120,200,30,160}
  word('_fx_packet_count',4)
  for i=1,4 do
   local a=0x7e0000+labels._fx_packet+(i-1)*10;local mt=emu.memType.snesMemory
   emu.write16(a,centers[i]&65535,mt);emu.write16(a+2,bottoms[i],mt)
   emu.write(a+4,size,mt);emu.write(a+5,size,mt);emu.write(a+6,assets[i],mt);emu.write(a+7,flags,mt)
   emu.write16(a+8,0,mt)
  end
 end
 if packetOffload and (scenario:match('^flipfixture') or scenario:match('^leftfixture')) then
  local mt=emu.memType.snesMemory;local n=emu.read16(0x7e0000+labels._fx_packet_count,mt)
  byte('_fx_draw_count',n)
  for i=0,n*10-1 do emu.write(0x7e0000+labels._fx_draw+i,emu.read(0x7e0000+labels._fx_packet+i,mt),mt)end
 end
 logicMs=(emu.getState().masterClock-begin)/21477.272
 local parts={};for name,v in pairs(cpuParts)do parts[#parts+1]=string.format('"%s":%.6f',name,v)end
 local activeParts={};for name,v in pairs(cpuActiveParts)do activeParts[#activeParts+1]=string.format('"%s":%.6f',name,v)end
 cpuJobs[#cpuJobs+1]=string.format('{"field":%d,"logicMs":%.6f,"activeLogicMs":%.6f,"parts":{%s},"activeParts":{%s}}',field,logicMs,(activeClock()-activeBegin)/21477.272,table.concat(parts,','),table.concat(activeParts,','))
end)
cb('transfer_chunk',function()local s=emu.getState();readyLine=s['ppu.scanline'];startClock=s.masterClock end)
cb('dma_chunk_ready',function()waitMs=(emu.getState().masterClock-startClock)/21477.272;startClock=emu.getState().masterClock end)
cb('sa1_clear_start',function()sa1begin=emu.getState().masterClock end,emu.cpuType.sa1)
if labels.cpu_dirty_prepare and labels.cpu_dirty_done then
 local f=assert(io.open(output..'/cpu_dirty.jsonl','w'))
 local t,a=0,0
 cb('cpu_dirty_prepare',function()t=emu.getState().masterClock;a=activeClock()end)
 cb('cpu_dirty_done',function()
  f:write(string.format('{"logic":%d,"field":%d,"ms":%.6f,"activeMs":%.6f}\\n',logic,field,(emu.getState().masterClock-t)/21477.272,(activeClock()-a)/21477.272));f:flush()
 end)
end
if labels.sa1_sprite_begin then
 cb('sa1_sprite_begin',function()objectBegin=emu.getState().masterClock end,emu.cpuType.sa1)
 cb('sa1_sprite_done',function()
  local mt=emu.memType.sa1Memory;local i=emu.read16(0x2c,mt);local a=0x430000+i*10;local ms=(emu.getState().masterClock-objectBegin)/21477.272
  if ms>0.5 then objectJobs[#objectJobs+1]=string.format('{\"field\":%d,\"job\":%d,\"index\":%d,\"asset\":%d,\"width\":%d,\"height\":%d,\"x\":%d,\"bottom\":%d,\"ms\":%.6f}',field,#times+1,i,emu.read(a+6,mt),emu.read(a+4,mt),emu.read(a+5,mt),emu.read16(a,mt),emu.read16(a+2,mt),ms)end
 end,emu.cpuType.sa1)
end
if labels.flame_direct_row then
 local active=false;local f=assert(io.open(output..'/flame_direct.jsonl','w'))
 cb('sa1_left_hint_draw',function()active=emu.read16(0x3e,emu.memType.sa1Memory)==31 end,emu.cpuType.sa1)
 cb('flame_direct_row',function()
  if not active then return end
  local mt=emu.memType.sa1Memory
  f:write(string.format('{"job":%d,"row":%d,"width":%d,"cur":%d}\\n',#times+1,emu.read16(0xa0,mt),emu.read16(0x34,mt),emu.read16(0x90,mt)));f:flush()
 end,emu.cpuType.sa1)
 cb('left_hint_finished',function()active=false end,emu.cpuType.sa1)
end
if labels.direct_left_row then
 local active=false;local f=assert(io.open(output..'/direct_left.jsonl','w'))
 cb('sa1_left_hint_draw',function()active=true end,emu.cpuType.sa1)
 cb('direct_left_row',function()
  if not active then return end
  local mt=emu.memType.sa1Memory
  f:write(string.format('{"job":%d,"row":%d,"asset":%d,"width":%d,"cur":%d}\\n',#times+1,emu.read16(0xa0,mt),emu.read16(0x3e,mt),emu.read16(0x34,mt),emu.read16(0x90,mt)));f:flush()
 end,emu.cpuType.sa1)
 cb('left_hint_finished',function()active=false end,emu.cpuType.sa1)
end
if labels.sa1_output_done then cb('sa1_output_done',function()
 local n=0
 if prebankDma then
  local mt=emu.memType.sa1Memory;local count=emu.read16(0x11a,mt)
  local base=emu.read16(0x19a,mt);local gen=emu.read16(0x198,mt)
  local page=gen%2==1 and 0x3000 or 0;local bytes,cost=0,0
  local table=(emu.read16(0x102,mt)&255)*65536+base+0x6600
  assert(count<=48,'prebank descriptor overflow')
  for i=0,count-1 do
   local a=0x430800+i*6;local len=emu.read16(a,mt);local src=(emu.read16(a+2,mt)-base)&65535
   local dst=emu.read16(a+4,mt)
   assert(len>0 and len%32==0 and src>=1024 and src+len<=24576,'prebank source extent invalid')
   assert(dst==page+src//2-496 and dst+len//2<=page+0x3000,'prebank absolute destination invalid')
   bytes=bytes+len
   cost=cost+len+len//32+len//128+(prefixRefreshSixteenth and len//16 or 0)+PREFIXDESCCOST
   assert(emu.read16(table+i*4,mt)==bytes and emu.read16(table+i*4+2,mt)==cost,'prebank cumulative cost differs from independent formula')
  end
  assert(bytes==emu.read16(0x118,mt),'prebank transfer bytes differ')
 end
 if splitViewports then
  local mt=emu.memType.sa1Memory;n=emu.read16(0x11a,mt)
  assert(n<=48,'split DMA metadata overflow')
  assert(emu.read16(0x19a,mt)==0x400,'split base was not restored')
  local bytes=0
  for i=0,n-1 do
   local a=0x430800+i*6;local len=emu.read16(a,mt);local src=emu.read16(a+2,mt);local dst=emu.read16(a+4,mt)
   local pos=src&0x3ff
   assert(len>0 and pos>=0x100 and pos+len<=0x300 and len%32==0,'split descriptor crosses viewport half')
   local original=(src&0x7c00)-0x400+pos-0x100+((src&0x8000)~=0 and 0x200 or 0)
   assert(original>=1024 and original+len<=24576 and dst*2+992==original,'split descriptor source/VRAM mismatch')
   bytes=bytes+len
  end
  assert(bytes==emu.read16(0x118,mt),'split transfer bytes differ')
 end
 outputJobs[#outputJobs+1]=string.format('{\"field\":%d,\"totalOutputMs\":%.6f,\"splitDescriptorsVerified\":%d}',field,(emu.getState().masterClock-sa1begin)/21477.272,n)
end,emu.cpuType.sa1)end
if prebankDma then
 local f=assert(io.open(output..'/prebank_dma_verified.jsonl','w'))
 cb('pipe_setup_transfer',function()
  local mt=emu.memType.snesMemory;local b=0x7e0000
  local r=b+labels.pipe_records+emu.read16(b+labels.pipe_record_offset,mt)
  local gen=emu.read16(r+8,mt);local page=gen%2==1 and 0x3000 or 0
  assert(emu.read16(r+6,mt)==page,'prebank generation/page ownership mismatch')
  assert(emu.read16(b+labels.fx4_page,mt)~=page,'prebank transfer targets visible page')
  local base=emu.read16(r,mt)&0x8400;local cursor=emu.read16(r+4,mt)
  local finish=emu.read16(r+2,mt)
  assert(cursor<=finish and finish<=48*6,'prebank WRAM extent invalid')
  for i=cursor,finish-1,6 do
   local a=r+208+i;local len=emu.read16(a,mt);local src=(emu.read16(a+2,mt)-base)&65535
   assert(emu.read16(a+4,mt)==page+src//2-496,'prebank resumed destination invalid')
   assert(src>=1024 and src+len<=24576,'prebank resumed source invalid')
  end
  f:write(string.format('{"generation":%d,"page":%d,"cursor":%d,"descriptors":%d}\\n',gen,page,cursor,finish//6));f:flush()
 end)
 if dmaShortIo then cb('pipe_fast_groups_done',function()
  local s=emu.getState()
  assert(s['cpu.dbr']==0x7e and s['cpu.d']==0,'DMA short I/O did not restore DB/D')
 end)end
end
if labels.sa1_dirty_done then
 cb('sa1_dirty_done',function()
 if pipeline then jobSequence=jobSequence+1;assert(emu.read16(0x198,emu.memType.sa1Memory)==jobSequence,'SA-1 job duplicated or skipped')end
dirtyDone=emu.getState().masterClock;dirtyMs=(dirtyDone-sa1begin)/21477.272 end,emu.cpuType.sa1)
 cb('sa1_clear_done',function()clearDone=emu.getState().masterClock;clearMs=(clearDone-dirtyDone)/21477.272 end,emu.cpuType.sa1)
 cb('sa1_native_done',function()nativeDone=emu.getState().masterClock;nativeMs=(nativeDone-drawbegin)/21477.272 end,emu.cpuType.sa1)
end
if labels.sa1_mask_clear then
 local f=assert(io.open(output..'/mask_clear.jsonl','w'))
 cb('sa1_clear_done',function()
  local mt=emu.memType.sa1Memory
  local bytes=emu.read16(0x1ac,mt);local bounds=0
  for r=0,23 do local a=0x120+r*4;bounds=bounds+math.max(0,emu.read16(a+2,mt)-emu.read16(a,mt))*8 end
  f:write(string.format('{"generation":%d,"bytes":%d,"boundsBytes":%d,"ms":%.6f}\\n',emu.read16(0x198,mt),bytes,bounds,clearMs));f:flush()
 end,emu.cpuType.sa1)
end
cb('sa1_draw_start',function()drawbegin=emu.getState().masterClock;bgMs=(drawbegin-clearDone)/21477.272 end,emu.cpuType.sa1)
cb('sa1_draw_done',function()
 local now=emu.getState().masterClock
 local mt=emu.memType.sa1Memory;local n=emu.read16(0x106,mt);local trace={}
 for _,a in ipairs({0x108,0x10a,0x10c,0x106})do local v=emu.read16(a,mt);trace[#trace+1]=string.char(v&255,v>>8)end
 for i=0,n*10-1 do trace[#trace+1]=string.char(emu.read(0x430000+i,mt))end
 packetTrace:write(table.concat(trace))
 if pipeline then
  local cpuMt=emu.memType.snesMemory;local slot=emu.read16(0x7e0000+labels.pipe_render_slot,cpuMt)
  local gen=emu.read16(0x7e0000+labels.pipe_records+slot*512+8,cpuMt)
  if DENSE_TILES and (captureGeneration(gen) or boundsFrames) then
   local bank=emu.read16(0x102,mt);local base=emu.read16(0x19a,mt);local t={}
   if splitViewports then
    bank=bank&255
    assert(base==0x400 and bank>=0x40 and bank<=0x42,'split framebuffer bank/base invalid bank='..bank..' base='..base)
    for y=0,191 do for half=0,1 do for x=32,95 do t[#t+1]=string.char(emu.read(bank*65536+base+half*0x8000+y*128+x,mt))end end end
   else for i=0,24575 do t[#t+1]=string.char(emu.read((bank&255)*65536+base+i,mt))end end
   local fb=table.concat(t)
   if boundsFrames then boundsFrames:write(string.char(gen&255,gen>>8)..fb);boundsFrames:flush()end
   if captureGeneration(gen) then completedFrames[gen]=fb end
  end
  if captureGeneration(gen) then local t={};for i=0,n*10-1 do t[#t+1]=string.char(emu.read(0x430000+i,mt))end;completedPackets[gen]=table.concat(t)end
 end
 local dirtyBytes=0
 for r=0,23 do local a=0x120+r*4;dirtyBytes=dirtyBytes+math.max(0,emu.read16(a+2,emu.memType.sa1Memory)-emu.read16(a,emu.memType.sa1Memory))*8 end
 if presents==0 then
  dump('first_bw.bin',emu.memType.snesSaveRam,0,65536)
  dump('first_iram.bin',emu.memType.sa1InternalRam,0,2048)
 end
 local parts={};for name,v in pairs(cpuParts)do parts[#parts+1]=string.format('"%s":%.6f',name,v)end
 times[#times+1]=string.format('{"field":%d,"clearAndBgMs":%.6f,"drawMs":%.6f,"totalSa1Ms":%.6f,"dirtyMs":%.6f,"clearMs":%.6f,"bgMs":%.6f,"nativeMs":%.6f,"compactMs":%.6f,"logicMs":%.6f,"dirtyBytes":%d,"cpuParts":{%s}}',field,(drawbegin-sa1begin)/21477.272,(now-drawbegin)/21477.272,(now-sa1begin)/21477.272,dirtyMs,clearMs,bgMs,nativeMs,(now-nativeDone)/21477.272,logicMs,dirtyBytes,table.concat(parts,','))
end,emu.cpuType.sa1)
if labels.pipe_fast_begin then
 local fastClock,fastBytes,fastCount,fastLine=0,0,0,0
 local fastLog=assert(io.open(output..'/fast_dma.jsonl','w'))
 local rejectedLog=assert(io.open(output..'/rejected_dma.jsonl','w'))
 cb('pipe_fast_unavailable',function()
  local mt=emu.memType.snesMemory;local base=0x7e0000
  local record=base+labels.pipe_records+emu.read16(base+labels.pipe_record_offset,mt)
  rejectedLog:write(string.format('{"field":%d,"gen":%d,"bytes":%d,"count":%d,"cost":%d,"available":%d}\\n',field,emu.read16(record+8,mt),emu.read16(record+34,mt),(emu.read16(record+2,mt)-emu.read16(record+4,mt))/6,emu.read16(base+labels.pipe_dma_chunk,mt),emu.read16(base+labels.pipe_available,mt)));rejectedLog:flush()
 end)
 cb('pipe_fast_begin',function()
  local st=emu.getState();assert(st['ppu.forcedBlank'] or st['ppu.scanline']>=225,'VRAM DMA began outside actual blank period')
  if scenario:match('tracedma') then
   local st=emu.getState();local f=assert(io.open(output..'/cc_state.jsonl','a'))
   f:write(string.format('{"field":%d,"source":%d,"dest":%d,"active":%s,"blank":%s,"line":%d}\\n',field,st['cart.coprocessor.dmaSrcAddr'],st['cart.coprocessor.dmaDestAddr'],tostring(st['cart.coprocessor.charConvDmaActive']),tostring(st['ppu.forcedBlank']),st['ppu.scanline']));f:close()
   if presents==0 then
    local f=assert(io.open(output..'/before_dma_bw.bin','wb'));local a={}
    for i=0,24575 do a[#a+1]=string.char(emu.read(1024+i,emu.memType.snesSaveRam))end
    f:write(table.concat(a));f:close()
   end
  end
  local mt=emu.memType.snesMemory;local record=0x7e0000+labels.pipe_records+emu.read16(0x7e0000+labels.pipe_record_offset,mt)
  fastClock=emu.getState().masterClock;fastLine=emu.getState()['ppu.scanline']
  fastBytes=emu.read16(record+34,mt);fastCount=(emu.read16(record+2,mt)-emu.read16(record+4,mt))/6
 end)
 cb('pipe_fast_done',function()
  local st=emu.getState()
  assert(st['ppu.forcedBlank'] or st['ppu.scanline']>=225,'VRAM DMA ended outside actual blank period')
  if scenario:match('tracedma') and presents==0 then
   local f=assert(io.open(output..'/beforeflip_vram.bin','wb'));local a={}
   for i=0,65535 do a[#a+1]=string.char(emu.read(i,emu.memType.snesVideoRam))end
   f:write(table.concat(a));f:close()
  end
  fastLog:write(string.format('{"field":%d,"bytes":%d,"count":%d,"line":%d,"endLine":%d,"ms":%.6f}\\n',field,fastBytes,fastCount,fastLine,st['ppu.scanline'],(st.masterClock-fastClock)/21477.272));fastLog:flush()
 end)
end
if labels.fx_obj_upload_done then cb('fx_obj_upload_done',function()
 if field>90 then
  local st=emu.getState()
  assert(st['ppu.forcedBlank'] or st['ppu.scanline']>=225,'OAM DMA ended outside actual blank period')
 end
end)end
if labels.dense_vram_overflow then cb('dense_vram_overflow',function()error('packed image exceeds one VRAM page')end,emu.cpuType.sa1)end
if vramPrefetch3 then
 emu.addMemoryCallback(function(address,value)
  if field>85 then
   local st=emu.getState()
   assert(st['ppu.forcedBlank'] or st['ppu.scanline']>=225,'BG1 map changed outside actual blank period')
  end
 end,emu.callbackType.write,0x2107,0x2107,emu.cpuType.snes,emu.memType.snesMemory)
end
if labels.pipe_flip then cb('pipe_flip',function()flipBegin=emu.getState().masterClock;pageCommit=nil end)end
if labels.pipe_flip_prepared then
 local f=assert(io.open(output..'/flip_preparation.jsonl','w'))
 local prepared=nil
 cb('pipe_flip_prepared',function()
  local s=emu.getState();local channels={}
  for c=1,7 do
   local p='dmaController.channel['..c..'].'
   local bank=s[p..'srcBank'];local address=s[p..'hdmaTableAddress']
   assert(type(bank)=='number' and type(address)=='number','HDMA state fields missing')
   if bank==0x7e then assert(address<0x1c00 or address>=0x1e00,'HDMA table aliases flip metadata')end
   if s[p..'hdmaIndirectAddressing'] then
    local indirectBank=s[p..'hdmaBank'];local indirect=s[p..'transferSize']
    assert(type(indirectBank)=='number' and type(indirect)=='number','indirect HDMA state fields missing')
    if indirectBank==0x7e then assert(indirect<0x1c00 or indirect>=0x1e00,'indirect HDMA data aliases flip metadata')end
   end
   channels[#channels+1]=string.format('{"channel":%d,"bank":%d,"table":%d}',c,bank,address)
  end
  prepared={clock=s.masterClock,line=s['ppu.scanline'],field=field,channels=table.concat(channels,',')}
 end)
 cb('pipe_flip_ppu',function()
  assert(prepared,'flip PPU update before preparation')
  local s=emu.getState();local line=s['ppu.scanline']
  assert((line>=203 or line<=21) and (s['ppu.forcedBlank'] or line>=225),'early flip PPU update outside reserved blank')
  f:write(string.format('{"field":%d,"prepareField":%d,"prepareLine":%d,"ppuLine":%d,"waitTicks":%d,"channels":[%s]}\\n',field,prepared.field,prepared.line,line,s.masterClock-prepared.clock,prepared.channels));f:flush();prepared=nil
 end)
end
if labels.fd_flip then
 local f=assert(io.open(output..'/map_delta.jsonl','w'))
 local begin=0;local count=0
 cb('fd_flip',function()
  local st=emu.getState();begin=st.masterClock
  local slot=emu.read16(0x7e0000+labels.pipe_target_slot,emu.memType.snesMemory)
  count=emu.read16(0x7e0000+labels.pipe_records+slot*512+62,emu.memType.snesMemory)
  if count>0 then assert(st['ppu.forcedBlank'] or st['ppu.scanline']>=225,'map update started outside actual blank')end
 end)
 cb('fd_flip_done',function()
  local st=emu.getState()
  if count>0 then assert(st['ppu.forcedBlank'] or st['ppu.scanline']>=225,'map update ended outside actual blank')end
  f:write(string.format('{"field":%d,"count":%d,"ms":%.6f,"line":%d}\\n',field,count,(st.masterClock-begin)/21477.272,st['ppu.scanline']));f:flush()
 end)
end
cb('dma_finished',function()
 presents=presents+1
 if pipeline then local mt=emu.memType.snesMemory;local slot=emu.read16(0x7e0000+labels.pipe_front_slot,mt);assert(emu.read16(0x7e0000+labels.pipe_records+slot*512+8,mt)==presents,'pipeline skipped or reordered a frame')end
 local state=emu.getState();local line=(pageCommit and pageCommit.line) or state['ppu.scanline']
 local commitField=(pageCommit and pageCommit.field) or field
 local visibleField=commitField+(line>=203 and line<225 and 1 or 0)
 assert(line<=21 or line>=203,'page flip occurred during visible lines field='..field..' line='..line)
 presentationTimes[#presentationTimes+1]=string.format('{"field":%d,"visibleField":%d,"line":%d,"clock":%d,"dmaBytes":%d,"readyLine":%d,"waitMs":%.6f,"transferMs":%.6f,"flipMs":%.6f}',field,visibleField,line,state.masterClock,emu.read16(0x7e0000+labels.fx4_dma_bytes,emu.memType.snesMemory),readyLine,waitMs,(state.masterClock-startClock)/21477.272,(state.masterClock-flipBegin)/21477.272)
 if captureGeneration(presents) then
  local n=string.format('present%05d',presents)
  local record=nil
  if pipeline then
   local mt=emu.memType.snesMemory;local slot=emu.read16(0x7e0000+labels.pipe_front_slot,mt)
   record=0x7e0000+labels.pipe_records+slot*512
   local gen=emu.read16(record+8,mt);assert(gen==presents,'pipeline skipped or reordered a frame')
   local page=emu.read16(record+6,mt)*2
   local bg1Chr=state['ppu.layers[0].chrAddress']*2
   local bg1Map=state['ppu.layers[0].tilemapAddress']*2
   local bg2Chr=state['ppu.layers[1].chrAddress']*2
   local bg2Map=state['ppu.layers[1].tilemapAddress']*2
   assert(bg1Chr==math.floor(page/8192)*8192,'PPU BG1 CHR base differs from the rendered page')
   assert(bg1Map==(vramFourOwned and page+0x2800 or fixedMap and 0xc000 or vramFourShared and 0xc000 or vramPrefetch3 and page+0x800 or 0xc000),'PPU BG1 map base differs')
   assert(bg2Chr==(vramFourOwned and 0xc000 or (fixedMap or vramFifo) and 0xa000 or vramFourShared and 0x8000 or NATIVENEAR and 0 or 0xc000),'PPU BG2 CHR base differs')
   assert(bg2Map==0xc000,'PPU BG2 map base differs')
   local p=assert(io.open(output..'/'..n..'_ppu.json','w'))
   p:write(string.format('{"bg1Chr":%d,"bg1Map":%d,"bg2Chr":%d,"bg2Map":%d}',bg1Chr,bg1Map,bg2Chr,bg2Map));p:close()
   if NATIVEBACKGROUND then dump(n..'_record.bin',emu.memType.snesMemory,record,512)end
   if fixedMapDelta then dump(n..'_map_delta.bin',emu.memType.snesMemory,0x7e0000+labels.fdStorage+slot*1472,1472)end
   if COMPILEDGROUND then dump(n..'_ground_h.bin',emu.memType.snesMemory,0x7e0000+emu.read16(record+26,mt),270)end
   for i=0,23 do assert(emu.read(i,emu.memType.snesSpriteRam)==emu.read(record+64+i,mt),'pipeline OAM differs field='..field..' gen='..presents..' byte='..i..' actual='..emu.read(i,emu.memType.snesSpriteRam)..' expected='..emu.read(record+64+i,mt))end
   if NATIVENEAR then
    local expected=emu.read16(record+192,mt)|0x0aaa
    local actual=emu.read16(512,emu.memType.snesSpriteRam)
    assert((actual&0x0fff)==(expected&0x0fff),'player high OAM differs')
    dump(n..'_oam.bin',emu.memType.snesSpriteRam,0,544)
    dump(n..'_palette.bin',emu.memType.snesCgRam,0,512)
   else
    for i=0,7 do assert(emu.read(512+i,emu.memType.snesSpriteRam)==emu.read(record+192+i,mt),'pipeline high OAM differs')end
   end
   local f=assert(io.open(output..'/'..n..'_fb.bin','wb'));f:write((assert(completedFrames[gen],'missing completed snapshot')));f:close();completedFrames[gen]=nil
  elseif padded then
   local f=assert(io.open(output..'/'..n..'_fb.bin','wb'));local t={}
   for y=0,191 do for x=0,127 do t[#t+1]=string.char(emu.read(y*256+64+x,emu.memType.snesSaveRam))end end
   f:write(table.concat(t));f:close()
  else dump(n..'_fb.bin',emu.memType.snesSaveRam,0,24576)end
  if NATIVEBACKGROUND and record then dump(n..'_background.bin',emu.memType.snesSaveRam,0x30000+emu.read16(record+40,emu.memType.snesMemory),2048)end
  dump(n..'_vram.bin',emu.memType.snesVideoRam,0,65536)
  local count=emu.read16(pipeline and record+16 or 0x3106,emu.memType.snesMemory)
  local f=assert(io.open(output..'/'..n..'_meta.bin','wb'))
  local t={}
  local addresses=pipeline and {record+10,record+12,record+14,record+16,0x7e0000+labels.fx4_page} or {0x3108,0x310a,0x310c,0x3106,0x7e0000+labels.fx4_page}
  for _,a in ipairs(addresses)do
   local v=emu.read16(a,emu.memType.snesMemory);t[#t+1]=string.char(v&255,v>>8)
  end
  if pipeline then
   local gen=emu.read16(record+8,emu.memType.snesMemory)
   t[#t+1]=assert(completedPackets[gen],'missing completed packet');completedPackets[gen]=nil
  else
   for i=0,count*10-1 do t[#t+1]=string.char(emu.read(0x430000+i,emu.memType.snesMemory))end
  end
  f:write(table.concat(t));f:close()
 end
end)
emu.addEventCallback(function()
 local input={a=true}
 if scenario:match('move') then
  local phase=logic%240
  input.right=phase<60;input.left=phase>=120 and phase<180
  input.up=phase>=60 and phase<120;input.down=phase>=180
 end
 emu.setInput(input,0)
end,emu.eventType.inputPolled)
emu.addEventCallback(function()
 field=field+1
 if NATIVENEAR and presents>0 then
  for i=0,31 do
   local fx=emu.read(32+i,emu.memType.snesCgRam)
   local near=emu.read(480+i,emu.memType.snesCgRam)
   if fx~=expectedPalette[i+1] or near~=expectedPalette[i+1] then
    local f=assert(io.open(output..'/failure.txt','w'))
    f:write('CGRAM changed field='..field..' byte='..i..' fx='..fx..' near='..near..' expected='..expectedPalette[i+1]);f:close();emu.stop(1);return
   end
  end
 end
 local finished=field==maxframe or (targetPresents>0 and presents>=targetPresents)
 if finished then
  local f=assert(io.open(output..'/final_state.txt','w'));for k,v in pairs(emu.getState())do f:write(tostring(k)..'='..tostring(v)..'\\n')end;f:close()
 end
 if field==120 or finished then
  local f=assert(io.open(output..'/frame'..field..'.rgb','wb'));local t={}
  for _,v in ipairs(emu.getScreenBuffer())do t[#t+1]=string.char((v>>16)&255,(v>>8)&255,v&255)end
  f:write(table.concat(t));f:close()
 end
 if finished then
  local st=assert(io.open(output..'/end_state.txt','w'));for k,v in pairs(emu.getState())do st:write(tostring(k)..'='..tostring(v)..'\\n')end;st:close()
  dump('end_wram.bin',emu.memType.snesWorkRam,0,131072)
  finishedCapture=true
  packetTrace:close()
  local f=assert(io.open(output..'/summary.json','w'))
  f:write(string.format('{"fields":%d,"logic":%d,"presents":%d,"presentationTimes":[%s],"sa1Jobs":[%s],"cpuJobs":[%s],"outputJobs":[%s],"queueSamples":[%s],"objectJobs":[%s],"dmaJobs":[%s],"cpuStageJobs":[%s]}',field,logic,presents,table.concat(presentationTimes,','),table.concat(times,','),table.concat(cpuJobs,','),table.concat(outputJobs,','),table.concat(queueSamples,','),table.concat(objectJobs,','),table.concat(dmaJobs,','),table.concat(cpuStageJobs,',')));f:close()
  dump('iram.bin',emu.memType.sa1InternalRam,0,2048)
  emu.stop(0)
 end
end,emu.eventType.endFrame)
'''.replace('COMPACTGAME','true' if config.get('sa1GameCompact') else 'false').replace('GAMEBWBASE',str(0x430000 if config.get('sa1GameCompact') else 0x400000)).replace('GAMEOFFLOAD','true' if config.get('sa1Game') else 'false').replace('NATIVENEAR','true' if config.get('nativeNear',False) else 'false').replace('NATIVEBACKGROUND','true' if config.get('nativeBackground',False) else 'false').replace('CPUCODEBASE',str(config.get('cpuCodeBank',0x7f)*65536)).replace('LABELS',lua(labels)).replace('CALLS',lua(calls)).replace('OUTDIR',lua(dest.as_posix())).replace('MAXFRAME',str(args.frames)).replace('TARGETPRESENTS',str(args.presents)).replace('SCENARIO',lua(args.scenario)).replace('PADDED','true' if config.get('paddedFramebuffer',False) else 'false').replace('DEPTH',str(config.get('pipelineDepth',3))).replace('PIPELINE','true' if config.get('pipeline',False) else 'false')
    from sa1_patterns import dimensions
    patterns=dimensions()
    edge_bands={}
    if config.get('edgeBandGuard'):
        from analyze_sa1_edge_guard import bands
        rom=(BUILD/'MonoSHSA1_4bpp_game.sfc').read_bytes()
        for asset in (40,41):
            for width,height in patterns[asset]:
                if width>=32 and height>=24:edge_bands[f'{asset}_{width}_{height}']=[r for l,r in bands(rom,asset,width,height)]
    script=script.replace('EDGEBANDS',lua(edge_bands))
    script=script.replace('EDGEWIDTHTAG','true' if config.get('edgeBandGuard') else 'false')
    script=script.replace('EDGEJITMAX',str(config.get('edgeJitMax',64 if config.get('wideEdgeJit') else 32) if config.get('smallEdgeJit') else 0))
    script=script.replace('EDGETEMPLATES',lua((BUILD/'small_edge_templates.bin').as_posix()))
    script=script.replace('EXACTMASKBOUNDS','true' if config.get('maskBounds') else 'false')
    script=script.replace('IRQCODEBASE',str(0xc10000 if config.get('irqFastrom') and not config.get('gameIrqWram') else 0x7f0000))
    minimum=config.get('reverseExplosionsMinWidth',91)
    minimum_geometries=sorted(set(patterns[40])&set(patterns[41]))
    minimum_geometries=[list(g) for g in minimum_geometries if g[0]==minimum]
    if args.scenario.startswith('stackfixturemin'):assert minimum_geometries
    script=script.replace('STACKMINGEOMETRIES',lua(minimum_geometries))
    left_geometries=[]
    for i in range(6):
        for asset in ((0,1,2,3,4,5,13,14,31,39,40,41,42) if config.get('leftRuntimeScan') else (0,3,39,31) if config.get('leftFlameHints') else (0,3,39) if config.get('leftExplosionHints') else (0,3)):
            sizes=sorted((w,h) for w,h in patterns[asset] if w>=64 if config.get('leftRuntimeScan') or w>=90)
            if asset==39 and config.get('leftExplosionHints'):
                sizes=sorted((w,h) for w,h in patterns[asset] if w>=config['leftExplosionHintsMinWidth'])
            if asset==31 and config.get('leftFlameHints'):
                sizes=sorted((w,h) for w,h in patterns[asset] if w>=64)
            if not sizes:continue
            left_geometries.append([asset,*sizes[min(len(sizes)-1,i*(len(sizes)-1)//5)]])
    if args.scenario.startswith('leftfixtureflame'):
        left_geometries=[[31,w,h] for w,h in sorted(patterns[31]) if w>=64]
        assert len(left_geometries)==2
    if args.scenario.startswith('leftfixtureindexed'):
        left_geometries=[[a,w,h] for a in (0,2,3,5) for w,h in sorted(patterns[a]) if w>=64]
    script=script.replace('LEFTFIXTUREGEOMETRIES',lua(left_geometries))
    script=script.replace('SPLITFIXTURES',lua([j['draws'] for j in split_jobs]))
    script=script.replace('OPAQUETARGETS',lua([[w,h] for w,h in sorted(patterns[40]) if 49<=w<=79]))
    script=script.replace('OPAQUEFRONTS',lua([[a,w,h] for a in (39,40,41) for w,h in sorted(patterns[a]) if w>=64]))
    script=script.replace('OPAQUEINLINERAW','true' if config.get('opaquePrefixInlineRaw') else 'false')
    script=script.replace('DENSE_TILES','true' if (config.get('denseTiles') or config.get('cpuPack') or config.get('directSparse')) else 'false')
    script=script.replace('VRAMPREFETCH3','true' if config.get('vramPrefetch3') else 'false')
    script=script.replace('VRAMFOURSHARED','true' if config.get('vramFourShared') else 'false')
    script=script.replace('VRAMFIFO','true' if config.get('vramFifo') else 'false')
    script=script.replace('VRAMFOUROWNED','true' if config.get('vramFourOwned') else 'false')
    script=script.replace('FIXEDMAPDELTADMA','true' if config.get('fixedMapDeltaDma') else 'false')
    script=script.replace('FIXEDMAPDELTA','true' if config.get('fixedMapDelta') else 'false')
    script=script.replace('FIXEDMAP','true' if config.get('fixedMap') else 'false')
    script=script.replace('PREBANKDMA','true' if config.get('prebankDma') else 'false')
    script=script.replace('DMASHORTIO','true' if config.get('dmaShortIo') else 'false')
    script=script.replace('PREFIXREFRESHSIXTEENTH','true' if config.get('prefixRefreshSixteenth') else 'false')
    script=script.replace('FRONTPROBEGEN',str(config.get('fixedFrontProbeGeneration',0)))
    script=script.replace('PREFIXDESCCOST',str(64-(7 if config.get('dmaWordStart') else 0)-config.get('prebankDescriptorCostDiscount',0)))
    script=script.replace('SPLITVIEWPORTS','true' if config.get('splitViewports') else 'false')
    script=script.replace('PACKETOFFLOAD','true' if config.get('packetOffload') else 'false')
    script=script.replace('PREFIXONEPASS','true' if config.get('prefixOnePass') else 'false')
    script=script.replace('PREFIXFULLRESERVE',str(config.get('prefixFullReserve',384)))
    script=script.replace('PARTIALTRANSFERRESERVE',str(config.get('partialTransferReserve',0)))
    script=script.replace('TRANSFERREQUESTLINE',str(config.get('transferRequestLine',197)))
    script=script.replace('PREARMTRANSFERLINE',str(config.get('prearmTransferLine',0)))
    script=script.replace('DMAUNROLLCOUNT',str(config.get('dmaUnrollCount',12)))
    script=script.replace('DMAWORDSTART','true' if config.get('dmaWordStart') else 'false')
    script=script.replace('PACKETIRAMARRAYS','true' if config.get('packetIramArrays') else 'false')
    script=script.replace('EXPECTEDPALETTE',lua(list((BASE/'assets4/palette4.bin').read_bytes())))
    script=script.replace('COMPILEDGROUND','true' if config.get('compiledGround') else 'false')
    # stop要求後にもMesenがcallbackを進める場合がある。最初のexec異常を保持する。
    script=script.replace('emu.addMemoryCallback(function(address,value)\n','emu.addMemoryCallback(function(address,value)\n if finishedCapture then return end\n')
    script=script.replace('emu.stop(1)','finishedCapture=true;emu.stop(1)')
    path=dest/'test.lua';path.write_text(script)
    exe=prepare_runtime(MESEN_EXE)
    settings=exe.parent/'settings.json';cfg=json.loads(settings.read_text());cfg['Snes'].update(DisableFrameSkipping=True,Port1={'Type':'SnesController'});settings.write_text(json.dumps(cfg))
    result=subprocess.run([str(exe),'--testRunner',f'--timeout={args.timeout}','--doNotSaveSettings','--enableStdout',str(BUILD/'MonoSHSA1_4bpp_game.sfc'),str(path)],cwd=exe.parent,capture_output=True,timeout=args.timeout+10,creationflags=subprocess.CREATE_NO_WINDOW)
    (dest/'emulator.log').write_bytes(result.stdout+result.stderr)
    if (dest/'failure.txt').exists():raise AssertionError((dest/'failure.txt').read_text())
    if result.returncode:print((result.stdout+result.stderr).decode(errors='replace'));raise RuntimeError('Mesen failed')
    if config.get('fixedFrontProbeGeneration'):
        rows=[json.loads(x) for x in (dest/'fixed_front_probe.jsonl').read_text().splitlines()]
        assert len(rows)==1 and rows[0]['generation']==config['fixedFrontProbeGeneration']
        result=dict(probe=rows[0],romSha256=config['romSha256'],goal60fpsAchieved=False,
            runtimeMasksDescriptorsPrefixesRegistersVerified=True,
            stoppedBeforeReturningToDisplayPath=True,pixelMatchedPresents=verify_pixels(dest,labels,config),
            maskBoundsVerified=verify_mask_bounds(dest,False))
        (dest/'probe_result.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result));return
    for f in dest.glob('*.rgb'):
        raw=f.read_bytes();Image.frombytes('RGB',(256,len(raw)//768),raw).save(f.with_suffix('.png'))
    summary=json.loads((dest/'summary.json').read_text())
    print(json.dumps({k:v for k,v in summary.items() if k not in ('sa1Jobs','presentationTimes','cpuJobs','outputJobs','queueSamples','objectJobs','dmaJobs','cpuStageJobs')}))
    assert summary['presents']>0,'SA-1 game never presented an image'
    print('SA-1 max ms:',max(x['totalSa1Ms'] for x in summary['sa1Jobs']))
    summary['pixelMatchedPresents']=verify_pixels(dest,labels,config)
    ppu_files=list(dest.glob('present*_ppu.json'))
    summary['hardwarePpuReferencesVerified']=bool(config.get('pipeline') and len(ppu_files)==summary['pixelMatchedPresents'])
    summary['romSha256']=config['romSha256']
    summary['irqMathRegistersVerified']=bool(config.get('pipeline'))
    summary['labelsSha256']=hashlib.sha256((BUILD/'game.lbl').read_bytes()).hexdigest()
    intervals=np.diff([p['visibleField'] for p in summary['presentationTimes'][2:]])
    summary['presentationFieldIntervals']={str(int(k)):int(v) for k,v in zip(*np.unique(intervals,return_counts=True))}
    summary['stalledTailFields']=max(0,summary['fields']-summary['presentationTimes'][-1]['visibleField'])
    summary['goal60fpsAchieved']=bool(len(intervals)>=120 and np.all(intervals==1) and summary['stalledTailFields']<=1)
    if args.scenario.startswith(('stackfixture','transferfixture')):
        summary['fixturePresentationEveryField']=summary['goal60fpsAchieved']
        summary['goal60fpsAchieved']=False
    if split_jobs:
        from sa1_split_fixture import verify
        summary['splitViewportFixture']=verify(dest,split_jobs,summary)
        summary['fixturePresentationEveryField']=summary['goal60fpsAchieved']
        summary['goal60fpsAchieved']=False
    if labels.get('flame_direct_row'):
        events=[json.loads(line) for line in (dest/'flame_direct.jsonl').read_text().splitlines()]
        summary['flameDirectCoverage']=dict(rows=len(events),jobs=len({e['job'] for e in events}))
        if args.scenario.startswith('leftfixtureflame') and not config.get('flameDirectHintsBypass'):
            assert len(events)>120
    if labels.get('direct_left_row'):
        events=[json.loads(line) for line in (dest/'direct_left.jsonl').read_text().splitlines()]
        summary['directLeftCoverage']=dict(rows=len(events),jobs=len({e['job'] for e in events}),assets=sorted({e['asset'] for e in events}))
    if labels.get('opaque_prefix_patch_done'):
        summary['opaquePrefixCoverage']=opaque_prefix_coverage(dest)
        if args.scenario.startswith('opaquefixture'):
            assert summary['pixelMatchedPresents']>=240 and summary['stalledTailFields']<=1
            assert summary['opaquePrefixCoverage']['advancedRows']>=120
            assert set(summary['opaquePrefixCoverage']['hintFormats'])==({'0'} if config.get('opaquePrefixInlineRaw') else {'0','128','129'})
            summary['opaqueFixtureCoverage']=verify_opaque_fixture_coverage(dest)
    if 'auditgame' in args.scenario:
        summary['gameStateAudit']=verify_game_state_audit(dest,summary['logic'],args.scenario)
    if args.scenario.startswith('stackfixturemin'):
        summary['minimumClipCoverage']=verify_minimum_clip_coverage(dest,config)
    if args.scenario.startswith('clipfixture'):
        assert summary['pixelMatchedPresents']>=240
        summary['clipCacheCoverage']=verify_clip_cache_coverage(dest)
    if 'tracebounds' in args.scenario:
        summary['maskBoundsVerified']=verify_mask_bounds(dest,config.get('maskBounds',False))
        assert len(summary['sa1Jobs'])<=summary['maskBoundsVerified']['jobs']<=len(summary['sa1Jobs'])+1
    (dest/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    if args.scenario.startswith('stackfixture'):
        assert summary['stalledTailFields']<=1, 'stack clipping fixture stopped presenting'
        assert summary['presents']>=2*13*7, 'stack clipping fixture did not exercise both heights'
        if 'wide' in args.scenario:
            assert summary['presents']>=3*13*7, 'stack clipping fixture did not exercise width 91'
    if args.scenario.startswith('leftfixtureexplosion'):
        assert summary['stalledTailFields']<=1 and summary['presents']>=189, 'left explosion fixture did not complete its geometry/position cycle'
    if args.scenario.startswith('leftfixtureflame'):
        assert summary['stalledTailFields']<=1 and summary['presents']>=252, 'left flame fixture did not complete its geometry/position/phase cycle'
        summary['flameFixtureCoverage']=verify_flame_fixture_coverage(dest)
        (dest/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    if args.scenario.startswith('leftfixtureindexed'):
        summary['directLeftFixtureCoverage']=verify_direct_left_fixture_coverage(dest)
        assert summary['pixelMatchedPresents']>=1450 and summary['stalledTailFields']<=1
        assert summary['directLeftCoverage']['rows']>1000 and summary['directLeftCoverage']['assets']==[0,2,3,5]
        (dest/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('Pixel-matched presents:',summary['pixelMatchedPresents'])

if __name__=='__main__':main()
