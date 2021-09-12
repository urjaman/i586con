#!/bin/sh
echo "$(cat br-version)-$(git log -1 --pretty=format:%cs)-$(git rev-parse --short=8 HEAD)"
