# Rootless podman setup for a batch node, sourced by anything that runs a
# container on the cluster.
#
# Sourced, not executed: it exports variables and installs an EXIT trap that the
# caller needs. Reads $USE_PODMAN (only acts when true) and $LSB_JOBID (only the
# per-job parts apply under LSF); writes CONTAINERS_STORAGE_CONF, CONTAINERS_CONF,
# XDG_RUNTIME_DIR, REGISTRY_AUTH_FILE, and defines cleanup_podman_job.
#
# Extracted from run_harbor.sh so run_harbor.sh and submit_rerun_verifier.sh share
# one copy. Everything here is a workaround for a specific batch-node failure, and
# each one was found the hard way -- duplicating it would guarantee the two copies
# drift the next time podman surprises us.
#
# shellcheck shell=bash

if [ "$USE_PODMAN" = true ]; then
  export REGISTRY_AUTH_FILE="$HOME/.config/containers/auth.json"
  # On a batch node there is no systemd user session and no per-job container
  # state. Redirecting podman requires CONFIG FILES: CONTAINERS_RUNROOT and
  # CONTAINERS_GRAPHROOT are not env vars podman reads, and an explicit runroot
  # in ~/.config/containers/storage.conf overrides XDG_RUNTIME_DIR.
  # The split matters: runroot and tmp_dir are PER JOB, because a shared runroot
  # goes stale when the node reboots ("current system boot ID differs from cached
  # boot ID"); graphroot is shared per node so a second job on the same host
  # reuses cached layers instead of repeating the ~7 min image build.
  if [ -n "${LSB_JOBID:-}" ]; then
    PODMAN_JOB_DIR="/scratch/$USER/podman-$LSB_JOBID"
    PODMAN_GRAPHROOT="/scratch/$USER/podman-storage"

    # ---- NEW (1): do not let a failed mkdir become a podman error 13 s later ----
    if ! mkdir -p "$PODMAN_JOB_DIR/run" "$PODMAN_JOB_DIR/tmp" "$PODMAN_GRAPHROOT"; then
      echo "ERROR: cannot create podman dirs under /scratch/$USER on $(hostname)"
      ls -ld /scratch "/scratch/$USER" 2>&1
      exit 1
    fi
    # ---- end new (1) ----

    cat > "$PODMAN_JOB_DIR/storage.conf" <<EOF
[storage]
driver = "overlay"
runroot = "$PODMAN_JOB_DIR/run"
graphroot = "$PODMAN_GRAPHROOT"
[storage.options]
mount_program = "/usr/bin/fuse-overlayfs"
EOF
    cat > "$PODMAN_JOB_DIR/containers.conf" <<EOF
[engine]
# crun defaults to the systemd cgroup manager, which needs a D-Bus session bus.
# A batch node has none, so container creation dies with
# "sd-bus call: Interactive authentication required".
cgroup_manager = "cgroupfs"
tmp_dir = "$PODMAN_JOB_DIR/tmp"
EOF
    export CONTAINERS_STORAGE_CONF="$PODMAN_JOB_DIR/storage.conf"
    export CONTAINERS_CONF="$PODMAN_JOB_DIR/containers.conf"
    export XDG_RUNTIME_DIR="$PODMAN_JOB_DIR/run"
    echo "podman: host=$(hostname) runroot=$PODMAN_JOB_DIR/run graphroot=$PODMAN_GRAPHROOT"

    # Rootless podman leaves a `catatonit -P` pause process holding the user
    # namespace. It reparents to init and never exits, so LSF keeps the job in
    # RUN long after the work is done -- a whole node held until the wall clock
    # kills it. Kill it by the pid podman recorded, and only if that pid really
    # is catatonit, so a recycled pid can never be hit.
    cleanup_podman_job() {
      local pidfile pid
      for pidfile in "$PODMAN_JOB_DIR/tmp/pause.pid" \
                     "$PODMAN_JOB_DIR/run/libpod/tmp/pause.pid"; do
        [ -f "$pidfile" ] || continue
        pid=$(cat "$pidfile" 2>/dev/null)
        if [ -n "$pid" ] && [ "$(ps -p "$pid" -o comm= 2>/dev/null)" = "catatonit" ]; then
          echo "podman: stopping pause process $pid"
          kill "$pid" 2>/dev/null || true
        fi
      done
      rm -rf "$PODMAN_JOB_DIR"
    }
    trap cleanup_podman_job EXIT

    # ---- NEW (2): prove podman works, and repair it, before harbor starts ----
    # Once harbor is running, a broken podman becomes a per-trial exception and the
    # job still exits 0, so LSF records DONE, frees the node, and hands it the next
    # pending job to kill. Probing here turns that into a job that EXITs, and gives
    # the repair a chance first.
    #
    # Escalate in the order that costs least:
    #   a. podman system migrate      -- rebuilds the userns state; podman's own advice
    #   b. kill leftover catatonit    -- a pause process from a job that died without
    #                                    running its cleanup trap holds the old userns
    #   c. reset the shared graphroot -- the only other state carried between jobs;
    #                                    costs a ~7 min image rebuild
    # Anything printed here is the diagnosis for the next occurrence: today's logs
    # contain only podman's misleading message, which is why three hosts' worth of
    # failures took an hour to attribute.
    podman_healthy() { podman info >/dev/null 2>&1; }

    if ! podman_healthy; then
      echo "WARNING: podman unhealthy on $(hostname) before any work -- attempting repair"
      podman info 2>&1 | tail -5
      pgrep -u "$USER" -a catatonit 2>/dev/null | sed 's/^/  stale: /'

      podman system migrate >/dev/null 2>&1 || true
      if ! podman_healthy; then
        pkill -u "$USER" -x catatonit 2>/dev/null || true
        podman system migrate >/dev/null 2>&1 || true
      fi
      if ! podman_healthy; then
        # The graphroot is the only state carried between jobs on a node, and on
        # 2026-07-28 wiping it was the ONLY step that ever repaired a poisoned host
        # -- migrate and killing catatonit both failed first. Confirmed on h06u10.
        #
        # Remove it from inside the user namespace. Image layers under overlay/*/diff
        # are owned by subuid-mapped UIDs, so a plain `rm -rf` as the invoking user
        # gets "Permission denied" on most of the tree and leaves debris behind (it
        # removed just enough to let podman re-init, which is luck, not a fix).
        # `podman unshare` enters the same mapping that created those files.
        echo "podman: resetting shared image store $PODMAN_GRAPHROOT"
        podman unshare rm -rf "$PODMAN_GRAPHROOT" 2>/dev/null \
          || rm -rf "$PODMAN_GRAPHROOT" 2>/dev/null \
          || true
        # Anything left is subuid-owned debris a later job cannot read either;
        # move it aside so the fresh store starts clean. /scratch is node-local
        # and wiped between allocations, so the leftovers cost nothing.
        if [ -d "$PODMAN_GRAPHROOT" ] && [ -n "$(ls -A "$PODMAN_GRAPHROOT" 2>/dev/null)" ]; then
          mv "$PODMAN_GRAPHROOT" "$PODMAN_GRAPHROOT.broken-$LSB_JOBID" 2>/dev/null || true
          echo "podman: could not fully remove the old store; moved it aside"
        fi
        mkdir -p "$PODMAN_GRAPHROOT"
      fi
      if ! podman_healthy; then
        echo "ERROR: podman unusable on $(hostname); refusing the job so LSF marks it EXIT"
        podman info 2>&1 | tail -20
        exit 1
      fi
      echo "podman: recovered on $(hostname)"
    fi
    # ---- end new (2) ----
  fi
fi
