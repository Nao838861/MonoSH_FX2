;; Song and Sound Effect ca65 enums for monosh.terrificaudio.
;;
;; Automatically generated using `tad-compiler ca65-enums` or `tad-compiler ca65-export`.
;;
;; This file MUST BE recreated if song list or sound effect export order changes.
;;


LAST_SONG_ID = 1
N_SOUND_EFFECTS = 6

;; Song enum.
;; Input argument for `Tad_LoadSong`
.enum Song
  BLANK = 0 ; blank (silent) song
  theme = 1
.endenum


;; Sound Effects enum.
;; Input argument for `Tad_QueueSoundEffect` and `Tad_QueuePannedSoundEffect`
.enum SFX
  ; high-priority sound effects
  death = 0
  boss_explosion = 1
  ; normal-priority sound effects
  stumble = 2
  explosion = 3
  reflect = 4
  ; low-priority sound effects
  shot = 5
.endenum
