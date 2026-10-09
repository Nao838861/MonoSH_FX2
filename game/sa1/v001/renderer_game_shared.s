.setcpu "65816"
.smart
.macpack longbranch
.import sa1_plan_dirty: far, sa1_prepare_transfer: far
.export sa1_dma_span
.export sa1_entry, sa1_clear_start, sa1_clear_done, sa1_draw_start, sa1_draw_done
rd=$20
rows=$24
packet=$28
index=$2c
count=$2e
table=$30
phase=$32
width=$34
height=$36
left=$38
top=$3a
flags=$3c
asset=$3e
dy=$40
tmp=$42
rowbase=$44
rowx=$48
runptr=$60
spanIndex=$64
spanCount=$66
spanLength=$68
spanOffset=$6a
mask=$6c
value=$6e
cur=$70
codeptr=$84
desc=$88
codelen=$8c
destbase=$8e
edge=$90
scany=$92
cmdlen=$94
guardleft=$96
guardright=$97
fullcount=$98
dmaSrc=$9a
dmaCount=$9c
dmaDest=$9e
vpos=$c0
vstep=$c2
source_map=$c4
source_rows=$c8
dirtyL=$d0
dirtyR=$d2
bgptr=$e0
bgrow=$e4
bgdest=$e6
bgscroll=$e8
bgfirst=$ea
bgbase=$ec
bgwidth=$ee
bgtemp=$f0
.segment "SA1"
sa1_entry:
  sei
  clc
  xce
  rep #$30
  lda #$01ff
  tcs
  lda #0
  tcd
  sep #$20
  pha
  plb
  lda #$80
  sta $2227
  lda #$22
  sta $07f0
  lda #$60
  sta $07f4
wait_job:
  rep #$30
  lda $0100
  beq wait_job
sa1_clear_start:
  jsl sa1_plan_dirty
  sep #$20
  lda #$84
  sta $2230
  rep #$30
  stz bgrow
clear_tile_row:
  lda bgrow
  asl
  asl
  tax
  lda $0122,x
  sec
  sbc $0120,x
  beq clear_tile_next
  bmi clear_tile_next
  sta bgfirst
  lda bgrow
  xba
  asl
  asl
  clc
  adc $0120,x
  sta bgdest
  lda #8
  sta bgscroll
clear_scanline:
  lda bgfirst
  sta $2238
  lda #$8000
  sta $2232
  lda bgdest
  sta $2235
  sep #$20
  lda #2
  sta $2234
  lda #$40
  sta $2237
  rep #$20
  lda bgdest
  clc
  adc #128
  sta bgdest
  dec bgscroll
  bne clear_scanline
clear_tile_next:
  inc bgrow
  lda bgrow
  cmp #24
  bne clear_tile_row
sa1_clear_done:
  jsl background
  stz index
  lda $0106
  sta count
  stz packet
  sep #$20
  lda #$43
  sta packet+2
sa1_draw_start:
  rep #$30
next:
  lda index
  cmp count
  jcs finished
  ldy #4
  lda [packet],y
  and #255
  sta width
  jeq skip
  iny
  lda [packet],y
  and #255
  sta height
  jeq skip
  ldy #0
  lda [packet],y
  sta left
  lda width
  lsr
  sta tmp
  lda left
  sec
  sbc tmp
  sta left
  cmp #$8000
  ror
  sta rowx
  stz edge
  lda left
  bmi edge_draw
  clc
  adc width
  cmp #257
  bcc regular_draw
edge_draw:
  inc edge
regular_draw:
  ldy #2
  lda [packet],y
  sec
  sbc height
  sec
  sbc #20
  sta top
  ldy #6
  lda [packet],y
  and #255
  sta asset
  iny
  lda [packet],y
  and #255
  sta flags
  and #3
  cmp #3
  bcc :+
  lda #0
