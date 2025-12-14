#!/bin/bash
#
#

set -ue -o pipefail

error_handler() {
    2>&1 echo "SETUP FAILED: error $? on line ${BASH_LINENO[0]} from: ${BASH_COMMAND}"
}

trap error_handler ERR

usage(){
    cat << EOF

This OpenMANET script provides help automating the initialization of OpenWRT build.
Make sure you run this script from the top directory of OpenWRT!

Usage:
    ${0} <options>
        options:
            -i                      initializes openwrt by updating/installing feeds

            -b <board>              assembles config based on diffconfigs in target board folder.

            -m                      minimal diffconfig. Includes only target_diffconfig when selecting
                                    files from the board config. Often combined with '-x'
                                    for custom configurations.

            -x                      apply extra diffconfig options in common_extra. One of these is
                                    'dev' (no minification, use local git-src if linked, etc.).

            -g                      Override the source of a package to use a git-src tree.
                                    Format is <PKG_NAME>:<git path>. (-g morse_driver:../morse_driver/)
                                    Can be specified multiple times.

            -l <target>             loads selected target defconfig [deprecated]

            -s <target>             saves your current menuconfig from .config to a defconfig.
                                    (this option overwrites pre-existing files!) [deprecated]

            -e <toolchain_path>     use the toolchain specified at <toolchain_path>

            -E                      identifies the architecture of the selected board, and
                                    downloads a toolchain from the configured VERSION_REPO.
                                    By default, the toolchain will be extracted to /opt
                                    unless -e specifies an alternative toolchain path.

        eg.:
            ${0} -i -b ekh03v3
            ${0} -m -x dev -b ekh01

EOF
    echo -e "Available extra (-x) options:\n"
    ls -1 boards/common_extras | sed 's/\(.*\)_diffconfig/  \1/'
    echo
    echo -e "Available board (-b) options (can use build name or individual targets):\n"
    for b in boards/*; do
        if [ -e "$b/target_diffconfig" ]; then
            echo "  $(basename $b)"
            sed -n 's/CONFIG_TARGET_.*_DEVICE_\(.*\)_\(.*\)=y/    \2 (\1 \2)/p' $b/target_diffconfig
            echo
        fi
    done
exit "${1}"
}

download_toolchain(){
    INSTALL_PATH="${1:-}"
    mkdir -p tmp
    mkdir -p tmp/dl
    gcc_vers="$(sed -nE 's/^CONFIG_GCC_VERSION=\"([^\"]+)\"/\1/p' .config)"
    arch="$(sed -nE 's/^CONFIG_ARCH=\"([^\"]+)\"/\1/p' .config)"
    cpu_type="$(sed -nE 's/^CONFIG_CPU_TYPE=\"([^\"]+)\"/\1/p' .config)"
    if [ -n "$cpu_type" ]; then
        arch_suffix="_${cpu_type}"
    fi
    libc="$(sed -nE 's/^CONFIG_LIBC=\"([^\"]+)\"/\1/p' .config)"
    base_url="$(sed -nE 's/^CONFIG_VERSION_REPO=\"([^\"]+)\"/\1/p' .config)"
    vers=${base_url%%/}
    vers=${vers##http*/}
    libc_suffix=
    if grep -q '^CONFIG_arm=y' .config; then
        libc_suffix=_eabi
    fi
    toolchain_archive="openwrt-toolchain-${vers}-${target}-${subtarget}_gcc-${gcc_vers}_${libc}${libc_suffix}.Linux-x86_64"

    if [ -n "${INSTALL_PATH}" ]; then
        [ ! -d "${INSTALL_PATH}" ] && mkdir -p "${INSTALL_PATH}"
        TAR_STRIP="--strip-components=2"
        SUB_FOLDER="${toolchain_archive}/toolchain-${arch}${arch_suffix}_gcc-${gcc_vers}_${libc}${libc_suffix}"
        TOOLCHAIN_PATH=${INSTALL_PATH}
    else
        INSTALL_PATH="/opt"
        TOOLCHAIN_PATH="/opt/${toolchain_archive}/toolchain-${arch}${arch_suffix}_gcc-${gcc_vers}_${libc}${libc_suffix}"
        SUB_FOLDER=""
        TAR_STRIP=""
    fi

    echo "Toolchain will be installed into ${TOOLCHAIN_PATH}"

    if [ ! -d "${TOOLCHAIN_PATH}/bin" ]; then
        SUDO=''
        if [ ! -w "${INSTALL_PATH}" ]; then
            SUDO="sudo"
        fi

        if [ ! -f "tmp/dl/${toolchain_archive}.tar.xz" ]; then
            wget -P tmp/dl "${base_url}/targets/${target}/${subtarget}/${toolchain_archive}.tar.xz"
        fi

        $SUDO tar -xf "tmp/dl/${toolchain_archive}.tar.xz" -C ${INSTALL_PATH} ${SUB_FOLDER} ${TAR_STRIP}

        if [ -n "$SUDO" ]; then
                $SUDO chown -R "$USER:$(id -g)" "${TOOLCHAIN_PATH}"
        fi

        echo "${toolchain_archive}.tar.xz extracted to ${TOOLCHAIN_PATH}"
    else
        echo "${TOOLCHAIN_PATH} already contains a toolchain!"
    fi
}

