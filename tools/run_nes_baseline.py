"""NES版の既存compiled sprite本体を隔離NROMへ載せ、同じMesenで測る。"""

import hashlib
import json
import re
import subprocess

from run_probe import BUILD, NES_ROOT, MESEN_EXE, lua, prepare_runtime


def main():
    dest=BUILD/'nes_baseline';dest.mkdir(parents=True,exist_ok=True)
    original=NES_ROOT/'src/gen/sprite_Tree0.s'
    source=original.read_text(encoding='utf-8')
    sizes=(0,3,7,11,15)
    blocks=[]
    for index in sizes:
        name=f'_draw_Tree0_{index:02}_s0'
        body=re.search(r'(?ms)^\.proc '+name+r'\n(.*?)^\.endproc',source).group(1)
        assert not re.search(r'\b(?:jsr|jmp)\b',body)
        body=body.replace('    rts','::return_'+str(index)+':\n    rts')
        blocks.append(f'.export {name},return_{index}\n.proc {name}\n'+body+'\n.endproc\n')
    asm='''
.setcpu "6502"
dst_ptr=$00
VBUF_STRIDE_PACKED=64
.segment "HEADER"
.byte "NES",$1A,2,0,2,0
.res 8,0
.segment "CODE"
.export reset
reset:
  sei
  cld
  ldx #$FF
  txs
  lda #0
  sta $2000
  sta $2001
  sta $0700
ready:
  lda #16
  sta $0702
wait_request:
  lda $0700
  beq wait_request
  sec
  sbc #1
  tax
  lda lows,x
  sta $02
  lda highs,x
  sta $03
  lda #0
  sta $00
  lda #$60
  sta $01
  jsr call_sprite
  lda #2
  sta $0702
  lda #0
  sta $0700
  jmp ready
call_sprite:
  jmp ($0002)
lows:
.byte '''+','.join(f'<_draw_Tree0_{i:02}_s0' for i in sizes)+'''
highs:
.byte '''+','.join(f'>_draw_Tree0_{i:02}_s0' for i in sizes)+'\n'+''.join(blocks)+'''
.segment "VECTORS"
.word reset,reset,reset
'''
    (dest/'probe.s').write_text(asm)
    (dest/'rom.cfg').write_text('''
MEMORY {
 H:start=0,size=16,file=%O;
 P:start=$8000,size=$7FFA,file=%O,fill=yes;
 V:start=$FFFA,size=6,file=%O;
}
SEGMENTS {HEADER:load=H,type=ro;CODE:load=P,type=ro;VECTORS:load=V,type=ro;}
''')
    subprocess.run(['ca65','-o',str(dest/'probe.o'),str(dest/'probe.s')],check=True)
    subprocess.run(['ld65','-C',str(dest/'rom.cfg'),'-o',str(dest/'probe.nes'),'-Ln',str(dest/'labels.txt'),str(dest/'probe.o')],check=True)
    labels={n:int(a,16) for a,n in re.findall(r'al ([0-9A-Fa-f]+) \.([^\s]+)',(dest/'labels.txt').read_text())}
    script='''
local labels=LABELS
local sizes=SIZES
local index=0
local active=nil
local begin=nil
local f=assert(io.open(REPORT,"w"))
for _,i in ipairs(sizes) do
  local first=labels[string.format("_draw_Tree0_%02d_s0",i)]
  local last=labels[string.format("return_%d",i)]
  emu.addMemoryCallback(function() begin=emu.getState()["cpu.cycleCount"] end,emu.callbackType.exec,first,first)
  emu.addMemoryCallback(function()
    local now=emu.getState()["cpu.cycleCount"]
    f:write(i.."\\t"..(now-begin+6).."\\n");f:flush()
  end,emu.callbackType.exec,last,last)
end
emu.addMemoryCallback(function(a,v) if v==2 then active=nil end end,emu.callbackType.write,0x0702,0x0702)
emu.addEventCallback(function()
  if active or emu.read(0x0702,emu.memType.nesMemory)~=16 then return end
  index=index+1
  if index>#sizes then f:close();emu.stop(0);return end
  active=true
  for i=0,3071 do emu.write(0x6000+i,0,emu.memType.nesMemory) end
  emu.write(0x0700,index,emu.memType.nesMemory)
end,emu.eventType.endFrame)
'''.replace('LABELS',lua(labels)).replace('SIZES',lua(list(sizes))).replace('REPORT',lua((dest/'cycles.tsv').as_posix()))
    (dest/'measure.lua').write_text(script)
    mesen=prepare_runtime(MESEN_EXE)
    run=subprocess.run([str(mesen),'--testRunner','--timeout=15','--doNotSaveSettings',str(dest/'probe.nes'),str(dest/'measure.lua')],cwd=mesen.parent,capture_output=True,timeout=25,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    (dest/'emulator.log').write_bytes(run.stdout+run.stderr)
    if run.returncode:raise RuntimeError('NES baseline failed')
    records=[]
    for line in (dest/'cycles.tsv').read_text().splitlines():
        index,cycles=map(int,line.split('\t'))
        row=dict(size_index=index,cpu_cycles=cycles,ms=cycles/(21_477_272/12)*1000)
        records.append(row);print(row)
    (dest/'results.json').write_text(json.dumps(dict(source_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
                                                   excludes='dispatch/banking/clear/PPU DMA',cases=records),indent=2)+'\n')


if __name__=='__main__':main()
