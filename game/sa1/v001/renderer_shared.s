.setcpu "65816"
.smart
.macpack longbranch
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
  sta desc
  iny
  iny
  sep #$20
  lda [rows],y
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
  cmp #128
  bcc command_ok
  cmp #$ffff
  beq command_ok
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
  ldx rowbase
  dex
  sep #$20
  lda f:$400000,x
  sta guardleft
  rep #$20
  lda rowbase
  clc
  adc #128
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
  ldx rowbase
  dex
  sep #$20
  lda guardleft
  sta f:$400000,x
  rep #$20
  lda rowbase
  clc
  adc #128
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
sa1_draw_done:
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
  bcc dma_positive
  lda #0
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
  stz cur
dma_positive:
  lda cur
  cmp #128
  bcs dma_return
  clc
  adc dmaCount
  cmp #129
  bcc dma_bounded
  lda #128
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
