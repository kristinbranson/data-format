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
  #
  # PODMAN_PRIVATE_STORAGE=true gives the job its own graphroot as well. Set it when
  # SEVERAL JOBS MAY SHARE A NODE. The shared store is only safe for one job at a
  # time. Whole-node sweeps (submit_harbor_cluster.py, run_harbor.sh) cannot hit this 
  # and should leave it unset, so they keep the warm store. The cost when set is one 
  # image build per job instead of one per node, which is free when the jobs run in parallel 
  # anyway.
  if [ -n "${LSB_JOBID:-}" ]; then
    PODMAN_JOB_DIR="/scratch/$USER/podman-$LSB_JOBID"
    if [ "${PODMAN_PRIVATE_STORAGE:-false}" = true ]; then
      PODMAN_GRAPHROOT="$PODMAN_JOB_DIR/storage"
    else
      PODMAN_GRAPHROOT="/scratch/$USER/podman-storage"
    fi

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
      # Remove this job's containers FIRST, while storage.conf still exists. The rm -rf
      # at the end of this function destroys the configuration podman needs to address
      # them, so a container that outlives harbor's own teardown becomes unreachable:
      #   Failed to obtain podman configuration: stat .../storage.conf: no such file
      # while its conmon/sh/sleep keep running and LSF holds the job in RUN until the
      # wall clock. 
      #
      # Scoped by this job's runroot -- container state lives there, and the runroot is
      # per job -- so a sibling job on the same node is not touched.
      #
      # --time 10 because harbor runs the main service as `sleep infinity`, which
      # ignores SIGTERM: podman waits the full timeout before sending SIGKILL.
      podman rm -f --all --time 10 >/dev/null 2>&1 || true

      for pidfile in "$PODMAN_JOB_DIR/tmp/pause.pid" \
                     "$PODMAN_JOB_DIR/run/libpod/tmp/pause.pid"; do
        [ -f "$pidfile" ] || continue
        pid=$(cat "$pidfile" 2>/dev/null)
        if [ -n "$pid" ] && [ "$(ps -p "$pid" -o comm= 2>/dev/null)" = "catatonit" ]; then
          echo "podman: stopping pause process $pid"
          kill "$pid" 2>/dev/null || true
        fi
      done
      # Plain rm, and nothing that runs podman, because this is AFTER the pause process
      # was killed above. Any podman command here starts a replacement pause process to
      # re-enter the user namespace, and that one has no pidfile left to find it by, so
      # it survives and holds the job in RUN until the wall clock.
      #
      # A private graphroot's image layers under overlay/*/diff are owned by
      # subuid-mapped UIDs, so this leaves some of them behind. That costs nothing:
      # /scratch is node-local and cleared when the allocation ends.
      rm -rf "$PODMAN_JOB_DIR" 2>/dev/null || true
    }
    trap cleanup_podman_job EXIT

    # `podman system migrate` is podman's own fix for the stale boot-ID state that the 
    # per-job runroot above also avoids, and it costs nothing when there is nothing to 
    # migrate. The health check below only catches a store that is already broken at 
    # startup; today's corruption happened mid-build, after that check had passed.
    podman system migrate 2>/dev/null || true

    # ---- NEW (2): prove podman works, and repair it, before harbor starts ----
    # Once harbor is running, a broken podman becomes a per-trial exception and the
    # job still exits 0, so LSF records DONE, frees the node, and hands it the next
    # pending job to kill. Probing here turns that into a job that EXITs, and gives
    # the repair a chance first.
    #
    # Escalate in the order that costs least:
    #   a. podman system migrate    -- rebuilds the userns state; podman's own advice
    #   b. reset the graphroot      -- the only other state carried between jobs; costs
    #                                  a ~7 min image rebuild, and ONLY when this job
    #                                  owns the store (see the check below)
    #   c. refuse the job           -- rather than guess at state that may belong to a
    #                                  sibling job on the same host
    # Anything printed here is the diagnosis for the next occurrence: today's logs
    # contain only podman's misleading message, which is why three hosts' worth of
    # failures took an hour to attribute.
    podman_healthy() { podman info >/dev/null 2>&1; }

    if ! podman_healthy; then
      echo "WARNING: podman unhealthy on $(hostname) before any work -- attempting repair"
      podman info 2>&1 | tail -5
      # pause processes on this host, for the diagnosis. Any of them may belong to
      # a sibling job that is running normally, so this only looks.
      pgrep -u "$USER" -a catatonit 2>/dev/null | sed 's/^/  pause process: /'

      podman system migrate >/dev/null 2>&1 || true
      if ! podman_healthy; then
        # Reset the store ONLY when this job owns it. A shared graphroot can be in use
        # by another job on the same node, and wiping it pulls the image store out from
        # under that job's running container: podman then has no record of the container,
        # so `compose down` removes nothing and still exits 0, while the container's
        # processes survive and hold the node until the wall clock.
        #
        # PODMAN_PRIVATE_STORAGE=true puts the graphroot inside PODMAN_JOB_DIR, after
        # which this repair can only destroy the job's own store. Set it whenever
        # several jobs may share a node.
        if [ "${PODMAN_GRAPHROOT#$PODMAN_JOB_DIR}" = "$PODMAN_GRAPHROOT" ]; then
          echo "ERROR: podman is unhealthy on $(hostname) and the image store"
          echo "       $PODMAN_GRAPHROOT is shared with any sibling job on this node."
          echo "       Refusing to reset it. Rerun with PODMAN_PRIVATE_STORAGE=true,"
          echo "       or clear it by hand when no other job is running on this host."
          exit 1
        fi
        # The graphroot is the only state carried between jobs on a node, so wiping it
        # is the last repair available when `podman system migrate` does not help.
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
