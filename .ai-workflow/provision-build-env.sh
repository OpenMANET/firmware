#!/usr/bin/env bash
# OpenMANET Pi5 port - provision the WSL Ubuntu 24.04 build distro.
# Run as root inside the 'openmanet-build' distro. Idempotent.
set -euo pipefail

log() { printf '\n\033[36m[provision] %s\033[0m\n' "$*"; }

WIN_REPO=/mnt/c/AI-Projects/OpenMANET-Pi5/firmware
BUILD_USER=builder
BUILD_HOME=/home/$BUILD_USER
BUILD_TREE=$BUILD_HOME/openmanet/firmware
BRANCH=pi5-wm6108-port

# --- wsl.conf ---------------------------------------------------------------
# systemd is not required for a build box, but we do want sane interop and
# for the default user to be 'builder'.
log 'Writing /etc/wsl.conf'
cat > /etc/wsl.conf <<'EOF'
[boot]
systemd=false

[user]
default=builder

[interop]
enabled=true
appendWindowsPath=false

[automount]
enabled=true
options="metadata"
EOF

# --- APT --------------------------------------------------------------------
export DEBIAN_FRONTEND=noninteractive
log 'apt update'
apt-get update -qq

log 'Installing OpenWrt 24.10 build dependencies'
# This is the OpenWrt-documented Debian/Ubuntu prerequisite set, plus the
# extras this tree needs (mtools/dosfstools for the RPi FAT boot partition,
# device-tree-compiler, qemu-user-static is NOT needed).
apt-get install -y -qq --no-install-recommends \
    build-essential clang flex bison g++ gawk gcc-multilib g++-multilib \
    gettext git libncurses-dev libssl-dev python3-setuptools python3-distutils-extra \
    rsync unzip zlib1g-dev file wget time \
    ca-certificates curl ccache ecj fastjar java-propose-classpath \
    libelf-dev libglib2.0-dev libpython3-dev lib32gcc-s1 libc6-dev-i386 \
    subversion swig xsltproc zlib1g-dev \
    python3 python3-pip python3-ply \
    mtools dosfstools device-tree-compiler \
    quilt patch diffutils bzip2 xz-utils zstd \
    npm node-typescript \
    procps sudo less nano vim-tiny \
    libnl-3-dev libnl-genl-3-dev libgps-dev libcap-dev pkg-config \
    libopus-dev libopusfile-dev portaudio19-dev net-tools \
    libpcre3-dev libpcre3 upx-ucl golang-go \
  || { log 'Full package set failed; retrying without optional extras'; \
       apt-get install -y -qq --no-install-recommends \
         build-essential clang flex bison g++ gawk gettext git libncurses-dev \
         libssl-dev rsync unzip zlib1g-dev file wget time python3 python3-setuptools \
         ccache libelf-dev mtools dosfstools device-tree-compiler quilt patch \
         bzip2 xz-utils zstd procps sudo; }

log 'Installed toolchain versions:'
gcc --version | head -1
make --version | head -1
python3 --version
git --version

# --- build user -------------------------------------------------------------
# OpenWrt refuses to build as root.
if ! id -u "$BUILD_USER" >/dev/null 2>&1; then
    log "Creating user $BUILD_USER"
    useradd -m -s /bin/bash "$BUILD_USER"
    usermod -aG sudo "$BUILD_USER"
    echo "$BUILD_USER ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/90-builder
    chmod 0440 /etc/sudoers.d/90-builder
else
    log "User $BUILD_USER already exists"
fi

# --- git identity + safe.directory -----------------------------------------
log 'Configuring git'
sudo -u "$BUILD_USER" git config --global user.name  "OpenMANET Pi5 Build"
sudo -u "$BUILD_USER" git config --global user.email "matthew.garcia@patriotscraft.com"
sudo -u "$BUILD_USER" git config --global --add safe.directory "$WIN_REPO"
sudo -u "$BUILD_USER" git config --global --add safe.directory '*'
sudo -u "$BUILD_USER" git config --global core.symlinks true

