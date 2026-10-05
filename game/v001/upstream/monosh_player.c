#include <games.h>
#include "mode3_sprite.h"
#include "monosh_assets.h"
#include "monosh_draw.h"
#include "monosh_player.h"

#define PLAYER_MIN_X       16
#define PLAYER_MAX_X      240
#define PLAYER_MIN_Y       56
#define PLAYER_MAX_Y      201
#define PLAYER_CENTER_Y   120
#define INTRO_TIMER       148u
#define TITLE_TIMER       124u
#define STUMBLE_FIELDS     40u
#define STUMBLE_POSE_SHIFT 3u

signed int monosh_player_x;
signed int monosh_player_bottom;
unsigned char monosh_player_state;
unsigned char monosh_player_invuln;
unsigned char monosh_player_stumble;
unsigned char monosh_player_pose;
unsigned char monosh_stage_title_timer;

static unsigned int player_fy;
static signed char death_vy;
static unsigned char death_timer;
static unsigned char movement_fraction;
static unsigned char death_accel_fraction;
static unsigned char intro_timer;
static unsigned char player_flip;
static unsigned char player_run_phase;
static const unsigned char pose_x_01[19] = {
    128u,124u,120u,116u,116u,112u,108u,104u,100u,100u,
    96u,92u,88u,88u,84u,80u,76u,76u,72u
};
static const unsigned char pose_x_12[19] = {
    72u,72u,72u,68u,68u,68u,64u,64u,64u,60u,
    60u,60u,56u,56u,56u,52u,52u,52u,48u
};
static const unsigned char pose_x_23[19] = {
    8u,8u,8u,8u,8u,8u,8u,8u,8u,8u,
    12u,16u,20u,24u,28u,32u,32u,32u,32u
};
/* One deliberate fall-and-recovery pass.  Each picture lasts eight VBlanks,
   giving the Bush response a 40-field fall-and-recovery arc. */
static const unsigned char stumble_poses[5] = {
    14u, 15u, 16u, 15u, 14u
};

void monosh_player_init(void)
{
    monosh_player_x = 128;
    monosh_player_bottom = PLAYER_MAX_Y;
    player_fy = (unsigned int)PLAYER_MAX_Y << 8;
    monosh_player_state = MONOSH_PLAYER_ALIVE;
    monosh_player_invuln = 0u;
    monosh_player_stumble = 0u;
    monosh_player_pose = 0u;
    monosh_stage_title_timer = TITLE_TIMER;
    intro_timer = INTRO_TIMER;
    death_vy = 0;
    death_timer = 0u;
    movement_fraction = 0u;
    death_accel_fraction = 0u;
    player_flip = 0u;
    player_run_phase = 0u;
}

static void begin_death(void)
{
    monosh_player_state = MONOSH_PLAYER_DEATH_AIR;
    death_vy = -48;
    death_timer = 0u;
    player_fy = (unsigned int)monosh_player_bottom << 8;
    player_flip = 0u;
    monosh_player_pose = 4u;
}

static void update_death(void)
{
    if (monosh_player_state == MONOSH_PLAYER_DEATH_AIR) {
        signed int step = (signed int)death_vy << 4;
        player_fy = (unsigned int)((signed int)player_fy + step);
        /* +1.5 source velocity units per 60 Hz field. */
        death_vy = (signed char)(death_vy + 1 + death_accel_fraction);
        death_accel_fraction ^= 1u;
        monosh_player_bottom = (signed int)(player_fy >> 8);
        ++death_timer;
        if (death_timer < 20u) monosh_player_pose = 4u;
        else if (death_timer < 60u) monosh_player_pose = 5u;
        else monosh_player_pose = 6u;
        if (death_vy >= 0 && monosh_player_bottom >= PLAYER_MAX_Y) {
            monosh_player_bottom = PLAYER_MAX_Y;
            player_fy = (unsigned int)PLAYER_MAX_Y << 8;
            monosh_player_state = MONOSH_PLAYER_DEATH_GROUND;
            death_timer = 0u;
            monosh_player_pose = 7u;
        }
        return;
    }

    ++death_timer;
    if (death_timer < 60u) monosh_player_pose = 7u;
    else if (death_timer < 72u) monosh_player_pose = 8u;
    else if (death_timer < 84u) monosh_player_pose = 9u;
    else monosh_player_pose = 0u;
    if (death_timer >= 108u) {
        monosh_player_state = MONOSH_PLAYER_ALIVE;
        /* O-key invincibility may be enabled while the death animation is
           running.  Do not replace its persistent $ff sentinel with the
           ordinary 30-field post-respawn timer. */
        if (monosh_player_invuln != 0xffu) monosh_player_invuln = 30u;
        death_timer = 0u;
        monosh_player_pose = 0u;
    }
}