:
  sta phase
  lda asset
  cmp #6
  beq phase_valid
  cmp #7
  beq phase_valid
  cmp #8
  beq phase_valid
  cmp #31
  beq phase_valid
  cmp #37
  beq phase_valid
  stz phase
phase_valid:
  lda asset
  xba
  asl
  sta tmp
  lda width
  asl
  clc
  adc tmp
  tax
  lda f:$ff0000,x
  tax
  sep #$20
  lda f:$ff0000,x
  sta table
  inx
find_height:
  lda f:$ff0000,x
  cmp height
  beq found_height
  inx
  inx
  inx
  inx
  inx
  dec table
  bne find_height
missing_pattern:
  bra missing_pattern
found_height:
  rep #$20
  lda f:$ff0001,x
  sta table
  lda f:$ff0003,x
  sta vstep
  lda phase
  asl
  clc
  adc phase
  asl
  asl
  sta tmp
  lda flags
  and #$10
  lsr
  lsr
  lsr
  sta cur
  lda left
  and #1
  clc
  adc cur
  sta cur
  asl
  clc
  adc cur
  adc tmp
  adc table
  tax
  lda f:$ff0000,x
  sta rows
  sep #$20
  lda f:$ff0002,x
  sta rows+2
  rep #$20
  ldy #0
  lda [rows],y
  sta source_map
  iny
  iny
  sep #$20
  lda [rows],y
  sta source_map+2
  iny
  rep #$20
  lda [rows],y
  sta source_rows
  iny
  iny
  sep #$20
  lda [rows],y
  sta source_rows+2
  rep #$20
  stz vpos
  lda flags
  bit #$20
  beq :+
  ldx asset
  sep #$20
  lda f:native_heights,x
  rep #$20
  and #255
  xba
  dec
  sta vpos
:
  stz dy
row:
  lda top
  clc
  adc dy
  cmp #192
  jcs row_done
  xba
  lsr
  sta rowbase
  .repeat 8
    lsr
  .endrepeat
  and #$fffc
  tax
  lda $0120,x
  sta dirtyL
  lda $0122,x
  sta dirtyR
  cmp dirtyL
  jcc row_done
  jeq row_done
  stz edge
  lda rowx
  bmi row_edge
  cmp dirtyL
  bcc row_edge
  lda left
  clc
  adc width
  inc
  lsr
  cmp dirtyR
  bcc row_regular
  beq row_regular
row_edge:
  inc edge
row_regular:
  lda vpos
  xba
  and #255
  tay
  lda [source_map],y
  and #255
  sta tmp
  asl
  clc
  adc tmp
  tay
  lda [source_rows],y
  sta desc
  iny
  iny
  sep #$20
  lda [source_rows],y
  sta desc+2
  rep #$20
  ldy #0
  lda [desc],y
  sta codeptr
  iny
  iny
  sep #$20
  lda [desc],y
  sta codeptr+2
  iny
  rep #$20
  lda [desc],y
  sta runptr
  iny
  iny
  sep #$20
  lda [desc],y
  sta runptr+2
  iny
  lda [desc],y
  rep #$20
  and #255
  clc
  adc rowx
  clc
  adc rowbase
  sta destbase
  ldy #0
  lda [codeptr],y
  sta codelen
  inc codeptr
  inc codeptr
  lda codeptr
  sta $07f1
  sep #$20
  lda codeptr+2
  sta $07f3
  rep #$20
  lda edge
  jeq invoke_row
  sep #$20
  lda #$80
  sta $2230
  rep #$20
  lda codeptr
  sta $2232
  sep #$20
  lda codeptr+2
  sta $2234
  rep #$20
  lda codelen
  sta $2238
  lda #$0700
  sta $2235
  sta $07f1
  sep #$20
  stz $07f3
  lda #$84
  sta $2230
  rep #$20
  stz scany
