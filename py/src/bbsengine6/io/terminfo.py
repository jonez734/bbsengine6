"""Pure-Python reader for the compiled terminfo database.

No ``curses`` and no ``infocmp`` at runtime. The search order follows ncurses:
``$TERMINFO``, then ``$TERMINFO_DIRS``, then ``~/.terminfo``, then the system directories.

Public API::

    find(name)      -> pathlib.Path | None
    load(name)      -> Terminfo          (raises TerminfoError)
    has_entry(name) -> bool              (cached)
    clear_cache()

Binary layout: see handbook/io/todo/terminfo.md, Part A.
"""

from __future__ import annotations

import os
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Tuple

__all__ = [
    "Terminfo",
    "TerminfoError",
    "find",
    "load",
    "has_entry",
    "clear_cache",
    "BOOL_CAPS",
    "NUM_CAPS",
    "STR_CAPS",
]

MAGIC_LEGACY = 0o432  # 16-bit numbers
MAGIC_EXTENDED = 0o1036  # 32-bit numbers

ABSENT = -1
CANCELLED = -2

SYSTEM_DIRS = (
    "/etc/terminfo",
    "/lib/terminfo",
    "/usr/share/terminfo",
    "/usr/lib/terminfo",
)


class TerminfoError(Exception):
    """A terminfo entry is missing, truncated, or not in the expected format."""


# ---------------------------------------------------------------------------
# Standard capability names, in the index order used by the binary format.
# Generated from terminfo(5); see handbook/io/todo/terminfo.md. Do not reorder.
# ---------------------------------------------------------------------------

BOOL_CAPS = (
    ("auto_left_margin", "bw"),
    ("auto_right_margin", "am"),
    ("no_esc_ctlc", "xsb"),
    ("ceol_standout_glitch", "xhp"),
    ("eat_newline_glitch", "xenl"),
    ("erase_overstrike", "eo"),
    ("generic_type", "gn"),
    ("hard_copy", "hc"),
    ("has_meta_key", "km"),
    ("has_status_line", "hs"),
    ("insert_null_glitch", "in"),
    ("memory_above", "da"),
    ("memory_below", "db"),
    ("move_insert_mode", "mir"),
    ("move_standout_mode", "msgr"),
    ("over_strike", "os"),
    ("status_line_esc_ok", "eslok"),
    ("dest_tabs_magic_smso", "xt"),
    ("tilde_glitch", "hz"),
    ("transparent_underline", "ul"),
    ("xon_xoff", "xon"),
    ("needs_xon_xoff", "nxon"),
    ("prtr_silent", "mc5i"),
    ("hard_cursor", "chts"),
    ("non_rev_rmcup", "nrrmc"),
    ("no_pad_char", "npc"),
    ("non_dest_scroll_region", "ndscr"),
    ("can_change", "ccc"),
    ("back_color_erase", "bce"),
    ("hue_lightness_saturation", "hls"),
    ("col_addr_glitch", "xhpa"),
    ("cr_cancels_micro_mode", "crxm"),
    ("has_print_wheel", "daisy"),
    ("row_addr_glitch", "xvpa"),
    ("semi_auto_right_margin", "sam"),
    ("cpi_changes_res", "cpix"),
    ("lpi_changes_res", "lpix"),
)

NUM_CAPS = (
    ("columns", "cols"),
    ("init_tabs", "it"),
    ("lines", "lines"),
    ("lines_of_memory", "lm"),
    ("magic_cookie_glitch", "xmc"),
    ("padding_baud_rate", "pb"),
    ("virtual_terminal", "vt"),
    ("width_status_line", "wsl"),
    ("num_labels", "nlab"),
    ("label_height", "lh"),
    ("label_width", "lw"),
    ("max_attributes", "ma"),
    ("maximum_windows", "wnum"),
    ("max_colors", "colors"),
    ("max_pairs", "pairs"),
    ("no_color_video", "ncv"),
    ("buffer_capacity", "bufsz"),
    ("dot_vert_spacing", "spinv"),
    ("dot_horz_spacing", "spinh"),
    ("max_micro_address", "maddr"),
    ("max_micro_jump", "mjump"),
    ("micro_col_size", "mcs"),
    ("micro_line_size", "mls"),
    ("number_of_pins", "npins"),
    ("output_res_char", "orc"),
    ("output_res_line", "orl"),
    ("output_res_horz_inch", "orhi"),
    ("output_res_vert_inch", "orvi"),
    ("print_rate", "cps"),
    ("wide_char_size", "widcs"),
    ("buttons", "btns"),
    ("bit_image_entwining", "bitwin"),
    ("bit_image_type", "bitype"),
)