static void update_ground_run_pose(unsigned char advance)
{
    if (advance != 0u || monosh_player_pose < 10u ||
        monosh_player_pose > 13u) {
        monosh_player_pose =
            (unsigned char)(10u + (player_run_phase >> 1));
    }
    if (advance != 0u) {
        player_run_phase = (unsigned char)((player_run_phase + 1u) & 7u);
    }
    player_flip = 0u;
}

static void update_intro(void)
{
    if (monosh_stage_title_timer != 0u) {
        --monosh_stage_title_timer;
        if (monosh_stage_title_timer == 0u) monosh_title_draw(0u);
    }
    if (intro_timer == 0u) return;
    --intro_timer;
    if (intro_timer >= 62u) {
        monosh_player_bottom = PLAYER_MAX_Y;
        player_fy = (unsigned int)PLAYER_MAX_Y << 8;
    } else if (intro_timer >= 40u) {
        signed int next = monosh_player_bottom - 4;
        monosh_player_pose = 0u;
        if (next < PLAYER_CENTER_Y) next = PLAYER_CENTER_Y;
        monosh_player_bottom = next;
        player_fy = (unsigned int)next << 8;
    } else {
        monosh_player_pose = 0u;
    }
}

static void update_movement_pose(unsigned char substep)
{
    if (monosh_player_bottom == PLAYER_MAX_Y) {
        /* Movement is split 4+5 pixels over the two 60 Hz fields.  Advance
           the source 30 Hz run animation on only the second half. */
        update_ground_run_pose(substep != 1u);
    } else {
        unsigned char row = (unsigned char)((monosh_player_bottom -
                                             PLAYER_MIN_Y) >> 3);
        unsigned char folded;
        unsigned char right = monosh_player_x > 128 ? 1u : 0u;
        unsigned char pose = monosh_player_pose;
        if (row > 18u) row = 18u;
        folded = (unsigned char)(128 -
            (monosh_player_x >= 128 ? monosh_player_x - 128 :
                                     128 - monosh_player_x));
        player_run_phase = 0u;
        if (pose > 3u) pose = 0u;
        if (folded == 16u) {
            pose = 3u;
        } else if (pose == 0u) {
            if ((unsigned char)(folded + 4u) <= pose_x_01[row]) pose = 1u;
        } else if (pose == 1u) {
            if (folded >= pose_x_01[row]) pose = 0u;
            else if ((unsigned char)(folded + 4u) <= pose_x_12[row]) pose = 2u;
        } else if (pose == 2u) {
            if (folded >= pose_x_12[row]) pose = 1u;
            else if ((unsigned char)(folded + 4u) <= pose_x_23[row]) pose = 3u;
        } else if (folded >= pose_x_23[row]) {
            pose = 2u;
        }
        monosh_player_pose = pose;
        player_flip = pose == 0u ? 0u : right;
    }
}

static void update_movement(unsigned char input, unsigned char substep)
{
    signed int dx = 0;
    signed int dy = 0;
    unsigned char step;

    if ((input & MOVE_LEFT) && !(input & MOVE_RIGHT)) dx = -1;
    else if ((input & MOVE_RIGHT) && !(input & MOVE_LEFT)) dx = 1;
    if ((input & MOVE_UP) && !(input & MOVE_DOWN)) dy = 1;
    else if ((input & MOVE_DOWN) && !(input & MOVE_UP)) dy = -1;
    if (dx != 0 && dy != 0) {
        step = substep == 1u ? 3 : (substep == 2u ? 4 : 7);
    } else {
        step = substep == 1u ? 4 : (substep == 2u ? 5 : 9);
    }
    /* dx/dy are only -1, 0 or +1.  Branching avoids two general signed
       multiplies on every displayed field. */
    if (dx < 0) monosh_player_x -= step;
    else if (dx > 0) monosh_player_x += step;
    if (dy < 0) monosh_player_bottom -= step;
    else if (dy > 0) monosh_player_bottom += step;
    if (monosh_player_x < PLAYER_MIN_X) monosh_player_x = PLAYER_MIN_X;
    if (monosh_player_x > PLAYER_MAX_X) monosh_player_x = PLAYER_MAX_X;
    if (monosh_player_bottom < PLAYER_MIN_Y) monosh_player_bottom = PLAYER_MIN_Y;
    if (monosh_player_bottom > PLAYER_MAX_Y) monosh_player_bottom = PLAYER_MAX_Y;
    player_fy = (unsigned int)monosh_player_bottom << 8;
    update_movement_pose(substep);
}

