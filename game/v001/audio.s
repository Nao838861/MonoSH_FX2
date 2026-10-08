.setcpu "65816"
.smart
LOROM = 1
.define TAD_CODE_SEGMENT "BOOT"
.include "audio/vendor/tad-audio.s"
.include "audio/enums.inc"

.import _monosh_player_state, _monosh_player_stumble, _monosh_boss_state
.import _monosh_runtime_paused
.export fx_audio_init: far, fx_audio_process: far
.export _fx_audio_events, fx_audio_sent, fx_audio_last_sfx

.segment "AUDIOBSS"
_fx_audio_events: .res 1          ; 1=shot, 2=explosion, 4=reflect, 8=ground object destroyed
audio_old_player: .res 1
audio_old_stumble: .res 1
audio_old_boss: .res 1
audio_old_pause: .res 1
fx_audio_sent: .res 2
fx_audio_last_sfx: .res 1

.segment "BOOT"
; Once, while forced blank and GSU stopped. Preserve caller widths/DBR.
fx_audio_init:
  php
  phb
  rep #$10
  sep #$20
  jsl Tad_Init
  lda #1
  sta Tad_audioMode
  lda #Song::theme
  jsr Tad_LoadSong
  ; 起動時に曲まで読み終える。Tad_FinishLoadingData は転送中にしか働かず、ドライバの準備待ちの間は
  ; 何も送らない。Tad_Process 任せだと1フレーム数百byteずつで、53KBの曲データでは開始が約4秒遅れた。
wait_song_loaded:
  jsl Tad_Process
  jsl Tad_FinishLoadingData
  jsr Tad_IsSongLoaded
  bcc wait_song_loaded
  plb
  plp
  rtl

; Only after GO has cleared. Never call from _fx_frame (GSU owns ROM).
fx_audio_process:
  php
  phb
  rep #$30
  pha
  phx
  phy
  sep #$20
  lda #$7e
  pha
  plb
  rep #$10
  lda _monosh_runtime_paused
  cmp audio_old_pause
  beq check_events
  sta audio_old_pause
  ldx #0
  ldy #0
  lda audio_old_pause
  bne pause_command
  lda #TadCommand::UNPAUSE
  bra queue_pause
pause_command:
  lda #TadCommand::PAUSE
queue_pause:
  jsr Tad_QueueCommandOverride
check_events:
  lda #$ff
  sta fx_audio_last_sfx
  lda _fx_audio_events
  and #1
  beq :+
  lda #SFX::shot               ; lowest priority
  sta fx_audio_last_sfx
:
  lda _fx_audio_events
  and #4
  beq :+
  lda #SFX::reflect
  sta fx_audio_last_sfx
:
  lda _fx_audio_events
  and #8
  beq :+
  lda #SFX::ground_explosion
  sta fx_audio_last_sfx
:
  lda _fx_audio_events
  and #2
  beq :+
  lda #SFX::explosion
  sta fx_audio_last_sfx
:
  stz _fx_audio_events
  lda _monosh_player_stumble
  beq store_stumble
  lda audio_old_stumble
  bne store_stumble
  lda #SFX::stumble
  sta fx_audio_last_sfx
store_stumble:
  lda _monosh_player_stumble
  sta audio_old_stumble
  lda _monosh_player_state
  cmp audio_old_player
  beq check_boss
  sta audio_old_player
  cmp #1
  bne check_boss
  lda #SFX::death              ; highest priority
  sta fx_audio_last_sfx
check_boss:
  lda _monosh_boss_state
  cmp audio_old_boss
  beq send
  sta audio_old_boss
  cmp #2
  bne send
  lda fx_audio_last_sfx
  beq send
  lda #SFX::boss_explosion
  sta fx_audio_last_sfx
send:
  lda fx_audio_last_sfx
  bmi process
  jsr Tad_QueueSoundEffect
  rep #$20
  inc fx_audio_sent
  sep #$20
process:
  jsl Tad_Process
  rep #$30
  ply
  plx
  pla
  plb
  plp
  rtl