STR_CAPS = (
    ("back_tab", "cbt"),
    ("bell", "bel"),
    ("carriage_return", "cr"),
    ("change_scroll_region", "csr"),
    ("clear_all_tabs", "tbc"),
    ("clear_screen", "clear"),
    ("clr_eol", "el"),
    ("clr_eos", "ed"),
    ("column_address", "hpa"),
    ("command_character", "cmdch"),
    ("cursor_address", "cup"),
    ("cursor_down", "cud1"),
    ("cursor_home", "home"),
    ("cursor_invisible", "civis"),
    ("cursor_left", "cub1"),
    ("cursor_mem_address", "mrcup"),
    ("cursor_normal", "cnorm"),
    ("cursor_right", "cuf1"),
    ("cursor_to_ll", "ll"),
    ("cursor_up", "cuu1"),
    ("cursor_visible", "cvvis"),
    ("delete_character", "dch1"),
    ("delete_line", "dl1"),
    ("dis_status_line", "dsl"),
    ("down_half_line", "hd"),
    ("enter_alt_charset_mode", "smacs"),
    ("enter_blink_mode", "blink"),
    ("enter_bold_mode", "bold"),
    ("enter_ca_mode", "smcup"),
    ("enter_delete_mode", "smdc"),
    ("enter_dim_mode", "dim"),
    ("enter_insert_mode", "smir"),
    ("enter_secure_mode", "invis"),
    ("enter_protected_mode", "prot"),
    ("enter_reverse_mode", "rev"),
    ("enter_standout_mode", "smso"),
    ("enter_underline_mode", "smul"),
    ("erase_chars", "ech"),
    ("exit_alt_charset_mode", "rmacs"),
    ("exit_attribute_mode", "sgr0"),
    ("exit_ca_mode", "rmcup"),
    ("exit_delete_mode", "rmdc"),
    ("exit_insert_mode", "rmir"),
    ("exit_standout_mode", "rmso"),
    ("exit_underline_mode", "rmul"),
    ("flash_screen", "flash"),
    ("form_feed", "ff"),
    ("from_status_line", "fsl"),
    ("init_1string", "is1"),
    ("init_2string", "is2"),
    ("init_3string", "is3"),
    ("init_file", "if"),
    ("insert_character", "ich1"),
    ("insert_line", "il1"),
    ("insert_padding", "ip"),
    ("key_backspace", "kbs"),
    ("key_catab", "ktbc"),
    ("key_clear", "kclr"),
    ("key_ctab", "kctab"),
    ("key_dc", "kdch1"),
    ("key_dl", "kdl1"),
    ("key_down", "kcud1"),
    ("key_eic", "krmir"),
    ("key_eol", "kel"),
    ("key_eos", "ked"),
    ("key_f0", "kf0"),
    ("key_f1", "kf1"),
    ("key_f10", "kf10"),
    ("key_f2", "kf2"),
    ("key_f3", "kf3"),
    ("key_f4", "kf4"),
    ("key_f5", "kf5"),
    ("key_f6", "kf6"),
    ("key_f7", "kf7"),
    ("key_f8", "kf8"),
    ("key_f9", "kf9"),
    ("key_home", "khome"),
    ("key_ic", "kich1"),
    ("key_il", "kil1"),
    ("key_left", "kcub1"),
    ("key_ll", "kll"),
    ("key_npage", "knp"),
    ("key_ppage", "kpp"),
    ("key_right", "kcuf1"),
    ("key_sf", "kind"),
    ("key_sr", "kri"),
    ("key_stab", "khts"),
    ("key_up", "kcuu1"),
    ("keypad_local", "rmkx"),
    ("keypad_xmit", "smkx"),
    ("lab_f0", "lf0"),
    ("lab_f1", "lf1"),
    ("lab_f10", "lf10"),
    ("lab_f2", "lf2"),
    ("lab_f3", "lf3"),
    ("lab_f4", "lf4"),
    ("lab_f5", "lf5"),
    ("lab_f6", "lf6"),
    ("lab_f7", "lf7"),
    ("lab_f8", "lf8"),
    ("lab_f9", "lf9"),
    ("meta_off", "rmm"),
    ("meta_on", "smm"),
    ("newline", "nel"),
    ("pad_char", "pad"),
    ("parm_dch", "dch"),
    ("parm_delete_line", "dl"),
    ("parm_down_cursor", "cud"),
    ("parm_ich", "ich"),
    ("parm_index", "indn"),
    ("parm_insert_line", "il"),
    ("parm_left_cursor", "cub"),
    ("parm_right_cursor", "cuf"),
    ("parm_rindex", "rin"),
    ("parm_up_cursor", "cuu"),
    ("pkey_key", "pfkey"),
    ("pkey_local", "pfloc"),
    ("pkey_xmit", "pfx"),
    ("print_screen", "mc0"),
    ("prtr_off", "mc4"),
    ("prtr_on", "mc5"),
    ("repeat_char", "rep"),
    ("reset_1string", "rs1"),
    ("reset_2string", "rs2"),
    ("reset_3string", "rs3"),
    ("reset_file", "rf"),
    ("restore_cursor", "rc"),
    ("row_address", "vpa"),
    ("save_cursor", "sc"),
    ("scroll_forward", "ind"),
    ("scroll_reverse", "ri"),
    ("set_attributes", "sgr"),
    ("set_tab", "hts"),
    ("set_window", "wind"),
    ("tab", "ht"),
    ("to_status_line", "tsl"),
    ("underline_char", "uc"),
    ("up_half_line", "hu"),
    ("init_prog", "iprog"),
    ("key_a1", "ka1"),
    ("key_a3", "ka3"),
    ("key_b2", "kb2"),
    ("key_c1", "kc1"),
    ("key_c3", "kc3"),
    ("prtr_non", "mc5p"),
    ("char_padding", "rmp"),
    ("acs_chars", "acsc"),
    ("plab_norm", "pln"),
    ("key_btab", "kcbt"),
    ("enter_xon_mode", "smxon"),
    ("exit_xon_mode", "rmxon"),
    ("enter_am_mode", "smam"),
    ("exit_am_mode", "rmam"),
    ("xon_character", "xonc"),
    ("xoff_character", "xoffc"),
    ("ena_acs", "enacs"),
    ("label_on", "smln"),
    ("label_off", "rmln"),
    ("key_beg", "kbeg"),
    ("key_cancel", "kcan"),
    ("key_close", "kclo"),
    ("key_command", "kcmd"),
    ("key_copy", "kcpy"),
    ("key_create", "kcrt"),
    ("key_end", "kend"),
    ("key_enter", "kent"),
    ("key_exit", "kext"),
    ("key_find", "kfnd"),
    ("key_help", "khlp"),
    ("key_mark", "kmrk"),
    ("key_message", "kmsg"),
    ("key_move", "kmov"),
    ("key_next", "knxt"),
    ("key_open", "kopn"),
    ("key_options", "kopt"),
    ("key_previous", "kprv"),
    ("key_print", "kprt"),
    ("key_redo", "krdo"),
    ("key_reference", "kref"),
    ("key_refresh", "krfr"),
    ("key_replace", "krpl"),
    ("key_restart", "krst"),
    ("key_resume", "kres"),
    ("key_save", "ksav"),
    ("key_suspend", "kspd"),
    ("key_undo", "kund"),
    ("key_sbeg", "kBEG"),
    ("key_scancel", "kCAN"),
    ("key_scommand", "kCMD"),
    ("key_scopy", "kCPY"),
    ("key_screate", "kCRT"),
    ("key_sdc", "kDC"),
    ("key_sdl", "kDL"),
    ("key_select", "kslt"),
    ("key_send", "kEND"),
    ("key_seol", "kEOL"),
    ("key_sexit", "kEXT"),
    ("key_sfind", "kFND"),
    ("key_shelp", "kHLP"),
    ("key_shome", "kHOM"),
    ("key_sic", "kIC"),
    ("key_sleft", "kLFT"),
    ("key_smessage", "kMSG"),
    ("key_smove", "kMOV"),
    ("key_snext", "kNXT"),
    ("key_soptions", "kOPT"),
    ("key_sprevious", "kPRV"),
    ("key_sprint", "kPRT"),
    ("key_sredo", "kRDO"),
    ("key_sreplace", "kRPL"),
    ("key_sright", "kRIT"),
    ("key_srsume", "kRES"),
    ("key_ssave", "kSAV"),
    ("key_ssuspend", "kSPD"),
    ("key_sundo", "kUND"),
    ("req_for_input", "rfi"),
    ("key_f11", "kf11"),
    ("key_f12", "kf12"),
    ("key_f13", "kf13"),
    ("key_f14", "kf14"),
    ("key_f15", "kf15"),
    ("key_f16", "kf16"),
    ("key_f17", "kf17"),
    ("key_f18", "kf18"),
    ("key_f19", "kf19"),
    ("key_f20", "kf20"),
    ("key_f21", "kf21"),
    ("key_f22", "kf22"),
    ("key_f23", "kf23"),
    ("key_f24", "kf24"),
    ("key_f25", "kf25"),
    ("key_f26", "kf26"),
    ("key_f27", "kf27"),
    ("key_f28", "kf28"),
    ("key_f29", "kf29"),
    ("key_f30", "kf30"),
    ("key_f31", "kf31"),
    ("key_f32", "kf32"),
    ("key_f33", "kf33"),
    ("key_f34", "kf34"),
    ("key_f35", "kf35"),
    ("key_f36", "kf36"),
    ("key_f37", "kf37"),
    ("key_f38", "kf38"),
    ("key_f39", "kf39"),
    ("key_f40", "kf40"),
    ("key_f41", "kf41"),
    ("key_f42", "kf42"),
    ("key_f43", "kf43"),
    ("key_f44", "kf44"),
    ("key_f45", "kf45"),
    ("key_f46", "kf46"),
    ("key_f47", "kf47"),
    ("key_f48", "kf48"),
    ("key_f49", "kf49"),
    ("key_f50", "kf50"),
    ("key_f51", "kf51"),
    ("key_f52", "kf52"),
    ("key_f53", "kf53"),
    ("key_f54", "kf54"),
    ("key_f55", "kf55"),
    ("key_f56", "kf56"),
    ("key_f57", "kf57"),
    ("key_f58", "kf58"),
    ("key_f59", "kf59"),
    ("key_f60", "kf60"),
    ("key_f61", "kf61"),
    ("key_f62", "kf62"),
    ("key_f63", "kf63"),
    ("clr_bol", "el1"),
    ("clear_margins", "mgc"),
    ("set_left_margin", "smgl"),
    ("set_right_margin", "smgr"),
    ("label_format", "fln"),
    ("set_clock", "sclk"),
    ("display_clock", "dclk"),
    ("remove_clock", "rmclk"),
    ("create_window", "cwin"),
    ("goto_window", "wingo"),
    ("hangup", "hup"),
    ("dial_phone", "dial"),
    ("quick_dial", "qdial"),
    ("tone", "tone"),
    ("pulse", "pulse"),
    ("flash_hook", "hook"),
    ("fixed_pause", "pause"),
    ("wait_tone", "wait"),
    ("user0", "u0"),
    ("user1", "u1"),
    ("user2", "u2"),
    ("user3", "u3"),
    ("user4", "u4"),
    ("user5", "u5"),
    ("user6", "u6"),
    ("user7", "u7"),
    ("user8", "u8"),
    ("user9", "u9"),
    ("orig_pair", "op"),
    ("orig_colors", "oc"),
    ("initialize_color", "initc"),
    ("initialize_pair", "initp"),
    ("set_color_pair", "scp"),
    ("set_foreground", "setf"),
    ("set_background", "setb"),
    ("change_char_pitch", "cpi"),
    ("change_line_pitch", "lpi"),
    ("change_res_horz", "chr"),
    ("change_res_vert", "cvr"),
    ("define_char", "defc"),
    ("enter_doublewide_mode", "swidm"),
    ("enter_draft_quality", "sdrfq"),
    ("enter_italics_mode", "sitm"),
    ("enter_leftward_mode", "slm"),
    ("enter_micro_mode", "smicm"),
    ("enter_near_letter_quality", "snlq"),
    ("enter_normal_quality", "snrmq"),
    ("enter_shadow_mode", "sshm"),
    ("enter_subscript_mode", "ssubm"),
    ("enter_superscript_mode", "ssupm"),
    ("enter_upward_mode", "sum"),
    ("exit_doublewide_mode", "rwidm"),
    ("exit_italics_mode", "ritm"),
    ("exit_leftward_mode", "rlm"),
    ("exit_micro_mode", "rmicm"),
    ("exit_shadow_mode", "rshm"),
    ("exit_subscript_mode", "rsubm"),
    ("exit_superscript_mode", "rsupm"),
    ("exit_upward_mode", "rum"),
    ("micro_column_address", "mhpa"),
    ("micro_down", "mcud1"),
    ("micro_left", "mcub1"),
    ("micro_right", "mcuf1"),
    ("micro_row_address", "mvpa"),
    ("micro_up", "mcuu1"),
    ("order_of_pins", "porder"),
    ("parm_down_micro", "mcud"),
    ("parm_left_micro", "mcub"),
    ("parm_right_micro", "mcuf"),
    ("parm_up_micro", "mcuu"),
    ("select_char_set", "scs"),
    ("set_bottom_margin", "smgb"),
    ("set_bottom_margin_parm", "smgbp"),
    ("set_left_margin_parm", "smglp"),
    ("set_right_margin_parm", "smgrp"),
    ("set_top_margin", "smgt"),
    ("set_top_margin_parm", "smgtp"),
    ("start_bit_image", "sbim"),
    ("start_char_set_def", "scsd"),
    ("stop_bit_image", "rbim"),
    ("stop_char_set_def", "rcsd"),
    ("subscript_characters", "subcs"),
    ("superscript_characters", "supcs"),
    ("these_cause_cr", "docr"),
    ("zero_motion", "zerom"),
    ("char_set_names", "csnm"),
    ("key_mouse", "kmous"),
    ("mouse_info", "minfo"),
    ("req_mouse_pos", "reqmp"),
    ("get_mouse", "getm"),
    ("set_a_foreground", "setaf"),
    ("set_a_background", "setab"),
    ("pkey_plab", "pfxl"),
    ("device_type", "devt"),
    ("code_set_init", "csin"),
    ("set0_des_seq", "s0ds"),
    ("set1_des_seq", "s1ds"),
    ("set2_des_seq", "s2ds"),
    ("set3_des_seq", "s3ds"),
    ("set_lr_margin", "smglr"),
    ("set_tb_margin", "smgtb"),
    ("bit_image_repeat", "birep"),
    ("bit_image_newline", "binel"),
    ("bit_image_carriage_return", "bicr"),
    ("color_names", "colornm"),
    ("define_bit_image_region", "defbi"),
    ("end_bit_image_region", "endbi"),
    ("set_color_band", "setcolor"),
    ("set_page_length", "slines"),
    ("display_pc_char", "dispc"),
    ("enter_pc_charset_mode", "smpch"),
    ("exit_pc_charset_mode", "rmpch"),
    ("enter_scancode_mode", "smsc"),
    ("exit_scancode_mode", "rmsc"),
    ("pc_term_options", "pctrm"),
    ("scancode_escape", "scesc"),
    ("alt_scancode_esc", "scesa"),
    ("enter_horizontal_hl_mode", "ehhlm"),
    ("enter_left_hl_mode", "elhlm"),
    ("enter_low_hl_mode", "elohlm"),
    ("enter_right_hl_mode", "erhlm"),
    ("enter_top_hl_mode", "ethlm"),
    ("enter_vertical_hl_mode", "evhlm"),
    ("set_a_attributes", "sgr1"),
    ("set_pglen_inch", "slength"),
)


