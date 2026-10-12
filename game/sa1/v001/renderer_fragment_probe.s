; 遮蔽表の探索を除いた、prefixコピー+suffix直接呼出の費用測定。
.setcpu "65816"
.smart
.macpack longbranch
.export sa1_entry, sa1_clear_start, sa1_clear_done, sa1_draw_start, sa1_draw_done
.export fragment_prefix_copy, fragment_suffix_invoke
commands=$20
remaining=$24
mode=$26
dest=$28
code=$2a
stop=$2e
resume=$30
initial=$32
suffix=$34
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
  lda #$5c
  sta $07f0
wait_job:
  rep #$30
  lda $0100
  beq wait_job
sa1_clear_start:
  sep #$20
  lda #$84
  sta $2230
  rep #$20
  lda #$8000
  sta $2232
  sep #$20
  lda #2
  sta $2234
  rep #$20
  lda #$6000
  sta $2238
  stz $2235
  sep #$20
  lda #$40
  sta $2237
  rep #$20
sa1_clear_done:
  lda $0108
  asl
  sta dest
  asl
  clc
  adc dest
  tax
  lda f:$c20000,x
  sta remaining
  lda f:$c20002,x
  sta commands
  lda f:$c20004,x
  and #255
  sta commands+2
  lda f:$c20005,x
  and #255
  sta mode
sa1_draw_start:
  nop                         ; 開始callbackを行loopへ重ねない。
next_row:
  rep #$30
  ldy #0
  lda [commands],y
  sta dest
  ldy #2
  lda [commands],y
  sta code
  sta f:$0007f1
  ldy #4
  lda [commands],y
  and #255
  sta code+2
  sep #$20
  sta f:$0007f3
  rep #$20
  lda mode
  jeq full_row
  ldy #5
  lda [commands],y
  and #255
  sta stop
  ldy #6
  lda [commands],y
  and #255
  sta resume
  cmp stop
  jeq full_row
  cmp #255
  bne :+
  lda stop
  jeq row_done
:
  ldy #7
  lda [commands],y
  sta initial
  lda resume
  clc
  adc code
  sta suffix
  lda stop
  beq call_suffix
fragment_prefix_copy:
  lda mode
  cmp #2
  beq copy_cpu
  lda stop
  sta $2238
  lda code
  sta $2232
  sep #$20
  lda code+2
  sta $2234
  lda #$80
  sta $2230
  rep #$20
  lda #$0500
  sta $2235
  bra prefix_ready
copy_cpu:
  sep #$20
  lda code+2
  sta copy_block+2
  rep #$30
  ldx code
  ldy #$0500
  lda stop
  dec
copy_block:
  mvn #$c4,#$00
prefix_ready:
  ldx stop
  sep #$20
  lda #$6b
  sta f:$000500,x
  lda #$40
  pha
  plb
  rep #$20
  ldx dest
  jsl $000500
call_suffix:
  lda resume
  cmp #255
  jeq row_done
  lda suffix
  sta f:$0007f1
  sep #$20
  lda #$40
  pha
  plb
  rep #$20
  ldx dest
  lda initial
fragment_suffix_invoke:
  jsl $0007f0
  bra row_done
full_row:
  sep #$20
  lda #$40
  pha
  plb
  rep #$20
  ldx dest
  jsl $0007f0
row_done:
  sep #$20
  lda #0
  pha
  plb
  rep #$20
  lda commands
  clc
  adc #9
  sta commands
  dec remaining
  jne next_row
sa1_draw_done:
  lda #1
  sta $0104
wait_release:
  lda $0100
  bne wait_release
  stz $0104
  jmp wait_job