patch_feeds_packages(){
    local BOARD_ARG="${1:-}"

    if [ -z "$BOARD_ARG" ]; then
        echo "No board specified, skipping patches."
        return 0
    fi

    PATCHES_DIR="patches/${BOARD_ARG}"

    # Check if the board-specific patches directory exists
    if [ ! -d "$PATCHES_DIR" ]; then
        echo "No patches directory found for board '$BOARD_ARG' at '$PATCHES_DIR', skipping patches."
        return 0
    fi

    echo "Applying patches from: $PATCHES_DIR"

    # Iterate over all patch files in the board-specific patches directory
    for patch_file in "$PATCHES_DIR"/*.patch; do
        if [ -e "$patch_file" ]; then
            echo "Applying patch: $patch_file"
            if patch -N -p1 < "$patch_file"; then
                echo "Patch applied successfully."
            fi
        fi
    done

    echo "All patches applied successfully."
}



# script has to run from openwrt top
if [[ "$(pwd)" != "$(git rev-parse --show-toplevel)" ]]; then
    usage 1
fi

MINIMAL=
INITIALIZE=
EXTRAS=
EXT_TOOLCHAIN=
GIT_SRC_OVERRIDES=( )
MODE=""
while getopts ":l:s:b:x:g:ie:Emh" OPT; do
    case "${OPT}" in
        b)
            MODE=${OPT}
            BOARD="${OPTARG}"
            ;;
        e)
            EXT_TOOLCHAIN=1
            TOOLCHAIN_PATH="${OPTARG}"
            ;;
        E)
            EXT_TOOLCHAIN=1
            DOWNLOAD_TOOLCHAIN=1
            ;;
        l|s)
            MODE="${OPT}"
            TARGET_DEFCONFIG="${OPTARG}"
            ;;
        i)
            INITIALIZE=1
            ;;
        m)
            MINIMAL=1
            ;;
        x)
            EXTRAS="$EXTRAS $OPTARG"
            ;;
        g)
            GIT_SRC_OVERRIDES+=( "$OPTARG" )
            ;;
        h)
            usage 0
            ;;
        *)
            usage 1
            ;;
    esac
done
shift $((OPTIND-1))

# gotta have a target if saving/loading
if [ "${MODE}" ] &&  [ -z "${TARGET_DEFCONFIG+x}" ] && [ -z "${BOARD+x}" ]; then
    usage 1
fi

if [ -z "$MODE" ] && [ -z "$INITIALIZE" ]; then
    usage 1
fi

if [ "${INITIALIZE}" ]; then
    ./scripts/feeds update -a
    #patch packages if necessary and re-create index files
    patch_feeds_packages "${BOARD:-}"
    ./scripts/feeds update -i
    ./scripts/feeds install -p openmanet -a
    ./scripts/feeds install -a

    ./scripts/feeds install -f -p morse iwinfo
fi

case "${MODE}" in
    b)
        if [ ! -d "boards/${BOARD}" ]; then
            FOUND_MULTIPROFILE_TARGET=0
            for b in boards/*; do
                if [ -e "$b/target_diffconfig" ]; then
                    if sed -n 's/CONFIG_TARGET_DEVICE_.*_DEVICE_.*_\(.*\)=y/\1/p' $b/target_diffconfig | grep -qxF "$BOARD"; then
                        b="$(basename "$b")"
                        echo "No boards/$BOARD, but '$BOARD' will be built by boards/$b"
                        FOUND_MULTIPROFILE_TARGET=1
                        BOARD="$b"
                    fi
                fi
            done
            if [ "$FOUND_MULTIPROFILE_TARGET" = 0 ]; then
                echo "Error: No ${BOARD} board"
                usage 1
            fi
        fi

        echo "Using ${BOARD}"

        if [ "${BOARD}" = "common" ] || [ "${BOARD}" = "common_extras" ]; then
            echo "${BOARD} is not a board!"
            usage 1
        fi

        for file in ./boards/"${BOARD}"/*_diffconfig; do
            if ! [ "$(basename "$file")" = target_diffconfig ]; then
                if ! [ -h "$file" ]; then
                    echo "${file} is not a symlink; aborting."
                    usage 1
                fi
            fi
        done

        # awk 1 is a line by line print from stdin - 1 is an always true command
        # and the default action is to print line.
        # I've opted for this instead of cat + echo as I didn't want to unroll globs
        awk 1 ./boards/common/*_diffconfig > .config
        if [ "${MINIMAL}" = 1 ]; then
            awk 1 ./boards/"${BOARD}"/target_diffconfig >> .config
        else
            awk 1 ./boards/"${BOARD}"/*_diffconfig >> .config
        fi

        for extra in $EXTRAS; do
            echo "Applying $extra config..."
            awk 1 "./boards/common_extras/${extra}_diffconfig" >> .config
        done

        # Remove and recreate symlinks for git-src overrides.
        # Only remove symlinks in git-src, so we dont destroy any user content.
        mkdir -p "./git-src/"
        find ./git-src/ -maxdepth 1 -type l -exec rm -v {} \;
        for git_src_override in "${GIT_SRC_OVERRIDES[@]}"; do
            package=$(echo "$git_src_override" | cut -f1 -d:)
            git_path=$(echo "$git_src_override" | cut -f2 -d:)
            ln -vfrs "$git_path" "git-src/$package"
        done

        echo Make defconfig...
        make defconfig

        if [ "${EXT_TOOLCHAIN}" = "1" ]; then
            read -r target subtarget <<<"$(sed -nE 's/^CONFIG_TARGET_([a-z0-9]+)_([a-z0-9]+)=y/\1 \2/p' "boards/${BOARD}/target_diffconfig")"
            if [ "${DOWNLOAD_TOOLCHAIN}" = "1" ]; then
                download_toolchain "${TOOLCHAIN_PATH:-}"
            fi

            echo "Adding external toolchain ${TOOLCHAIN_PATH}"
            ./scripts/ext-toolchain.sh --toolchain "${TOOLCHAIN_PATH}" \
                        --overwrite-config --config "${target}/${subtarget}"
        fi

        ;;
    s)
        ./scripts/diffconfig.sh > "${TARGET_DEFCONFIG}"
        ;;
    l)
        echo "Using legacy load of defconfig!"
        if [ -f "${TARGET_DEFCONFIG}" ]; then
            cp "${TARGET_DEFCONFIG}" .config
        else
            echo "Selected target defconfig was not found!" 1>&2
            exit 2
        fi
        make defconfig
        ;;
esac