@dataclass
class Terminfo:
    """A parsed terminfo entry.

    ``bools``, ``nums``, and ``strs`` are keyed by capname (for example ``cols``,
    ``cup``, ``setaf``). Standard and extended capabilities share the same dicts.
    """

    name: str
    path: Path
    bools: Dict[str, bool] = field(default_factory=dict)
    nums: Dict[str, int] = field(default_factory=dict)
    strs: Dict[str, str] = field(default_factory=dict)

    def get(self, cap: str):
        """Return the value of ``cap``, or None if it is absent or cancelled.

        Booleans are True or False. Numbers are int. Strings are str, decoded as latin-1
        so escape bytes survive unchanged. Padding markers such as ``$<5>`` are kept.
        """
        if cap in self.strs:
            return self.strs[cap]
        if cap in self.nums:
            return self.nums[cap]
        if cap in self.bools:
            return self.bools[cap]
        return None


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------

_cache: Dict[str, Optional[Path]] = {}
_entry_cache: Dict[str, bool] = {}


def _valid_name(name: str) -> bool:
    if not name or name.startswith("."):
        return False
    if "/" in name or "\x00" in name:
        return False
    return True


def _search_dirs() -> Tuple[str, ...]:
    """Directories in ncurses order: $TERMINFO, ~/.terminfo, $TERMINFO_DIRS, system."""
    dirs = []
    single = os.environ.get("TERMINFO")
    if single:
        dirs.append(single)

    dirs.append(os.path.expanduser("~/.terminfo"))

    multi = os.environ.get("TERMINFO_DIRS")
    if multi is None:
        dirs.extend(SYSTEM_DIRS)
    else:
        for part in multi.split(":"):
            if part == "":
                # An empty entry means the system default list (terminfo(5)).
                dirs.extend(SYSTEM_DIRS)
            else:
                dirs.append(part)
    return tuple(dirs)


