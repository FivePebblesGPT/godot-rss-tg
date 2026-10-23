#!/usr/bin/env bash
# Install a user timer that survives moving between shell sessions.
set -euo pipefail

script_path="$(readlink -f -- "${BASH_SOURCE[0]}")"
repo_root="$(cd -- "$(dirname -- "$script_path")/.." && pwd -P)"
unit_dir="${XDG_CONFIG_HOME:-${HOME}/.config}/systemd/user"
launcher_dir="${HOME}/.local/bin"

mkdir -p -- "$unit_dir" "$launcher_dir"
ln -sfn -- "$repo_root/scripts/check-rss.sh" "$launcher_dir/godot-rss-tg-check"
install -m 0644 "$repo_root/systemd/godot-rss-tg.service" "$unit_dir/godot-rss-tg.service"
install -m 0644 "$repo_root/systemd/godot-rss-tg.timer" "$unit_dir/godot-rss-tg.timer"
systemctl --user daemon-reload
systemctl --user enable --now godot-rss-tg.timer
systemctl --user list-timers godot-rss-tg.timer
