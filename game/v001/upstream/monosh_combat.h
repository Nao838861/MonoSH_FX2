#ifndef MSXSH_MONOSH_COMBAT_H
#define MSXSH_MONOSH_COMBAT_H

#define MONOSH_PLAYER_BULLET_MAX 3u
#define MONOSH_REFLECTED_BULLET_MAX 3u

typedef struct MonoshPlayerBullet {
    unsigned char active;
    unsigned char screen_x;
    unsigned char screen_y;
    unsigned char wz;
    unsigned char timer;
} MonoshPlayerBullet;

typedef struct MonoshReflectedBullet {
    unsigned char active;
    unsigned char screen_x;
    unsigned char screen_y;
    signed char velocity_x;
    signed char velocity_y;
} MonoshReflectedBullet;

extern MonoshPlayerBullet monosh_player_bullets[MONOSH_PLAYER_BULLET_MAX];
extern unsigned char monosh_player_bullet_count;
extern MonoshReflectedBullet
    monosh_reflected_bullets[MONOSH_REFLECTED_BULLET_MAX];
extern unsigned char monosh_reflected_bullet_count;
/* ROM uses byte zero as an eight-band occupancy mask.  The host fallback
   retains one byte per band for its C implementation. */
extern unsigned char monosh_collision_bullet_bands[8u];

/* L=player-bullet index, H=reflecting EM1/boss-part index. */
void monosh_combat_reflect_bullet(unsigned int packed) __z88dk_fastcall;

void monosh_combat_init(void);
void monosh_combat_update(unsigned char input,
                          signed int player_x,
                          signed int player_bottom);
void monosh_combat_render(void);
void monosh_combat_fast_frame(void);
void monosh_combat_build_collision_bands(void);

#endif
