# Sieve Rule Decision Matrix

This note documents how the bot should behave when a new Telegram request overlaps with existing Sieve rules.

## Address requests

- Same email, same folder: return `duplicate`.
- Different email, same domain, same folder: extend the existing rule by adding the new email into the same `if address :contains ...` block.
- Different email, different domain, same folder: keep as a separate rule for now.
- Same email or same domain, different folder: return `conflict`.
- Address request covered by an existing domain-wide rule for the same folder: return `duplicate`.

## Domain-wide requests

- Same domain, same folder, existing domain-wide rule: return `duplicate`.
- Same domain, different folder: return `conflict`.
- Same domain, same folder, but the folder already has address-specific rules from that domain: return `conflict` instead of silently broadening the match scope.

## Notes

- The current implementation is intentionally conservative when the same domain points to different folders.
- If we later decide that "different domain, same folder" should also merge into one block, that can be added as a separate rule-normalization step.
