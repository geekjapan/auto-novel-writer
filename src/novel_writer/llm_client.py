from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Any

from novel_writer.schema import StoryInput


class BaseLLMClient(ABC):
    @abstractmethod
    def generate_loglines(self, story_input: StoryInput) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def generate_characters(self, story_input: StoryInput, logline: dict[str, Any]) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def generate_three_act_plot(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
    ) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def generate_chapter_plan(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
        three_act_plot: dict[str, Any],
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def generate_chapter_draft(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
        chapter_plan: list[dict[str, Any]],
        chapter_index: int = 0,
    ) -> dict[str, Any]:
        raise NotImplementedError


class MockLLMClient(BaseLLMClient):
    def generate_loglines(self, story_input: StoryInput) -> list[dict[str, Any]]:
        base = f"{story_input.theme}をめぐる{story_input.genre}短編"
        return [
            {
                "id": "logline-1",
                "title": "鏡の中の約束",
                "premise": f"{base}。静かな主人公が一度だけ大きな選択を迫られる。",
                "hook": f"{story_input.tone}な読後感を残す、秘密と決断の物語。",
            },
            {
                "id": "logline-2",
                "title": "雨粒の証言",
                "premise": f"{story_input.theme}を抱えた若者が、小さな町の異変を追う。",
                "hook": f"{story_input.tone}さを保ちながら、人間関係の綻びを描く。",
            },
            {
                "id": "logline-3",
                "title": "最後の灯り",
                "premise": f"{story_input.genre}の枠組みで、失われたものと向き合う一夜の出来事。",
                "hook": f"目標文字数{story_input.target_length}字を想定した密度の高い短編案。",
            },
        ]

    def generate_characters(self, story_input: StoryInput, logline: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            {
                "name": "篠崎 遥",
                "role": "protagonist",
                "goal": f"{story_input.theme}に対する自分の答えを見つける",
                "conflict": "本音を語ると大切な関係が壊れると恐れている",
                "arc": "受け身から能動へ",
            },
            {
                "name": "木崎 蓮",
                "role": "foil",
                "goal": "現実的な解決策で状況を収束させたい",
                "conflict": "主人公の感情的な選択を理解できない",
                "arc": "合理性だけでは救えないものを認める",
            },
            {
                "name": "水守 透子",
                "role": "catalyst",
                "goal": f"『{logline['title']}』の核心となる秘密を明かす",
                "conflict": "真実を話すと自分の居場所も失う",
                "arc": "沈黙から告白へ",
            },
        ]

    def generate_three_act_plot(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
    ) -> dict[str, Any]:
        protagonist = characters[0]["name"]
        return {
            "act_1": {
                "setup": f"{protagonist}は{story_input.theme}に関する未解決の問題を抱えながら日常を送っている。",
                "inciting_incident": f"{logline['title']}につながる異変が起き、後戻りできなくなる。",
            },
            "act_2": {
                "rising_action": "協力と対立を繰り返しながら、真相に近づくほど人間関係が揺らぐ。",
                "midpoint": "主人公自身が問題の一端を担っていたと知る。",
                "crisis": "秘密を守るか、誰かを救うために公にするかで板挟みになる。",
            },
            "act_3": {
                "climax": f"{story_input.tone}な雰囲気の中で、主人公が自分の意思で選択を下す。",
                "resolution": "代償を払いながらも、新しい関係と次の一歩を手に入れる。",
            },
        }

    def generate_chapter_plan(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
        three_act_plot: dict[str, Any],
    ) -> list[dict[str, Any]]:
        target = max(3, min(6, story_input.target_length // 2000))
        chapters: list[dict[str, Any]] = []
        beats = [
            ("導入", three_act_plot["act_1"]["setup"]),
            ("転機", three_act_plot["act_1"]["inciting_incident"]),
            ("対立", three_act_plot["act_2"]["rising_action"]),
            ("危機", three_act_plot["act_2"]["crisis"]),
            ("結末", three_act_plot["act_3"]["resolution"]),
            ("余韻", f"{logline['title']}の余波が静かに残る締め。"),
        ]
        for index in range(target):
            heading, purpose = beats[index]
            chapters.append(
                {
                    "chapter_number": index + 1,
                    "title": f"第{index + 1}章 {heading}",
                    "purpose": purpose,
                    "point_of_view": characters[0]["name"],
                    "target_words": max(800, story_input.target_length // target),
                }
            )
        return chapters

    def generate_chapter_draft(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
        chapter_plan: list[dict[str, Any]],
        chapter_index: int = 0,
    ) -> dict[str, Any]:
        chapter = chapter_plan[chapter_index]
        protagonist = characters[0]["name"]
        return {
            "chapter_number": chapter["chapter_number"],
            "title": chapter["title"],
            "summary": chapter["purpose"],
            "text": (
                f"{protagonist}はまだ夜の静けさに慣れずにいた。"
                f"{story_input.theme}の気配は、窓を叩く風よりも近くで息をしている。"
                f"目の前の選択は小さく見えて、その実、これから失うものすべてを量っていた。"
                f"『{logline['title']}』の始まりとして、"
                f"{story_input.tone}な空気と不穏な予感を前景に置いた導入を書く。"
            ),
        }


class OpenAIClient(BaseLLMClient):
    def __init__(self, model: str = "gpt-4.1-mini") -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("OpenAI provider requires the openai package to be installed.") from exc

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set.")

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def _generate_json(self, system_prompt: str, user_prompt: str) -> Any:
        response = self._client.chat.completions.create(
            model=self._model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        content = response.choices[0].message.content or "{}"
        return json.loads(content)

    def generate_loglines(self, story_input: StoryInput) -> list[dict[str, Any]]:
        data = self._generate_json(
            "You generate concise short-story planning assets in Japanese.",
            (
                "Return JSON with key 'loglines' as an array of 3 items. "
                f"theme={story_input.theme}, genre={story_input.genre}, "
                f"tone={story_input.tone}, target_length={story_input.target_length}"
            ),
        )
        return data["loglines"]

    def generate_characters(self, story_input: StoryInput, logline: dict[str, Any]) -> list[dict[str, Any]]:
        data = self._generate_json(
            "You generate concise character sheets in Japanese.",
            (
                "Return JSON with key 'characters' as an array of 3 items. "
                f"story={story_input.to_dict()}, logline={json.dumps(logline, ensure_ascii=False)}"
            ),
        )
        return data["characters"]

    def generate_three_act_plot(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
    ) -> dict[str, Any]:
        data = self._generate_json(
            "You generate a three-act plot in Japanese.",
            (
                "Return JSON with key 'three_act_plot'. "
                f"story={story_input.to_dict()}, logline={json.dumps(logline, ensure_ascii=False)}, "
                f"characters={json.dumps(characters, ensure_ascii=False)}"
            ),
        )
        return data["three_act_plot"]

    def generate_chapter_plan(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
        three_act_plot: dict[str, Any],
    ) -> list[dict[str, Any]]:
        data = self._generate_json(
            "You generate a short chapter plan in Japanese.",
            (
                "Return JSON with key 'chapter_plan' as an array. "
                f"story={story_input.to_dict()}, logline={json.dumps(logline, ensure_ascii=False)}, "
                f"characters={json.dumps(characters, ensure_ascii=False)}, "
                f"plot={json.dumps(three_act_plot, ensure_ascii=False)}"
            ),
        )
        return data["chapter_plan"]

    def generate_chapter_draft(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
        chapter_plan: list[dict[str, Any]],
        chapter_index: int = 0,
    ) -> dict[str, Any]:
        data = self._generate_json(
            "You generate a first chapter draft in Japanese.",
            (
                "Return JSON with key 'chapter_1_draft'. "
                f"story={story_input.to_dict()}, logline={json.dumps(logline, ensure_ascii=False)}, "
                f"characters={json.dumps(characters, ensure_ascii=False)}, "
                f"chapter_plan={json.dumps(chapter_plan, ensure_ascii=False)}, "
                f"chapter_index={chapter_index}"
            ),
        )
        return data["chapter_1_draft"]


def build_llm_client(provider: str, model: str = "gpt-4.1-mini") -> BaseLLMClient:
    normalized = provider.lower()
    if normalized == "mock":
        return MockLLMClient()
    if normalized == "openai":
        return OpenAIClient(model=model)
    raise ValueError(f"Unsupported provider: {provider}")

