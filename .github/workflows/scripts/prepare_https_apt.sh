#!/bin/sh
set -eu

# Hosted runners can have working HTTPS while the Azure HTTP mirror times out
# once per package. Cover both deb822/list sources and mirror+file mirror lists.
for source_file in /etc/apt/sources.list /etc/apt/sources.list.d/*.list \
                   /etc/apt/sources.list.d/*.sources /etc/apt/apt-mirrors*.txt; do
    [ -f "$source_file" ] || continue
    sudo sed -i \
        -e 's|http://azure.archive.ubuntu.com/ubuntu|https://archive.ubuntu.com/ubuntu|g' \
        -e 's|http://archive.ubuntu.com/ubuntu|https://archive.ubuntu.com/ubuntu|g' \
        -e 's|http://security.ubuntu.com/ubuntu|https://security.ubuntu.com/ubuntu|g' \
        "$source_file"
done