def _candidates(directory: str, name: str):
    first = name[0]
    yield Path(directory) / first / name
    yield Path(directory) / format(ord(first), "x") / name


def find(name: str) -> Optional[Path]:
    """Return the path of the compiled entry for ``name``, or None."""
    if name in _cache:
        return _cache[name]
    found: Optional[Path] = None
    if _valid_name(name):
        for directory in _search_dirs():
            for path in _candidates(directory, name):
                if path.is_file():
                    found = path
                    break
            if found is not None:
                break
    _cache[name] = found
    return found


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


def _cstr(data: bytes, offset: int, what: str) -> str:
    end = data.find(b"\x00", offset)
    if end < 0:
        raise TerminfoError(f"{what}: string at offset {offset} is not NUL-terminated")
    return data[offset:end].decode("latin-1")


def _check_range(data: bytes, start: int, length: int, what: str) -> None:
    if start < 0 or start + length > len(data):
        raise TerminfoError(f"{what}: section past end of file")


def _parse(data: bytes, name: str, path: Path) -> Terminfo:
    if len(data) < 12:
        raise TerminfoError(f"{path}: file shorter than the 12-byte header")

    magic, name_size, bool_count, num_count, str_count, str_size = struct.unpack_from(
        "<6h", data, 0
    )
    if magic == MAGIC_LEGACY:
        num_width, num_fmt = 2, "<h"
    elif magic == MAGIC_EXTENDED:
        num_width, num_fmt = 4, "<i"
    else:
        raise TerminfoError(f"{path}: bad magic number {magic:#o}")

    if min(name_size, bool_count, num_count, str_count, str_size) < 0:
        raise TerminfoError(f"{path}: negative section size")

    offset = 12
    _check_range(data, offset, name_size, f"{path} names")
    offset += name_size
    _check_range(data, offset, bool_count, f"{path} booleans")
    bools_raw = data[offset : offset + bool_count]
    offset += bool_count

    if offset % 2:
        offset += 1  # pad so the numbers start on an even boundary

    _check_range(data, offset, num_count * num_width, f"{path} numbers")
    nums_raw = [
        struct.unpack_from(num_fmt, data, offset + i * num_width)[0]
        for i in range(num_count)
    ]
    offset += num_count * num_width

    _check_range(data, offset, str_count * 2, f"{path} string offsets")
    str_offsets = list(struct.unpack_from(f"<{str_count}h", data, offset))
    offset += str_count * 2

    _check_range(data, offset, str_size, f"{path} string table")
    table = data[offset : offset + str_size]
    offset += str_size

    info = Terminfo(name=name, path=path)

    for i, value in enumerate(bools_raw):
        if i < len(BOOL_CAPS):
            info.bools[BOOL_CAPS[i][1]] = bool(value)

    for i, value in enumerate(nums_raw):
        if i < len(NUM_CAPS) and value not in (ABSENT, CANCELLED):
            info.nums[NUM_CAPS[i][1]] = value

    for i, off in enumerate(str_offsets):
        if i < len(STR_CAPS) and off not in (ABSENT, CANCELLED):
            if off < 0 or off >= len(table):
                raise TerminfoError(f"{path}: string offset {off} outside table")
            info.strs[STR_CAPS[i][1]] = _cstr(table, off, str(path))

    # Extended capabilities (ncurses user-defined entries, after the standard section)
    # are not parsed yet. Their offset layout is unverified, so they are left out rather
    # than returned wrong. See handbook/io/todo/terminfo.md, "Extended capabilities".
    _ = offset

    return info


def load(name: str) -> Terminfo:
    """Parse the entry for ``name``. Raises TerminfoError if it is missing or corrupt."""
    path = find(name)
    if path is None:
        raise TerminfoError(f"no terminfo entry for {name!r}")
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise TerminfoError(f"{path}: {exc}") from exc
    return _parse(data, name, path)


def has_entry(name: str) -> bool:
    """True if ``name`` names a terminfo entry that parses. Cached per name."""
    if name in _entry_cache:
        return _entry_cache[name]
    try:
        load(name)
        ok = True
    except TerminfoError:
        ok = False
    _entry_cache[name] = ok
    return ok


def clear_cache() -> None:
    """Forget cached lookups (used by tests and after a terminfo change)."""
    _cache.clear()
    _entry_cache.clear()