patch:
  ldy scany
  sep #$20
  lda $0700,y
  cmp #$6b
  jeq patched
  cmp #$a9
  beq dma_command
  cmp #$b7
  beq opaque_command
  rep #$20
  lda #17
  sta cmdlen
  lda $0701,y
  bra patch_word
opaque_command:
  rep #$20
  lda #7
  sta cmdlen
  lda $0703,y
patch_word:
  clc
  adc destbase
  sec
  sbc rowbase
  cmp #$8000
  bcs patch_negative
  cmp dirtyR
  bcs patch_remove
  inc
  cmp dirtyL
  bcs command_ok
  bra patch_remove
patch_negative:
  inc
  cmp dirtyL
  beq command_ok
patch_remove:
  lda #$c8c8
  sta $0700,y
  lda cmdlen
  sec
  sbc #4
  xba
  ora #$80
  sta $0702,y
  bra command_ok
dma_command:
  rep #$20
  lda #12
  sta cmdlen
command_ok:
  lda scany
  clc
  adc cmdlen
  sta scany
  jmp patch
patched:
  rep #$30
  lda rowbase
  clc
  adc dirtyL
  dec
  tax
  sep #$20
  lda f:$400000,x
  sta guardleft
  rep #$20
  lda rowbase
  clc
  adc dirtyR
  tax
  sep #$20
  lda f:$400000,x
  sta guardright
  rep #$20
invoke_row:
  ldx destbase
  ldy #0
  sep #$20
  lda #$40
  pha
  plb
  rep #$20
  jsr $07f0
  sep #$20
  lda #0
  pha
  plb
  rep #$20
  lda edge
  beq row_done
  lda rowbase
  clc
  adc dirtyL
  dec
  tax
  sep #$20
  lda guardleft
  sta f:$400000,x
  rep #$20
  lda rowbase
  clc
  adc dirtyR
  tax
  sep #$20
  lda guardright
  sta f:$400000,x
  rep #$20
row_done:
  lda flags
  bit #$20
  bne v_reverse
  lda vpos
  clc
  adc vstep
  sta vpos
  bra v_updated
v_reverse:
  lda vpos
  sec
  sbc vstep
  sta vpos
v_updated:
  inc dy
  lda dy
  cmp height
  jcc row
skip:
  lda packet
  clc
  adc #10
  sta packet
  inc index
  jmp next
finished:
sa1_draw_done:
  jsl sa1_prepare_transfer
  sep #$20
  lda #$b1
  sta $2230
  rep #$20
  lda #1
  sta $0104
wait_release:
  lda $0100
  bne wait_release
  stz $0104
  jmp wait_job

; shared native kernelから呼ぶ。DBR=$40、DP=$0000、X=行原点、Y=色データ。
; $80=原点からのbyte offset、A=byte数。Xを保存しYを元のbyte数だけ進める。
sa1_dma_span:
  sta fullcount
  sta dmaCount
  phx
  phy
  txa
  clc
  adc $80
  sta dmaDest
  tya
  clc
  adc runptr
  sta dmaSrc
  lda edge
  beq dma_bounded
  lda dmaDest
  sec
  sbc rowbase
  sta cur
  cmp #$8000
  bcs dma_clip_left
  cmp dirtyL
  bcs dma_positive
dma_clip_left:
  lda dirtyL
  sec
  sbc cur
  cmp dmaCount
  jcs dma_return
  sta tmp
  clc
  adc dmaSrc
  sta dmaSrc
  lda dmaDest
  clc
  adc tmp
  sta dmaDest
  lda dmaCount
  sec
  sbc tmp
  sta dmaCount
  lda dirtyL
  sta cur
dma_positive:
  lda cur
  cmp dirtyR
  bcs dma_return
  clc
  adc dmaCount
  cmp dirtyR
  bcc dma_bounded
  lda dirtyR
  sec
  sbc cur
  sta dmaCount
