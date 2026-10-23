#!/usr/bin/env bash
# Offline integration test: replace curl and docker with local fakes.
set -euo pipefail

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
work="$(mktemp -d)"
trap 'rm -rf -- "$work"' EXIT
mkdir -p -- "$work/repo/scripts" "$work/bin" "$work/state"
cp -- "$repo_root/scripts/check-rss.sh" "$work/repo/scripts/check-rss.sh"
printf 'services:\n  bot: {}\n' > "$work/repo/compose.yml"
printf '<rss><item><link>https://godotengine.org/a</link></item></rss>\n' > "$work/feed.xml"

cat > "$work/bin/curl" <<'MOCK_CURL'
#!/usr/bin/env bash
while (($#)); do
  if [[ "$1" == --output ]]; then shift; output="$1"; fi
  shift
done
cp -- "$MOCK_FEED" "$output"
MOCK_CURL

cat > "$work/bin/docker" <<'MOCK_DOCKER'
#!/usr/bin/env bash
printf 'started\n' >> "$MOCK_DOCKER_LOG"
[[ ! -e "$MOCK_DOCKER_FAIL" ]]
MOCK_DOCKER
chmod +x "$work/bin/curl" "$work/bin/docker"

export MOCK_FEED="$work/feed.xml"
export MOCK_DOCKER_LOG="$work/docker.log"
export MOCK_DOCKER_FAIL="$work/fail"
export XDG_STATE_HOME="$work/state"
export PATH="$work/bin:$PATH"

bash "$work/repo/scripts/check-rss.sh"  # First run starts the container.
bash "$work/repo/scripts/check-rss.sh"  # Unchanged: no container.
[[ "$(wc -l < "$MOCK_DOCKER_LOG")" -eq 1 ]]

printf '<rss><item><link>https://godotengine.org/b</link></item></rss>\n' > "$MOCK_FEED"
bash "$work/repo/scripts/check-rss.sh"
[[ "$(wc -l < "$MOCK_DOCKER_LOG")" -eq 2 ]]

printf '<rss><item><link>https://godotengine.org/c</link></item></rss>\n' > "$MOCK_FEED"
touch "$MOCK_DOCKER_FAIL"
if bash "$work/repo/scripts/check-rss.sh"; then
  printf 'Bot failure unexpectedly succeeded\n' >&2
  exit 1
fi
rm -f -- "$MOCK_DOCKER_FAIL"
bash "$work/repo/scripts/check-rss.sh"  # Must retry the failed fingerprint.
[[ "$(wc -l < "$MOCK_DOCKER_LOG")" -eq 4 ]]

bash "$work/repo/scripts/check-rss.sh" --force
[[ "$(wc -l < "$MOCK_DOCKER_LOG")" -eq 5 ]]
printf 'check-rss.sh tests passed\n