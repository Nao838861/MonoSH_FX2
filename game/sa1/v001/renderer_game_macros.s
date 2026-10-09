.setcpu "65816"
.smart
.macpack longbranch
.import sa1_plan_dirty: far, sa1_prepare_transfer: far
.import sa1_try_fast: far
.import sa1_draw_rows: far
.import sa1_compact: far
.import sa1_near_row: far
.import sa1_find_shape: far
.export sa1_entry, sa1_clear_start, sa1_clear_done, sa1_draw_start, sa1_draw_done
.export invoke_row, row_done, clip_left_found
.export sa1_dirty_done, sa1_native_done
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
wordstart=$d4
initialA=$d6
coverEnd=$ce
coverMode=$da
coverOwner=$dc
coverPacket=$de
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
sa1_dirty_done:
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
  stz $c4
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
  bit #$30
  beq :+
unsupported_hflip:
  bra unsupported_hflip
:
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
  lda height
  xba
  ora width
  ldx asset
  jsl sa1_find_shape
  rep #$20
  lda f:$ff0003,x
  sta $c0
  lda f:$ff0005,x
  sta $c2
  lda f:$ff0001,x
  sta table
  lda phase
  asl
  clc
  adc phase
  asl
  sta tmp
  lda left
  and #1
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
  jsl sa1_try_fast
  jcs skip
  stz dy
row:
  lda top
  clc
  adc dy
  cmp #192
  jcs row_done
  .repeat 7
    asl
  .endrepeat
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
  lda dirtyL
  cmp $b4                    ; visible opaque left, prepared by sa1_try_fast
  bcc :+
  beq :+
  bra row_partial
:
  lda dirtyR
  cmp $b0                    ; visible opaque right
  bcc row_partial
  lda top
  clc
  adc dy
  and #7
  eor #7
  inc
  clc
  adc dy
  cmp height
  bcc :+
  lda height
:
  sta $9a
  tax
  lda dy
  jsl sa1_draw_rows
  lda $9a
  dec
  sta dy
  jmp row_done
row_partial:
  lda dy
  asl
  sta tmp
  asl
  asl
  clc
  adc tmp
  adc dy
  sta desc
  inc
  tay
  lda [rows],y
  and #127
  clc
  adc rowx
  sta cur
  lda desc
  clc
  adc #8
  tay
  lda [rows],y
  sta codeptr
  sec
  sbc #2
  sta runptr
  iny
  iny
  sep #$20
  lda [rows],y
  sta codeptr+2
  sta runptr+2
  rep #$20
  ldy #0
  lda [runptr],y
  sta tmp
  and #255
  sta codelen
  lda tmp
  xba
  and #255
  clc
  adc cur
  sta coverEnd
  lda cur
  cmp #$8000
  bcs bounds_left_negative
  cmp dirtyR
  jcs row_done
bounds_left_negative:
  lda coverEnd
  bmi bounds_empty
  cmp dirtyL
  jcc row_done
  jeq row_done
  stz edge
  cmp dirtyR
  bcc bounds_right_inside
  beq bounds_right_inside
  inc edge
bounds_right_inside:
  lda cur
  bmi bounds_left_outside
  cmp dirtyL
  bcs bounds_inside
bounds_left_outside:
  inc edge
bounds_inside:
  lda cur
  clc
  adc rowbase
  sta destbase
  bra bounds_ready
bounds_empty:
  jmp row_done
bounds_ready:
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
  lda codelen
  sec
  sbc #4
  tay
clip_right:
  sep #$20
  lda $0700,y
  cmp #$9d
  bne clip_right_prev
  rep #$20
  lda $0701,y
  clc
  adc destbase
  sec
  sbc rowbase
  bmi clip_right_keep
  cmp dirtyR
  bcc clip_right_keep
clip_right_prev:
  rep #$20
  dey
  dey
  dey
  bpl clip_right
clip_right_keep:
  sep #$20
  lda #$6b
  sta $0703,y
  rep #$20
  stz wordstart
  stz initialA
  ldy #0
clip_left:
  sep #$20
  lda $0700,y
  cmp #$6b
  jeq patched
  cmp #$a9
  bne clip_left_store
  rep #$20
  lda $0701,y
  sta initialA
  bra clip_left_next
clip_left_store:
  .a8
  cmp #$9d
  bne clip_left_next8
  rep #$20
  lda $0701,y
  clc
  adc destbase
  sec
  sbc rowbase
  inc
  cmp #$8000
  bcs clip_left_skipped
  cmp dirtyL
  bcs clip_left_found
clip_left_skipped:
  tya
  clc
  adc #3
  sta wordstart
  bra clip_left_next
clip_left_next8:
  rep #$20
clip_left_next:
  iny
  iny
  iny
  bra clip_left
clip_left_found:
  lda wordstart
  clc
  adc #$0700
  sta $07f1
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
  lda initialA
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
sa1_native_done:
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
.assert * <= $0700, error, "SA-1 shared worker overlaps edge JIT"
.assert * <= $0600, error, "SA-1 worker overlaps guard cache"

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
  .repeat 7
    asl
  .endrepeat
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
  .repeat 7
    asl
  .endrepeat
  sta bgdest
  stz bgrow
bg_near_row:
  jsr bg_bounds
  lda dirtyR
  sec
  sbc dirtyL
  beq bg_near_next
  bmi bg_near_next
  jsl sa1_near_row
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

