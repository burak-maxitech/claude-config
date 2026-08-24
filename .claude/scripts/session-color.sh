#!/usr/bin/env bash
# session-color.sh
# Sticky per-project session color allocation for the cc launcher.
# Source this file, then call: cc_session_color <project-name> [registry-path]
# Sourcing has no side effects. bash 3.2 compatible (macOS ships 3.2).
#
# Prints the color on stdout and returns 0. Prints nothing and returns 1 when
# the registry cannot be read or written, so the caller can launch uncolored.

CC_COLOR_PALETTE="cyan green blue purple orange pink yellow red"
CC_REGISTRY_HEADER="# cc session colors - auto-assigned, safe to delete (colors get reassigned)"

_cc_trim() {
    local s="$1"
    s="${s#"${s%%[![:space:]]*}"}"
    s="${s%"${s##*[![:space:]]}"}"
    printf '%s' "$s"
}

# Serialise the whole read-decide-append below. Two launches racing here both
# observe the same registry state and both claim the same color, which defeats
# the "distinct AND stable" goal the registry exists for. mkdir is atomic on
# every POSIX filesystem, so it is the portable mutex.
#
# A launch is never blocked by this: after ~10s we give up and proceed unlocked,
# which is exactly the old behaviour, so the worst case is the status quo and
# never worse. A lock orphaned by a killed process is reaped on age.
#
# The backoff is 20ms, not 100ms, and that matters: every waiter wakes and
# retries together, so the expected wait grows with the number of contenders.
# At 100ms, eight simultaneous launches took ~4.1s against a 5s cap — close
# enough that any extra load pushed late processes past the cap and into the
# unlocked path, reintroducing the exact collision this lock exists to stop.
# Measured 8-way contention at 20ms: well under 1s.
cc_session_color() {
    local registry_arg="${2:-$HOME/.claude/cc-session-colors}"
    local lock="${registry_arg}.lock" waited=0 rc=0 lock_dir=""
    lock_dir="$(dirname "$registry_arg")"
    [ -d "$lock_dir" ] || mkdir -p "$lock_dir" 2>/dev/null || return 1

    while ! mkdir "$lock" 2>/dev/null; do
        waited=$((waited + 1))
        if [ "$waited" -gt 500 ]; then
            # Budget (~10s) exhausted: either extreme contention or a lock
            # orphaned by a process killed while holding it. Reap ONCE and make
            # a final attempt. Never reap inside the loop — an age check there
            # runs on every retry, and a `find` that fails for any reason reads
            # as "stale" and rmdir's a LIVE lock, letting several processes into
            # the critical section. That is worse than no lock at all, and it is
            # exactly what an earlier version of this function did.
            rmdir "$lock" 2>/dev/null
            mkdir "$lock" 2>/dev/null || true
            break
        fi
        sleep 0.02
    done

    _cc_session_color_unlocked "$@"
    rc=$?
    rmdir "$lock" 2>/dev/null
    return $rc
}

_cc_session_color_unlocked() {
    local project="$1"
    local registry="${2:-$HOME/.claude/cc-session-colors}"
    local names=() colors=()
    # Every scalar is initialised: `local x` leaves x unset, and reading an unset
    # variable under `set -u` (which start-claude.sh sets) aborts the shell.
    local line="" name="" color="" candidate="" count=0
    local chosen="" best="" best_count=-1 i=0 dir=""

    # --- Read. A missing file is an empty registry, not a failure. ---
    if [ -e "$registry" ]; then
        [ -r "$registry" ] || return 1
        while IFS= read -r line || [ -n "$line" ]; do
            line="${line%$'\r'}"                       # tolerate CRLF registries
            line="$(_cc_trim "$line")"
            [ -z "$line" ] && continue
            case "$line" in \#*) continue ;; esac
            case "$line" in *=*) ;; *) continue ;; esac
            name="$(_cc_trim "${line%%=*}")"
            color="${line#*=}"
            case "$color" in *=*) continue ;; esac      # 2+ separators
            color="$(_cc_trim "$color" | tr '[:upper:]' '[:lower:]')"
            [ -n "$name" ] || continue
            case " $CC_COLOR_PALETTE " in *" $color "*) ;; *) continue ;; esac
            names+=("$name")
            colors+=("$color")
        done < "$registry"
    fi

    # --- A known project keeps its color, and the file is left untouched. ---
    i=0
    while [ "$i" -lt "${#names[@]}" ]; do
        if [ "$(printf '%s' "${names[$i]}" | tr '[:upper:]' '[:lower:]')" = "$(printf '%s' "$project" | tr '[:upper:]' '[:lower:]')" ]; then
            printf '%s\n' "${colors[$i]}"
            return 0
        fi
        i=$((i + 1))
    done

    # --- First unused color, else least-used (strict < keeps palette order on ties). ---
    chosen=""; best=""; best_count=-1
    for candidate in $CC_COLOR_PALETTE; do
        count=0
        i=0
        while [ "$i" -lt "${#colors[@]}" ]; do
            if [ "${colors[$i]}" = "$candidate" ]; then count=$((count + 1)); fi
            i=$((i + 1))
        done
        if [ "$count" -eq 0 ]; then chosen="$candidate"; break; fi
        if [ "$best_count" -lt 0 ] || [ "$count" -lt "$best_count" ]; then
            best_count="$count"; best="$candidate"
        fi
    done
    [ -n "$chosen" ] || chosen="$best"

    # --- Persist. Any failure here means "no color", not a broken launch. ---
    dir="$(dirname "$registry")"
    if [ ! -d "$dir" ]; then mkdir -p "$dir" 2>/dev/null || return 1; fi
    # -s, not -e: a 0-byte registry counts as missing, or an existing-but-empty
    # file would skip the header forever and leave the file unexplained.
    if [ ! -s "$registry" ]; then
        printf '%s\n' "$CC_REGISTRY_HEADER" > "$registry" 2>/dev/null || return 1
    fi
    printf '%s=%s\n' "$project" "$chosen" >> "$registry" 2>/dev/null || return 1

    printf '%s\n' "$chosen"
    return 0
}
