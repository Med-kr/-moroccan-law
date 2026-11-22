#!/usr/bin/env bash
# Install the Moroccan-law skills for Claude Code.
#
#   ./install.sh                 install every skill into ~/.claude/skills
#   ./install.sh maroc-travail   install only the named skill(s)
#   ./install.sh --project       install into ./.claude/skills of the current directory
#   ./install.sh --list          list available skills
#   ./install.sh --dry-run       show what would be copied
#   ./install.sh --force         replace skills that are already installed
set -euo pipefail

src="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/skills"
dest="${HOME}/.claude/skills"
dry=0; force=0; names=()

for arg in "$@"; do
  case "$arg" in
    --project) dest="$(pwd)/.claude/skills" ;;
    --dry-run) dry=1 ;;
    --force)   force=1 ;;
    --list)    for d in "$src"/*/; do printf '%s\n' "$(basename "$d")"; done; exit 0 ;;
    -h|--help) sed -n '2,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    -*)        echo "unknown option: $arg" >&2; exit 2 ;;
    *)         names+=("$arg") ;;
  esac
done

if [ ${#names[@]} -eq 0 ]; then
  for d in "$src"/*/; do names+=("$(basename "$d")"); done
fi

status=0
for name in "${names[@]}"; do
  if [ ! -f "$src/$name/SKILL.md" ]; then
    echo "!! no such skill: $name (see --list)" >&2; status=1; continue
  fi
  target="$dest/$name"
  if [ -e "$target" ] && [ "$force" -ne 1 ]; then
    echo "-- $name is already installed in $dest (use --force to replace it)"; continue
  fi
  if [ "$dry" -eq 1 ]; then
    echo "would install $name -> $target"; continue
  fi
  mkdir -p "$dest"
  rm -rf "$target"
  cp -R "$src/$name" "$target"
  echo "installed $name -> $target"
done
exit $status
