#include "monosh_far_background.h"
#define FAR_U_HEIGHT 8u
#define FAR_D_HEIGHT 2u
#define FAR_TOTAL_HEIGHT (FAR_U_HEIGHT + FAR_D_HEIGHT)
#define FAR_GROUND_BASE 118u
#define FAR_TOP_BASE (FAR_GROUND_BASE - FAR_TOTAL_HEIGHT)

unsigned int monosh_far_u_scroll_acc;
unsigned int monosh_far_d_scroll_acc;
unsigned char monosh_far_u_offset;
unsigned char monosh_far_d_offset;
unsigned char monosh_far_u_scroll_high;
unsigned char monosh_far_u_scroll_low;
unsigned char monosh_far_d_scroll_high;
unsigned char monosh_far_d_scroll_low;
unsigned char monosh_far_scroll_active;
unsigned char monosh_far_horizon;
unsigned char monosh_far_redraw_count;
static unsigned char far_valid;

void monosh_far_background_fast_scroll(signed int player_x)
    __z88dk_fastcall;

static void redraw(unsigned char ground_offset)
{
    unsigned char top = (unsigned char)(
        FAR_TOP_BASE + ground_offset);
    /* The double-buffered ground renderer restores the previous footprint
       and copies the mountain to the page it is building. */
    monosh_far_horizon = top;
    ++monosh_far_redraw_count;
    far_valid = 1u;
}

void monosh_far_background_init(unsigned char ground_offset)
{
    monosh_far_u_scroll_acc = 0u;
    monosh_far_d_scroll_acc = 0u;
    monosh_far_u_offset = 0u;
    monosh_far_d_offset = 0u;
    monosh_far_u_scroll_high = 0u;
    monosh_far_u_scroll_low = 0u;
    monosh_far_d_scroll_high = 0u;
    monosh_far_d_scroll_low = 0u;
    monosh_far_scroll_active = 0u;
    monosh_far_horizon = 0u;
    monosh_far_redraw_count = 0u;
    far_valid = 0u;
    redraw(ground_offset);
}

void monosh_far_background_reset(unsigned char ground_offset)
{
    monosh_far_u_scroll_acc = 0u;
    monosh_far_d_scroll_acc = 0u;
    monosh_far_u_offset = 0u;
    monosh_far_d_offset = 0u;
    monosh_far_u_scroll_high = 0u;
    monosh_far_u_scroll_low = 0u;
    monosh_far_d_scroll_high = 0u;
    monosh_far_d_scroll_low = 0u;
    monosh_far_scroll_active = 0u;
    redraw(ground_offset);
}

void monosh_far_background_frame(unsigned char world_active,
                                 signed int player_x,
                                 unsigned char ground_offset)
{
    unsigned char top = (unsigned char)(
        FAR_TOP_BASE + ground_offset);

    if (world_active) {
        monosh_far_background_fast_scroll(player_x);
    }
    if (!far_valid || top != monosh_far_horizon) {
        redraw(ground_offset);
    }
}
