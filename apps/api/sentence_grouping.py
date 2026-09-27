from dataclasses import dataclass

from jmdict_exact_repository import ExactCandidate
from sentence_service import ResolvedToken


@dataclass(frozen=True)
class SentenceGroup:
    surface: str
    start: int
    end: int
    tokens: tuple[ResolvedToken, ...]

    @property
    def candidates(self) -> tuple[ExactCandidate, ...]:
        return self.tokens[0].candidates


def token_category(item: ResolvedToken) -> str:
    parts = item.token.part_of_speech
    return parts[0] if parts else ""


def group_sentence(
    text: str,
    resolved: tuple[ResolvedToken, ...],
) -> tuple[SentenceGroup, ...]:
    groups = []
    index = 0

    while index < len(resolved):
        first = resolved[index]
        members = [first]
        index += 1

        if token_category(first) in {"動詞", "形容詞"}:
            while index < len(resolved):
                following = resolved[index]
                previous = members[-1]

                if following.token.start != previous.token.end:
                    break

                if token_category(following) != "助動詞":
                    break

                members.append(following)
                index += 1

        start = first.token.start
        end = members[-1].token.end

        groups.append(
            SentenceGroup(
                surface=text[start:end],
                start=start,
                end=end,
                tokens=tuple(members),
            )
        )

    return tuple(groups)
