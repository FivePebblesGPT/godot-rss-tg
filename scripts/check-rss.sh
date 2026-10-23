#!/usr/bin/env bash
# Fetch the feed cheaply on the host, starting Docker only when its contents change.
set -euo pipefail

script_path="$(readlink -f -- "${BASH_SOURCE[0]}")"
repo_root="$(cd -- "$(dirname -- "$script_path")/.." && pwd -P)"
state_dir="${XDG_STATE_HOME:-${HOME}/.local/state}/godot-rss-tg"
feed_url="${RSS_URL:-https://godotengine.org/rss.xml}"
force=false

case "${1:-}" in
  "") ;;
  --force) force=true ;;
  *) printf 'Usage: %s [--force]\n' "$0" >&2; exit 2 ;;
esac

mkdir -p -- "$state_dir"
# Protect local state from concurrent timers or manual invocations.
exec 9>"$state_dir/check.lock"
if ! flock -n 9; then
  printf 'Another RSS check is already running; skipping.\n'
  exit 0
fi

feed_file="$(mktemp -- "$state_dir/feed.XXXXXXXX")"
digest_tmp="$(mktemp -- "$state_dir/digest.XXXXXXXX")"
trap 'rm -f -- "$feed_file" "$digest_tmp"' EXIT

curl --fail --silent --show-error --location \
  --connect-timeout 10 --max-time 30 --retry 2 \
  --output "$feed_file" -- "$feed_url"

if [[ ! -s "$feed_file" ]]; then
  printf 'RSS response is empty; leaving state unchanged.\n' >&2
  exit 1
fi

digest="$(sha256sum -- "$feed_file")"
digest="${digest%% *}"
digest_file="$state_dir/last-successful-sha256"

if [[ "$force" == false && -r "$digest_file" && "$(cat -- "$digest_file")" == "$digest" ]]; then
  printf 'RSS unchanged; Docker not started.\n'
  exit 0
fi

printf 'RSS changed; running the one-shot bot...\n'
# A failed send/check leaves the previous fingerprint intact for retry.
docker compose --project-directory "$repo_root" --file "$repo_root/compose.yml" \
  run --rm --no-deps -T -e "RSS_URL=$feed_url" bot

printf '%s\n' "$digest" >"$digest_tmp"
mv -f -- "$digest_tmp" "$digest_file"
printf 'Bot finished successfully; RSS fingerprint saved.\n