void monosh_player_update(unsigned char input, unsigned char hit)
{
    unsigned char movement = (unsigned char)(
        input & (MOVE_LEFT | MOVE_RIGHT | MOVE_UP | MOVE_DOWN));

    /* Collision, controls, timers and death physics are sampled at 60 Hz. */
    if (hit == 1u && monosh_player_state == MONOSH_PLAYER_ALIVE &&
        monosh_player_invuln == 0u) {
        begin_death();
        monosh_player_stumble = 0u;
    } else if (hit == 2u && monosh_player_state == MONOSH_PLAYER_ALIVE &&
               monosh_player_stumble == 0u) {
        monosh_player_stumble = STUMBLE_FIELDS;
        /* MonoSH's bush stumble always starts on the Stage 1 ground line.
           PLAYER_CENTER_Y was a coordinate-system mix-up that visibly
           teleported the player upward before the first stumble pose. */
        monosh_player_bottom = PLAYER_MAX_Y;
        player_fy = (unsigned int)PLAYER_MAX_Y << 8;
        monosh_player_pose = 14u;
        player_flip = 0u;
        player_run_phase = 0u;
    }

    /* $ff is the O-key persistent invincibility sentinel. */
    if (monosh_player_invuln != 0u && monosh_player_invuln != 0xffu) {
        --monosh_player_invuln;
    }
    if (monosh_player_state != MONOSH_PLAYER_ALIVE) {
        update_death();
        return;
    }

    update_intro();
    if (monosh_player_stumble != 0u) {
        unsigned char stumble_index =
            (unsigned char)((STUMBLE_FIELDS - monosh_player_stumble) >>
                            STUMBLE_POSE_SHIFT);
        monosh_player_pose = stumble_poses[stumble_index];
        --monosh_player_stumble;
        /* The NES source keeps this animation facing one direction.  The old
           60 Hz port toggled FLIP_X every two fields, which made the stumble
           look like unrelated poses flashing back and forth. */
        player_flip = 0u;
        player_run_phase = 0u;
        return;
    }
    /* The source masks only UP/DOWN during the scripted hold/rise.  Keep
       LEFT/RIGHT live, and let the common movement/pose path below advance
       exactly once per field. */
    if (intro_timer >= 40u) {
        input &= (unsigned char)(MOVE_LEFT | MOVE_RIGHT);
        movement = (unsigned char)(input & (MOVE_LEFT | MOVE_RIGHT));
    }

    if (movement != 0u) {
        /* Preserve exactly 9 cardinal or 7 diagonal pixels per original
           30 Hz tick, split as 4+5 or 3+4 over two independently sampled
           60 Hz inputs. */
        movement_fraction ^= 1u;
        update_movement(input, movement_fraction != 0u ? 1u : 2u);
    } else {
        if (monosh_player_bottom != PLAYER_MAX_Y) return;
        /* Forward motion never stops in Space Harrier.  At the ground limit
           the player keeps running even with no lateral/vertical input. */
        movement_fraction ^= 1u;
        update_ground_run_pose(movement_fraction == 0u);
    }
}

unsigned char monosh_player_draw_flags(void)
{
    unsigned char flags = player_flip ? MODE3_FLIP_X : 0u;
    /* O-key invincibility uses the persistent $ff sentinel and must retain
       the normal player colours.  Timed post-death invulnerability keeps
       its existing visual feedback. */
    if (monosh_player_invuln != 0u && monosh_player_invuln != 0xffu &&
        (monosh_player_invuln & 1u)) {
        flags |= MODE3_BLEND_50;
    }
    return flags;
}

unsigned char monosh_player_draw_asset(void)
{
    if (monosh_player_pose == 0u) return MONOSH_DRAW_PLAYER;
    if (monosh_player_pose < 4u) {
        return (unsigned char)(MONOSH_DRAW_PLAYER_FLIGHT1 +
                               monosh_player_pose - 1u);
    }
    if (monosh_player_pose >= 10u) {
        return (unsigned char)(MONOSH_DRAW_PLAYER_RUN0 +
                               monosh_player_pose - 10u);
    }
    return (unsigned char)(MONOSH_DRAW_PLAYER_DEATH1 +
                           monosh_player_pose - 4u);
}

unsigned char monosh_player_world_active(void)
{
    return (unsigned char)(monosh_player_state == MONOSH_PLAYER_ALIVE);
}

unsigned char monosh_player_can_fire(void)
{
    return (unsigned char)(monosh_player_state == MONOSH_PLAYER_ALIVE &&
                           monosh_player_stumble == 0u);
}
