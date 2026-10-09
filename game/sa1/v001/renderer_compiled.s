.setcpu "65816"
.smart
.macpack longbranch
.export sa1_entry, sa1_clear_start, sa1_clear_done, sa1_draw_start, sa1_draw_done
src=$20
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
dx=$42
rowbase=$44
rowend=$46
rowx=$48
edge=$4a
tmp=$4c
value=$4e
offset=$50
clipfirst=$52
cliplast=$54
cliptable=$56
clipbytes=$5a
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
  stz edge
  bmi is_edge
  clc
  adc width
  cmp #257
  bcc not_edge
is_edge:
  inc edge
not_edge:
  lda left
  and #3
  clc
  adc width
  adc #3
  lsr
  lsr
  sta cliplast
  stz clipfirst
  lda left
  cmp #$8000
  ror
  cmp #$8000
  ror
  sta tmp
  bpl :+
  lda #0
  sec
  sbc tmp
  sta clipfirst
:
  lda tmp
  clc
  adc cliplast
  cmp #65
  bcc :+
  lda #64
  sec
  sbc tmp
  sta cliplast
:
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
  sta dx
  lda width
  asl
  clc
  adc dx
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
  asl
  asl
  sta dx                  ; phase*48
  lda flags
  and #$30
  lsr
  lsr
  sta tmp                 ; flip*4
  lda left
  and #3
  clc
  adc tmp
  sta tmp
  asl
  clc
  adc tmp
  adc dx
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
  clc
  adc #128
  sta rowend
  lda left
  and #$fffc
  cmp #$8000
  ror
  clc
  adc rowbase
  sta rowx
  tax
  lda dy
  asl
  clc
  adc dy
  asl
  tay
  lda [rows],y
  sta src
  sta row_call+1
  iny
  iny
  sep #$20
  lda [rows],y
  sta src+2
  sta row_call+3
  rep #$20
  lda edge
  bne edge_row
invoke_row:
  sep #$20
  lda #$40
  pha
  plb
  rep #$20
  jsr row_call
  sep #$20
  lda #0
  pha
  plb
  rep #$20
  bra row_done
edge_row:
  iny
  lda [rows],y
  sta cliptable
  iny
  iny
  sep #$20
  lda [rows],y
  sta cliptable+2
  rep #$20
  lda clipfirst
  asl
  asl
  tay
  lda [cliptable],y
  sta tmp
  iny
  iny
  lda [cliptable],y
  sta $0501
  lda cliplast
  asl
  asl
  tay
  lda [cliptable],y
  sec
  sbc tmp
  jeq row_done
  sta clipbytes
  lda src
  clc
  adc tmp
  sta $2232
  sep #$20
  lda src+2
  sta $2234
  lda #$80
  sta $2230
  rep #$20
  lda clipbytes
  sta $2238
  lda #$0503
  sta $2235
  ldx clipbytes
  sep #$20
  lda #$a9
  sta $0500
  lda #$6b
  sta $0503,x
  rep #$20
  lda #$0500
  sta row_call+1
  sep #$20
  stz row_call+3
  rep #$20
  ldx rowx
  jmp invoke_row
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
row_call:
  jsl $000000
  rts
.assert * <= $0500, error, "SA-1 kernel overlaps clipped row code buffer"
