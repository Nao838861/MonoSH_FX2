.setcpu "65816"
.smart
.macpack longbranch
.import sa1_plan_dirty: far, sa1_prepare_transfer: far
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
dirtyL=$84
dirtyR=$86
bgptr=$90
bgrow=$94
bgdest=$96
bgscroll=$98
bgfirst=$9a
bgbase=$9c
bgwidth=$9e
bgtemp=$bc
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
  dec table
  bne find_height
missing_pattern:
  bra missing_pattern
found_height:
  rep #$20
  lda f:$ff0001,x
  sta table
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
  lda dy
  sta tmp
  lda flags
  bit #$20
  beq :+
  lda tmp
  clc
  adc height
  sta tmp
:
  lda tmp
  asl
  clc
  adc tmp
  tay
  lda [rows],y
  sta rd
  iny
  iny
  sep #$20
  lda [rows],y
  sta rd+2
  rep #$20
  ldy #0
  lda [rd],y
  sta spanCount
  lda #2
  sta spanIndex
span:
  lda spanCount
  jeq row_done
  ldy spanIndex
  lda [rd],y
  sta tmp
  and #255
  clc
  adc rowx
  sta spanOffset
  lda tmp
  xba
  and #255
  sta spanLength
  iny
  iny
  lda [rd],y
  sta runptr
  iny
  iny
  sep #$20
  lda [rd],y
  sta runptr+2
  rep #$20
  lda spanLength
  bit #$80
  jne mixed
  lda spanOffset
  cmp dirtyL
  bmi clip_left
  bcs positive
clip_left:
  lda dirtyL
  sec
  sbc spanOffset
  cmp spanLength
  jcs span_done
  sta tmp
  clc
  adc runptr
  sta runptr
  lda spanLength
  sec
  sbc tmp
  sta spanLength
  lda dirtyL
  sta spanOffset
positive:
  lda spanOffset
  cmp dirtyR
  jcs span_done
  clc
  adc spanLength
  cmp dirtyR
  bcc bounded
  lda dirtyR
  sec
  sbc spanOffset
  sta spanLength
bounded:
  lda rowbase
  clc
  adc spanOffset
  tax
  lda spanLength
  cmp #8
  bcc small
  sta $2238
  lda runptr
  sta $2232
  txa
  sta $2235
  sep #$20
  lda runptr+2
  sta $2234
  lda #$40
  sta $2237
  rep #$20
  jmp span_done
small:
  ldy #0
small_word:
  lda spanLength
  cmp #2
  bcc small_byte
  lda [runptr],y
  sta f:$400000,x
  iny
  iny
  inx
  inx
  dec spanLength
  dec spanLength
  bra small_word
small_byte:
  lda spanLength
  jeq span_done
  sep #$20
  lda [runptr],y
  sta f:$400000,x
  rep #$20
  jmp span_done
mixed:
  and #$7f
  sta spanLength
  lda spanOffset
  sta cur
  ldy #0
mixed_word:
  lda [runptr],y
  sta mask
  iny
  iny
  lda [runptr],y
  sta value
  iny
  iny
  lda rowbase
  clc
  adc cur
  tax
  lda cur
  cmp #$8000
  bcs mixed_negative
  inc
  cmp dirtyR
  beq last_byte
  bcs mixed_next
  dec
  cmp dirtyL
  bcs whole_word
  inc
  cmp dirtyL
  beq first_byte
  bra mixed_next
mixed_negative:
  inc
  cmp dirtyL
  beq first_byte
  bra mixed_next
whole_word:
  lda f:$400000,x
  and mask
  ora value
  sta f:$400000,x
  bra mixed_next
last_byte:
  sep #$20
  lda f:$400000,x
  and mask
  ora value
  sta f:$400000,x
  rep #$20
  bra mixed_next
first_byte:
  inx
  sep #$20
  lda f:$400000,x
  and mask+1
  ora value+1
  sta f:$400000,x
  rep #$20
mixed_next:
  inc cur
  inc cur
  dec spanLength
  bne mixed_word
span_done:
  lda spanIndex
  clc
  adc #5
  sta spanIndex
  dec spanCount
  jmp span
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

; 既存の遠景二層。遠景は不透明区間のDMA、手前は4画素単位の透過合成。
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
