.PHONY: build
default: build

EXCLUDE_PATTERNS := $(shell awk '/^\s*$$/ || /^\s*\#/{next} {sub(/^\//, ""); if (/\/$$/){sub(/\/$$/, "/*"); printf "\047%s\047 ", $$0} else if (/\*/){printf "\047%s\047 ", $$0} else {printf "\047%s\047 \047%s/*\047 ", $$0, $$0}}' .gitignore)

build:
	mkdir -p build
	zip -r build/growth-$(shell date +%Y-%m-%d).zip . -x '.git/*' $(EXCLUDE_PATTERNS)