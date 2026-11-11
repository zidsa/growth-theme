.PHONY: build
default: build

# Agent skills and instructions are not theme files (the skills folders are symlinks: zip would copy them 5x).
AGENT_PATTERNS := '.agents/*' '.claude/*' '.codex/*' '.cursor/*' '.hermes/*' 'AGENTS.md' 'CLAUDE.md'
EXCLUDE_PATTERNS := $(shell awk '/^\s*$$/ || /^\s*\#/{next} {sub(/^\//, ""); if (/\/$$/){sub(/\/$$/, "/*"); printf "\047%s\047 ", $$0} else if (/\*/){printf "\047%s\047 ", $$0} else {printf "\047%s\047 \047%s/*\047 ", $$0, $$0}}' .gitignore)

build:
	mkdir -p build
	zip -r build/growth-$(shell date +%Y-%m-%d).zip . -x '.git/*' $(AGENT_PATTERNS) $(EXCLUDE_PATTERNS)