.setcpu "65816"
.smart
.macpack longbranch
.export sa1_entry, sa1_clear_start, sa1_clear_done, sa1_draw_start, sa1_draw_done
; I-RAM DP: 両CPUの共有mailboxは$0100..0107、packetはBW-RAM $43:0000。
src=$20
dest=$24
packet=$28
index=$2c
count=$2e
u=$30
v=$32
du=$34
dv=$36
width=$38
height=$3a
left=$3c
top=$3e
dx=$40
dy=$42
base=$44
flags=$46
u0=$48
phase=$4a
asset=$4c
rowbytes=$4e
table=$50
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
  stz $223f
wait_job:
  rep #$30
  lda $0100
  beq wait_job
sa1_clear_start:
.ifdef SA1_DMA_CLEAR
  sep #$20
  lda #$84
  sta $2230
.ifdef SA1_PRESCALED
  stz $2232
  lda #$80
  sta $2233
  lda #$02
.else
  stz $2232
  stz $2233
  lda #$c3
.endif
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
.else
  lda #0
  ldx #$5ffe
clear:
  sta f:$400000,x
  dex
  dex
  bpl clear
.endif
sa1_clear_done:
  stz index
  lda $0106
  sta count
  lda #0
  sta packet
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
  sta base
  lda left
  sec
  sbc base
  sta left
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
.ifdef SA1_PRESCALED
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
  lda width
  inc
  lsr
  sta rowbytes
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
  ; 未生成寸法を無言で描き落とさない。テストではtimeout/PCとして検出する。
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
  sta dx
  lda flags
  lsr
  lsr
  lsr
  lsr
  and #3
  sta dy
  asl
  clc
  adc dy
  clc
  adc dx
  adc table
  tax
  lda f:$ff0000,x
  sta src
  sep #$20
  lda f:$ff0002,x
  sta src+2
  lda #$60
  sta dest+2
  rep #$20
  stz base
.else
  lda asset
  asl
  clc
  adc asset
  adc phase
  asl
  asl
  tax
  lda f:source_table,x
  sta src
  sta base
  sep #$20
  lda f:source_table+2,x
  sta src+2
  lda #$60
  sta dest+2
  rep #$20
  lda asset
  xba
  asl
  sta dx
  lda width
  asl
  clc
  adc dx
  tax
  lda f:$df0000,x
  sta du
  lda height
  asl
  clc
  adc dx
  tax
  lda f:$df5800,x
  sta dv
  stz u0
  stz v
  lda flags
  bit #$10
  beq no_hflip
  lda asset
  asl
  tax
  lda f:dimensions,x
  and #255
  xba
  dec
  sta u0
  lda #0
  sec
  sbc du
  sta du
no_hflip:
  lda flags
  bit #$20
  beq no_vflip
  lda asset
  asl
  tax
  lda f:dimensions+1,x
  and #255
  xba
  dec
  sta v
  lda #0
  sec
  sbc dv
  sta dv
no_vflip:
.endif
  stz dy
row:
.ifdef SA1_PRESCALED
  lda base
  sta u0
.else
  lda v
  and #$ff00
  clc
  adc base
  sta src
.endif
  lda top
  clc
  adc dy
  cmp #192
  bcs row_done
  xba
  sta dest
  lda u0
  sta u
  stz dx
pixel:
.ifdef SA1_PRESCALED
  lda dx
  lsr
  clc
  adc base
  tay
  sep #$20
  lda [src],y
  pha
  lda dx
  and #1
  beq even_pixel
  pla
  lsr
  lsr
  lsr
  lsr
  bra got_pixel
even_pixel:
  pla
got_pixel:
  and #15
.else
  lda u
  xba
  and #255
  tay
  sep #$20
  lda [src],y
.endif
  beq transparent
  pha
  rep #$20
  lda left
  clc
  adc dx
  cmp #256
  bcs outside
  tay
  sep #$20
  pla
  sta [dest],y
  bra transparent
outside:
  sep #$20
  pla
transparent:
  rep #$20
.ifndef SA1_PRESCALED
  lda u
  clc
  adc du
  sta u
.endif
  inc dx
  lda dx
  cmp width
  bcc pixel
row_done:
.ifdef SA1_PRESCALED
  lda base
  clc
  adc rowbytes
  sta base
.else
  lda v
  clc
  adc dv
  sta v
.endif
  inc dy
  lda dy
  cmp height
  bcc row
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
.segment "BOOT"
source_table: .incbin "lookup.bin"
dimensions: .incbin "dimensions.bin"
