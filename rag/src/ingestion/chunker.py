"""Token windows using original text offsets, with E5 input length checks."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    text: str
    token_count: int
    input_token_count: int
    start: int
    end: int


class TokenChunker:
    def __init__(
        self, tokenizer, *, target: int = 480, minimum: int = 450, overlap: int = 80
    ):
        if not 0 <= overlap < minimum <= target <= 480:
            raise ValueError("Invalid chunk parameters")
        self.tokenizer = tokenizer
        self.target = target
        self.minimum = minimum
        self.overlap = overlap

    def split(self, text: str) -> list[Chunk]:
        if not text.strip():
            return []
        encoded = self.tokenizer(
            text,
            add_special_tokens=False,
            truncation=False,
            return_offsets_mapping=True,
            verbose=False,
        )
        offsets = encoded["offset_mapping"]
        if not offsets:
            return []
        chunks = []
        start = 0
        while start < len(offsets):
            end = min(start + self.target, len(offsets))
            while end > start:
                # Avoid splitting character spans shared by several tokens.
                if end < len(offsets) and offsets[end - 1][1] > offsets[end][0]:
                    end -= 1
                    continue
                part = text[offsets[start][0] : offsets[end - 1][1]].strip()
                count = len(
                    self.tokenizer.encode(
                        part, add_special_tokens=False, truncation=False, verbose=False
                    )
                )
                full = len(
                    self.tokenizer.encode(
                        "passage: " + part,
                        add_special_tokens=True,
                        truncation=False,
                        verbose=False,
                    )
                )
                next_start = end - self.overlap
                safe_overlap = (
                    end == len(offsets)
                    or next_start <= 0
                    or offsets[next_start - 1][1] <= offsets[next_start][0]
                )
                if part and count <= self.target and full <= 512 and safe_overlap:
                    break
                end -= 1
            else:
                raise ValueError("Unable to construct a safe token window")
            if end < len(offsets) and (
                count < self.minimum or end - start <= self.overlap
            ):
                raise ValueError("Non-final chunk outside approved size range")
            chunks.append(Chunk(part, count, full, start, end))
            if end == len(offsets):
                break
            next_start = end - self.overlap
            # If the exact overlap cuts a shared character, fail rather than silently alter it.
            if next_start > 0 and offsets[next_start - 1][1] > offsets[next_start][0]:
                raise ValueError("Overlap splits a character span")
            start = next_start
        return chunks
