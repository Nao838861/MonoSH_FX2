"""次画面の範囲計算をS-CPUへ移し、SA-1の前画面描画と重ねる。"""
import re
from sa1_vram_four import change


def cpu_helper(dirty,row,shape,near,small=False,shapes=False):
    # row-dirty版の検索表は、高さごとに10 byte（元の表は7 byte）。
    # SA-1用shape生成と同じ変換を、本体CPU用の複製にも適用する。
    shape=shape.replace('  adc #7','  adc #10')
    shape=shape.replace('  asl\n  asl\n  asl\n  sec\n  sbc shapeMid',
                        '  asl\n  sta $f0\n  asl\n  asl\n  clc\n  adc $f0')
    aliases=dirty[dirty.index('dirty_count=$a0'):dirty.index('sa1_plan_dirty:\n')]
    mark=dirty[dirty.index('dirty_mark:\n'):dirty.index('sa1_prepare_transfer:\n')]
    if small:
        mark=change(mark,'  jsl sa1_dirty_rows\n  rts\n','  rts\n')
    shared=aliases+mark+'sa1_dirty_row_rect:\n  jsr dirty_rect\n  rtl\n'+row+shape
    near=near[:near.index('sa1_near_patch:\n')]
    near=near.replace('$010a','$d8').replace('$010c','$da')
    shared+=near
    shared=re.sub(r'^\.(?:import|export)[^\n]*\n','',shared,flags=re.M)
    shared=re.sub(r'^\.(?:setcpu|smart|macpack)[^\n]*\n','',shared,flags=re.M)
    shared=shared.replace('.segment "BOOT"','.segment "CODE"')
    names=set(re.findall(r'^([a-zA-Z_]\w*)(?=[:=])',shared,re.M))
    shared=re.sub(r'\b[a-zA-Z_]\w*\b',lambda m:'cd_'+m[0] if m[0] in names else m[0],shared)
    shared=re.sub(r'\bjsl (cd_\w+)',r'jsl $7f0000+\1',shared)
    for a,b in (('$430000','$7e0000+_fx_packet'),('$430002','$7e0002+_fx_packet'),
                ('$430004','$7e0004+_fx_packet'),('$430005','$7e0005+_fx_packet'),
                ('$430006','$7e0006+_fx_packet'),('$430007','$7e0007+_fx_packet'),
                ('$433000','$7ef0c0'),('$432800','$7ef000'),('$432802','$7ef002'),
                ('$436800','$7ef000'),('$436802','$7ef002'),
                ('$0120','f:$7ef060'),('$0122','f:$7ef062')):
        shared=shared.replace(a,b)
    shared=shared.replace('lda sa1_tile_masks','lda f:sa1_tile_masks')
    shared=re.sub(r'\b(bcc|bcs|beq|bne|bmi|bpl) (cd_\w+)',lambda m:'j'+m[1][1:]+' '+m[2],shared)
    preamble='''.setcpu "65816"
.smart
.macpack longbranch
.import _fx_packet,_fx_packet_count,_fx_far_u_acc,_monosh_ground_offset
.import sa1_tile_masks
.export cpu_dirty_prepare: far,cpu_dirty_upload: far,cpu_dirty_done: far
.segment "BSS"
cd_ready: .res 2
.segment "CODE"
cpu_dirty_prepare:
  php
  rep #$30
  pha
  phx
  phy
  phd
  phb
  lda #$0400
  tcd
  sep #$20
  lda #$7e
  pha
  plb
  rep #$30
  lda f:$7e0000+_fx_far_u_acc
  .repeat 7
    lsr
  .endrepeat
  and #511
  sta $d8
  lda f:$7e0000+_monosh_ground_offset
  and #255
  sta $da
  ldx #0
cd_init:
  lda #0
  sta f:$7ef000,x
  sta f:$7ef002,x
  sta f:$7ef062,x
  lda #128
  sta f:$7ef060,x
  inx
  inx
  inx
  inx
  cpx #96
  bcc cd_init
  lda f:$7e0000+_fx_packet_count
  sta cd_dirty_count
  stz cd_dirty_i
  ldx #0
cd_object:
  lda cd_dirty_i
  cmp cd_dirty_count
  bcs cd_background
  phx
  stz cd_dirty_ptr
  jsr cd_dirty_mark
  lda cd_dirty_i
  asl
  tax
  lda $ba
  sta f:$7ef0c0,x
  plx
  txa
  clc
  adc #10
  tax
  inc cd_dirty_i
  bra cd_object
cd_background:
  jsl $7f0000+cd_sa1_near_patch_bounds
  lda #1
  sta cd_ready
cpu_dirty_done:
  plb
  pld
  ply
  plx
  pla
  plp
  rtl
cpu_dirty_upload:
  rep #$30
  lda cd_ready
  bne cd_upload
  jsl $7f0000+cpu_dirty_prepare
cd_upload:
  stz cd_ready
  phb
  ldx #$f000
  ldy #$2c00
  lda #319
  mvn #$7e,#$43
  plb
  rtl
'''
    first=shared.index('cd_dirty_mark:\n')
    if shapes:
        preamble=change(preamble,'  stz cd_dirty_ptr\n  jsr cd_dirty_mark\n',
            '''  lda f:$7e0004+_fx_packet,x
  pha
  lda f:$7e0006+_fx_packet,x
  and #255
  tax
  pla
  jsl $7f0000+cd_sa1_find_shape
  stx $ba
''')
        preamble=change(preamble,'  jsl $7f0000+cd_sa1_near_patch_bounds\n','')
    return preamble.replace('.segment "CODE"\n','.segment "CODE"\n'+shared[:first],1)+shared[first:]


