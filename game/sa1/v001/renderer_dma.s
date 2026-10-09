.setcpu "65816"
.smart
.macpack longbranch
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
  sep #$20
  lda #$84
  sta $2230
  stz $2232
  lda #$80
  sta $2233
  lda #2
  sta $2234
  stz $2235
  stz $2236
  rep #$20
  lda #$6000
  sta $2238
  sep #$20
  lda #$40
  sta $2237
  rep #$30
sa1_clear_done:
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
  cmp #$8000
  bcc positive
  lda #0
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
  stz spanOffset
positive:
  lda spanOffset
  cmp #128
  jcs span_done
  clc
  adc spanLength
  cmp #129
  bcc bounded
  lda #128
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
  cmp #127
  bcc whole_word
  beq last_byte
  cmp #$ffff
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
  adc #6
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
  lda #1
  sta $0104
wait_release:
  lda $0100
  bne wait_release
  stz $0104
  jmp wait_job