dma_bounded:
  lda dmaCount
  sta f:$002238
  lda dmaSrc
  sta f:$002232
  lda dmaDest
  sta f:$002235
  sep #$20
  lda runptr+2
  sta f:$002234
  lda #$40
  sta f:$002237
  rep #$20
dma_return:
  ply
  plx
  tya
  clc
  adc fullcount
  tay
  rtl

.assert * <= $0700, error, "SA-1 shared worker overlaps edge JIT"

.include "assets4/background4.inc"
.segment "BOOT"
background:
  rep #$30
  lda $0108
  lsr
  sta bgscroll
  lda $0108
  and #1
  xba
  asl
  asl
  asl
  asl
  sta bgbase
  lda $010c
  clc
  adc #FX_BG_0_TOP
  xba
  lsr
  sta bgdest
  lda #0
  sta bgrow
bg_far_row:
  jsr bg_bounds
  lda dirtyR
  sec
  sbc dirtyL
  beq bg_far_next
  bmi bg_far_next
  sta bgwidth
  lda bgscroll
  clc
  adc dirtyL
  and #255
  sta bgtemp
  lda #256
  sec
  sbc bgtemp
  cmp bgwidth
  bcc :+
  lda bgwidth
:
  sta bgfirst
  sta $2238
  lda bgrow
  xba
  clc
  adc bgbase
  adc bgtemp
  sta $2232
  lda bgdest
  clc
  adc dirtyL
  sta $2235
  sep #$20
  lda #$de
  sta $2234
  lda #$40
  sta $2237
  rep #$20
  lda bgwidth
  sec
  sbc bgfirst
  beq bg_far_next
  sta $2238
  lda bgrow
  xba
  clc
  adc bgbase
  sta $2232
  lda bgdest
  clc
  adc bgfirst
  adc dirtyL
  sta $2235
  sep #$20
  lda #$40
  sta $2237
  rep #$20
bg_far_next:
  lda bgdest
  clc
  adc #128
  sta bgdest
  inc bgrow
  lda bgrow
  cmp #FX_BG_0_HEIGHT
  jne bg_far_row
  lda $010a
  and #3
  xba
  .repeat 5
    asl
  .endrepeat
  clc
  adc #$2000
  sta bgptr
  sep #$20
  lda #$de
  sta bgptr+2
  rep #$20
  lda $010a
  and #$1fc
  sta bgscroll
  lda $010c
  clc
  adc #FX_BG_1_TOP
  xba
  lsr
  sta bgdest
  stz bgrow
bg_near_row:
  jsr bg_bounds
  lda dirtyR
  sec
  sbc dirtyL
  beq bg_near_next
  bmi bg_near_next
  lsr
  sta bgfirst
  lda bgdest
  clc
  adc dirtyL
  tax
  lda dirtyL
  asl
  clc
  adc bgscroll
  and #511
  tay
bg_near_word:
  lda [bgptr],y
  sta mask
  iny
  iny
  lda [bgptr],y
  sta value
  lda f:$400000,x
  and mask
  ora value
  sta f:$400000,x
  inx
  inx
  iny
  iny
  tya
  and #511
  tay
  dec bgfirst
  bne bg_near_word
bg_near_next:
  lda bgdest
  clc
  adc #128
  sta bgdest
  lda bgptr
  clc
  adc #512
  sta bgptr
  inc bgrow
  lda bgrow
  cmp #FX_BG_1_HEIGHT
  bne bg_near_row
  rtl
bg_bounds:
  lda bgdest
  .repeat 8
    lsr
  .endrepeat
  and #$fffc
  tax
  lda $0120,x
  sta dirtyL
  lda $0122,x
  sta dirtyR
  rts

native_heights:
.byte 40,50,27,42,91,95,64,64,60,48,32,28,58,33,40,48,48,48,48,48,48,48,48,48,48,48,48,48,48,48,48,55,30,33,32,43,63,44,8,94,84,88,19,1