def dirty(text,small=False,shapes=False):
    a=text.index('sa1_plan_dirty:\n');b=text.index('dirty_first:\n',a)
    if shapes:
        text=change(text,'dirty_shape_new:\n  lda dirty_width\n  jsl sa1_find_shape\n  stx $ba\n',
            'dirty_shape_new:\n  lda dirty_i\n  asl\n  tax\n  lda f:$433000,x\n  tax\n  stx $ba\n')
        return change(text,'sa1_plan_dirty:\n','''sa1_plan_dirty:
  rep #$30
  phb
  ldx #$2cc0
  ldy #$3000
  lda #127
  mvn #$43,#$43
  plb
''')
    extra=''
    if small:
        extra='''  lda $0106
  sta dirty_count
  stz dirty_i
  stz dirty_ptr
  ldx #0
cpu_dirty_large_next:
  lda dirty_i
  cmp dirty_count
  bcs cpu_dirty_large_done
  lda f:$430007,x
  and #$30
  bne cpu_dirty_large_skip
  lda f:$430004,x
  and #255
  cmp #32
  bcc cpu_dirty_large_skip
  lda f:$430005,x
  and #255
  cmp #24
  bcc cpu_dirty_large_skip
  phx
  jsr dirty_mark
  plx
cpu_dirty_large_skip:
  txa
  clc
  adc #10
  tax
  inc dirty_i
  bra cpu_dirty_large_next
cpu_dirty_large_done:
'''
        text=change(text,'dirty_shape_new:\n  lda dirty_width\n  jsl sa1_find_shape\n  stx $ba\n',
                    'dirty_shape_new:\n  lda dirty_i\n  asl\n  tax\n  lda f:$433000,x\n  tax\n')
    return text[:a]+'''sa1_plan_dirty:
  rep #$30
  phb
  ldx #$2c00
  ldy #$2800
  lda #95
  mvn #$43,#$43
  ldx #$2c60
  ldy #$0120
  lda #95
  mvn #$43,#$00
  ldx #$2cc0
  ldy #$3000
  lda #127
  mvn #$43,#$43
  plb
'''+extra+'  jmp dirty_first\n'+text[b:]


def pipeline(text):
    text='.import cpu_dirty_prepare: far,cpu_dirty_upload: far\n'+text
    text=change(text,'pipe_main:\n  cli\n','pipe_main:\n  cli\n  jsl $7f0000+cpu_dirty_upload\n')
    return change(text,'logic_finished:\n  rep #$30\n','logic_finished:\n  rep #$30\n  jsl $7f0000+cpu_dirty_prepare\n')
