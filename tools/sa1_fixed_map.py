"""固定タイル配置表と24KiBのVRAM二面で、配置表の毎フレーム転送を省く。"""
import json,struct


def change(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new,1)


def ppu_layout(ppu,build):
    path=build/'native_near_packing.json'
    d=json.loads(path.read_text())
    far=list(range(0xbc20,0xc000,32))+list(range(0xe900,0xed20,32))
    near=list(range(0xc680,0xc800,32))+list(range(0xcb80,0xce00,32))+list(range(0xce80,0xd000,32))+list(range(0xed20,0xef60,32))
    assert len(far)==64 and len(near)==62
    remap=dict(zip(d['farChrAddresses'],far))
    near_remap=dict(zip(d['nearChrAddresses'],near))
    saved={target:bytes(ppu[old:old+32]) for old,target in {**remap,**near_remap}.items()}
    maps=[]
    for address in (0xc600,0xce00):
        data=bytearray(ppu[address:address+128])
        for i in range(64):
            entry=struct.unpack_from('<H',data,i*2)[0]
            struct.pack_into('<H',data,i*2,(entry&~1023)|((remap[(entry&1023)*32]-0xa000)//32))
        maps.append(data)
    new=bytearray(65536)
    ground_end=int(json.loads((build/'native_far_packing.json').read_text())['groundEnd'],16)
    new[0xd000:ground_end]=ppu[0xd000:ground_end]
    new[0xf000:]=ppu[0xf000:]
    new[0xc800:0xcb80]=ppu[0xc800:0xcb80]
    for address,data in saved.items():new[address:address+32]=data
    for tile in range(32,768):struct.pack_into('<H',new,0xc000+tile*2,0x2400|tile-31)
    for address,data in zip((0xc600,0xce00),maps):new[address:address+128]=data
    def obj_entry(entry):
        old=0xc000+(entry&255)*32+(0x2000 if entry&0x100 else 0)
        tile=(near_remap[old]-0xc000)//32
        return (entry&~0x1ff)|tile
    table=bytearray((build/'native_near_table.bin').read_bytes())
    for i in range(0,len(table),2):struct.pack_into('<H',table,i,obj_entry(struct.unpack_from('<H',table,i)[0]))
    (build/'native_near_table.bin').write_bytes(table)
    oam=bytearray((build/'native_near_oam.bin').read_bytes())
    for frame in range(512):
        for obj in range(54):
            i=frame*256+obj*4+2
            struct.pack_into('<H',oam,i,obj_entry(struct.unpack_from('<H',oam,i)[0]))
    (build/'native_near_oam.bin').write_bytes(oam)
    d.update(farChrAddresses=far,nearChrAddresses=near,farChrBase=0xa000)
    path.write_text(json.dumps(d,indent=2)+'\n')
    (build/'fixed_map_layout.json').write_text(json.dumps({
        'pages':[0,0x6000],'map':0xc000,'mapValidStart':0xc040,'mapValidEnd':0xc600,
        'farMapAddresses':[0xc600,0xce00],'playerChr':0xc800,
        'farChrAddresses':far,'nearChrAddresses':near},indent=2)+'\n')
    return new


def cpu(text):
    text=change(text,'  lda #4\n  sta $2107','  lda #$60\n  sta $2107')
    return change(text,'  lda #0\n  sta $210b','  lda #$50\n  sta $210b')


def objects(text):
    return text


def transfer_mask(text):
    start=text.index('sa1_transfer_mask_prepare:\n')
    before,after=text[:start],text[start:]
    after=change(after,'  lda f:$432800,x\n','  lda f:$432900,x\n')
    return before+after


def sparse_map(text):
    # 固定配置なので、空タイルの初期化も番号の詰め直しも不要。
    return '.setcpu "65816"\n.export sa1_sparse_map_prepare: far\n.segment "GSU"\nsa1_sparse_map_prepare:\n  rtl\n'


def direct(text):
    start=text.index('sa1_sparse_direct_finish:\n')
    return text[:start]+'''sa1_sparse_direct_finish:
  rep #$30
  lda $011a
  asl
  sta $b0
  asl
  clc
  adc $b0
  sta $b0
  ldx #0
fixed_descriptor:
  cpx $b0
  bcs fixed_done
  lda f:$430804,x
  sec
  sbc #496
  sta f:$430804,x
  txa
  clc
  adc #6
  tax
  bra fixed_descriptor
fixed_done:
  rtl
sparse_direct_overflow:
  stp
'''


def prefix(text):
    return change(text,'  lda pipe_records+2,x\n  sec\n  sbc #6\n','  lda pipe_records+2,x\n')


def pipeline(text,build,sa1):
    text=change(text,'  lda #$2000\n  sta p3NextPage','  lda #$3000\n  sta p3NextPage')
    text=change(text,'  lda p3Count\n  cmp #2\n','  lda p3Count\n  cmp #1\n')
    setup='''  lda pipe_records+4,x
  clc
  adc #6
  cmp pipe_records+2,x
  bne :+
  sep #$20
  lda #$95
  sta f:$002231
:
'''
    text=change(text,setup,'')
    after='''  sta pipe_records+4,x
  clc
  adc #6
  cmp pipe_records+2,x
  bne :+
  sep #$20
  lda #$95
  sta f:$002231
  rep #$20
:
  jmp pipe_descriptor'''
    text=change(text,after,'  sta pipe_records+4,x\n  jmp pipe_descriptor')
    begin=text.index('pipe_fast_groups_done:\n')
    end=text.index('  .else\npipe_fast_loop:',begin)
    text=text[:begin]+'''pipe_fast_groups_done:
  lda pfPartial
  jne pipe_fast_partial_done
'''+text[end:]
    text=change(text,'''pf_unroll_full:
  lda pipe_records+2,x
  sec
  sbc pipe_records+4,x
  sec
  sbc #6''','''pf_unroll_full:
  lda pipe_records+2,x
  sec
  sbc pipe_records+4,x''')
    begin=text.index('pipe_fast_partial_done:\n')
    end=text.index('  lda pipe_records+34,x\n',begin)
    text=text[:begin]+'''pipe_fast_partial_done:
  ldx pipe_record_offset
  lda pipe_records+4,x
  clc
  adc pfDesc
  sta pipe_records+4,x
'''+text[end:]
    text=change(text,'  sta f:$00210b\n','  ora #$50\n  sta f:$00210b\n')
    text=change(text,'  lda fx4_page+1\n  ora #4\n  sta f:$002107','  lda #$60\n  sta f:$002107')
    ring=(sa1/'vram_prefetch_cpu.inc').read_text(encoding='utf-8')
    begin=ring.index('  lda p3NextPage\n')
    end=ring.index('  sta p3NextPage\n',begin)
    ring=ring[:begin]+'  lda p3NextPage\n  eor #$3000\n'+ring[end:]
    (build/'fixed_map_cpu.inc').write_text(ring,encoding='utf-8')
    return change(text,'.include "vram_prefetch_cpu.inc"','.include "fixed_map_cpu.inc"')