# openmanetd declares its submodules with scp-style SSH URLs
# (git@github.com:OpenMANET/go-alfred.git). Without a rewrite the submodule
# clone blocks forever on an SSH credential prompt and the build simply hangs -
# it does not fail. Mirrors .github/workflows/build-firmware.yml:82-85.
sudo -u "$BUILD_USER" git config --global --unset-all url."https://github.com/".insteadOf || true
sudo -u "$BUILD_USER" git config --global --add url."https://github.com/".insteadOf "git@github.com:"
sudo -u "$BUILD_USER" git config --global --add url."https://github.com/".insteadOf "ssh://git@github.com/"
sudo -u "$BUILD_USER" git config --global --add url."https://github.com/".insteadOf "git://github.com/"

# Belt and braces: never let a build block on an interactive prompt.
grep -q GIT_TERMINAL_PROMPT "$BUILD_HOME/.bashrc" || sudo -u "$BUILD_USER" tee -a "$BUILD_HOME/.bashrc" >/dev/null <<'RC'

# Never block a build on an interactive git credential prompt.
export GIT_TERMINAL_PROMPT=0
export GIT_SSH_COMMAND="ssh -o BatchMode=yes -o StrictHostKeyChecking=no"
RC

# --- build tree -------------------------------------------------------------
# DESIGN NOTE (see CLAUDE.md "Build Rules"):
#   The Windows repo at C:\AI-Projects\OpenMANET-Pi5\firmware is the SINGLE
#   AUTHORITATIVE source tree. All edits and all commits happen there.
#   This WSL tree is a BUILD MIRROR only: it is a git clone whose 'winrepo'
#   remote points back at the Windows repo. We build here because OpenWrt
#   needs a case-sensitive filesystem, working symlinks (the Windows checkout
#   has core.symlinks=false, so boards/*/spi_diffconfig et al are plain text
#   files there) and ext4 speed. Never commit from this tree.
if [ ! -d "$BUILD_TREE/.git" ]; then
    log "Cloning authoritative Windows repo into $BUILD_TREE"
    sudo -u "$BUILD_USER" mkdir -p "$BUILD_HOME/openmanet"
    sudo -u "$BUILD_USER" git clone --origin winrepo --branch "$BRANCH" \
        "file://$WIN_REPO" "$BUILD_TREE"
else
    log "Build tree already present at $BUILD_TREE - fetching latest"
    sudo -u "$BUILD_USER" git -C "$BUILD_TREE" fetch winrepo
fi

sudo -u "$BUILD_USER" git -C "$BUILD_TREE" status --short --branch | head -5

# --- ccache -----------------------------------------------------------------
sudo -u "$BUILD_USER" bash -c 'ccache --max-size=20G >/dev/null 2>&1 || true'

# --- convenience helper -----------------------------------------------------
cat > "$BUILD_HOME/sync-from-windows.sh" <<'EOF'
#!/usr/bin/env bash
# Pull the latest committed state from the authoritative Windows repo into
# this build mirror. Uncommitted Windows changes are NOT picked up - commit
# them on the Windows side first (or use rsync-from-windows.sh).
set -euo pipefail
cd ~/openmanet/firmware
git fetch winrepo
git reset --hard "winrepo/$(git rev-parse --abbrev-ref HEAD)"
git status --short --branch
EOF

cat > "$BUILD_HOME/rsync-from-windows.sh" <<'EOF'
#!/usr/bin/env bash
# Mirror the Windows working tree (INCLUDING uncommitted edits) into the build
# mirror without touching build_dir/staging_dir/dl/.git. Use during rapid
# edit-build-fix cycles; the Windows tree stays authoritative.
set -euo pipefail
rsync -a --delete \
  --exclude '.git/' \
  --exclude 'build_dir/' --exclude 'staging_dir/' --exclude 'dl/' \
  --exclude 'bin/' --exclude 'tmp/' --exclude 'feeds/' \
  --exclude '.config' --exclude '.config.old' \
  /mnt/c/AI-Projects/OpenMANET-Pi5/firmware/ ~/openmanet/firmware/
echo "rsync complete"
EOF

chmod +x "$BUILD_HOME/sync-from-windows.sh" "$BUILD_HOME/rsync-from-windows.sh"
chown "$BUILD_USER:$BUILD_USER" "$BUILD_HOME/sync-from-windows.sh" "$BUILD_HOME/rsync-from-windows.sh"

log 'Provisioning complete.'
log "Build tree: $BUILD_TREE"
