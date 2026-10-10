"""12KiB四面の各面へ配置表も保持し、表示直前のmap転送を省く。"""
import json,struct
from sa1_vram_four import change,sparse_map as shared_map

def ppu_layout(ppu,build):
 p=build/'native_near_packing.json';d=json.loads(p.read_text())
 far=list(range(0xc000,0xc600,32))+list(range(0xeb40,0xed40,32))
 assert len(far)==64
 old=d['farChrAddresses'];remap=dict(zip(old,far));saved=[bytes(ppu[a:a+32]) for a in old]
 for address in (0xc600,0xce00):
  for i in range(64):
   e=struct.unpack_from('<H',ppu,address+i*2)[0]
   struct.pack_into('<H',ppu,address+i*2,(e&~1023)|((remap[(e&1023)*32]-0xc000)//32))
 ppu[:0xc000]=bytes(0xc000)
 for page in range(4):
  a=page*0x3000+0x2800
  ppu[a:a+0x600]=struct.pack('<H',0x2400+128*(page&1))*768
 for a,data in zip(far,saved):ppu[a:a+32]=data
 assert not set(far)&set(d['nearChrAddresses'])
 d.update(farChrAddresses=far,farChrBase=0xc000);p.write_text(json.dumps(d,indent=2)+'\n')
 (build/'vram_four_owned_layout.json').write_text(json.dumps(dict(
  pages=[0,0x3000,0x6000,0x9000],dynamicCapacity=335,mapOffset=0x2800,
  skippedTiles=[320,368],farChrBase=0xc000,farChrAddresses=far),indent=2)+'\n')
 return ppu

def sparse_map(text):
 text=shared_map(text)
 text=change(text,'  sta smTile\nsm_descriptor:', '''  sta smTile
  clc
  adc #319
  sta $b0
sm_descriptor:''')
 return change(text,'  inc\n  iny\n  iny\n  dec smCount', '''  inc
  cmp $b0
  bne :+
  clc
  adc #48
:
  iny
  iny
  dec smCount''')

def cpu(text):
 text=change(text,'  lda #4\n  sta $2107','  lda #$14\n  sta $2107')
 return change(text,'  lda #0\n  sta $210b','  lda #$60\n  sta $210b')

def pipeline(text,build,sa1):
 text=change(text,'p3Queue: .res 4','p3Queue: .res 6')
 text=change(text,'  lda #$2000\n  sta p3NextPage','  lda #$1800\n  sta p3NextPage')
 text=change(text,'  lda p3Count\n  cmp #2\n','  lda p3Count\n  cmp #3\n')
 text=change(text,'  sta f:$00210b\n','  ora #$60\n  sta f:$00210b\n')
 text=change(text,'  lda fx4_page+1\n  ora #4\n  sta f:$002107',
             '  lda fx4_page+1\n  clc\n  adc #$14\n  sta f:$002107')
 ring=(sa1/'vram_prefetch_cpu.inc').read_text(encoding='utf-8')
 for name in ('p3Tail','p3Head'):
  ring=change(ring,'  lda '+name+'\n  eor #1\n  sta '+name,
              '  lda '+name+'\n  inc\n  cmp #3\n  bcc :+\n  lda #0\n:\n  sta '+name)
 ring=change(ring,'  adc #$2000\n','  adc #$1800\n')
 (build/'vram_four_owned_cpu.inc').write_text(ring,encoding='utf-8')
 return change(text,'.include "vram_prefetch_cpu.inc"','.include "vram_four_owned_cpu.inc"')
