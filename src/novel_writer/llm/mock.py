from __future__ import annotations

import re
from typing import Any

from novel_writer.llm.base import BaseLLMClient
from novel_writer.schema import StoryInput


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

    def generate_story_bible(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
        three_act_plot: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "schema_name": "story_bible",
            "schema_version": "1.0",
            "core_premise": logline.get("premise", ""),
            "ending_reveal": (
                three_act_plot.get("act_2", {}).get("midpoint")
                or three_act_plot.get("act_3", {}).get("resolution", "")
            ),
            "theme_statement": f"{story_input.theme} を通じて、{story_input.tone} に選び直しの価値を描く。",
            "character_arcs": [
                {
                    "name": character.get("name"),
                    "role": character.get("role"),
                    "goal": character.get("goal"),
                    "conflict": character.get("conflict"),
                    "arc": character.get("arc"),
                }
                for character in characters
            ],
            "world_rules": [
                f"{story_input.genre} としての約束を保ちつつ、{story_input.theme} に関わる異変は現実へ具体的な影響を与える。",
                f"作品全体のトーンは {story_input.tone} を維持し、過剰な喜劇化で緊張を逃がさない。",
            ],
            "forbidden_facts": [
                "序盤で ending_reveal の核心を明示しない。",
                "主人公の選択の代償をなかったことにしない。",
            ],
            "foreshadowing_seeds": [
                {
                    "id": "seed-1",
                    "setup": three_act_plot.get("act_1", {}).get("inciting_incident", ""),
                    "payoff_target": three_act_plot.get("act_2", {}).get("midpoint", ""),
                },
                {
                    "id": "seed-2",
                    "setup": logline.get("hook", ""),
                    "payoff_target": three_act_plot.get("act_3", {}).get("resolution", ""),
                },
            ],
        }

    def generate_chapter_plan(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
        three_act_plot: dict[str, Any],
        story_bible: dict[str, Any],
    ) -> list[dict[str, Any]]:
        target = max(3, min(6, story_input.target_length // 2000))
        chapters: list[dict[str, Any]] = []
        theme_statement = story_bible.get("theme_statement", "")
        ending_reveal = story_bible.get("ending_reveal", "")
        foreshadowing_seeds = story_bible.get("foreshadowing_seeds", [])
        beats = [
            ("導入", f"{three_act_plot['act_1']['setup']} テーマ命題: {theme_statement}"),
            ("転機", f"{three_act_plot['act_1']['inciting_incident']} 伏線: {foreshadowing_seeds[0].get('setup', '')}" if foreshadowing_seeds else three_act_plot["act_1"]["inciting_incident"]),
            ("対立", three_act_plot["act_2"]["rising_action"]),
            ("危機", f"{three_act_plot['act_2']['crisis']} 真相の影: {ending_reveal}"),
            ("結末", f"{three_act_plot['act_3']['resolution']} 回収: {ending_reveal}"),
            ("余韻", f"{logline['title']}の余波が静かに残る締め。命題: {theme_statement}"),
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

    def generate_chapter_briefs(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
        three_act_plot: dict[str, Any],
        story_bible: dict[str, Any],
        chapter_plan: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return [
            {
                "chapter_number": chapter["chapter_number"],
                "purpose": chapter["purpose"],
                "goal": f"{chapter['title']} で物語を前進させる",
                "conflict": "主人公の望みと外部圧力が衝突する",
                "turn": story_bible["ending_reveal"],
                "must_include": [seed["setup"] for seed in story_bible["foreshadowing_seeds"][:1]],
                "continuity_dependencies": [characters[0]["name"]],
                "foreshadowing_targets": [seed["id"] for seed in story_bible["foreshadowing_seeds"]],
                "arc_progress": characters[0]["arc"],
                "target_length_guidance": "standard" if chapter["target_words"] < 12000 else "heavy",
            }
            for chapter in chapter_plan
        ]

    def generate_scene_cards(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
        three_act_plot: dict[str, Any],
        story_bible: dict[str, Any],
        chapter_plan: list[dict[str, Any]],
        chapter_briefs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        packets = []
        for brief in chapter_briefs:
            chapter = chapter_plan[brief["chapter_number"] - 1]
            packets.append(
                {
                    "chapter_number": brief["chapter_number"],
                    "scenes": [
                        {
                            "chapter_number": brief["chapter_number"],
                            "scene_number": 1,
                            "scene_goal": brief["goal"],
                            "scene_conflict": brief["conflict"],
                            "scene_turn": "前提が崩れる",
                            "pov_character": chapter["point_of_view"],
                            "participants": [characters[0]["name"]],
                            "setting": "導入地点",
                            "must_include": brief["must_include"],
                            "continuity_refs": brief["continuity_dependencies"],
                            "foreshadowing_action": "seed",
                            "exit_state": brief["turn"],
                        },
                        {
                            "chapter_number": brief["chapter_number"],
                            "scene_number": 2,
                            "scene_goal": "対立を表面化させる",
                            "scene_conflict": brief["conflict"],
                            "scene_turn": "関係が不安定になる",
                            "pov_character": chapter["point_of_view"],
                            "participants": [characters[0]["name"], characters[1]["name"]],
                            "setting": "対立地点",
                            "must_include": brief["must_include"],
                            "continuity_refs": brief["continuity_dependencies"],
                            "foreshadowing_action": "progress",
                            "exit_state": "協力関係にひびが入る",
                        },
                        {
                            "chapter_number": brief["chapter_number"],
                            "scene_number": 3,
                            "scene_goal": "章の転換を確定する",
                            "scene_conflict": brief["conflict"],
                            "scene_turn": brief["turn"],
                            "pov_character": chapter["point_of_view"],
                            "participants": [characters[0]["name"]],
                            "setting": "転換地点",
                            "must_include": brief["must_include"],
                            "continuity_refs": brief["continuity_dependencies"],
                            "foreshadowing_action": "payoff_or_seed",
                            "exit_state": brief["turn"],
                        },
                    ],
                }
            )
        return packets

    def generate_chapter_draft(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        characters: list[dict[str, Any]],
        chapter_plan: list[dict[str, Any]],
        chapter_briefs: list[dict[str, Any]] | None = None,
        scene_cards: list[dict[str, Any]] | None = None,
        chapter_index: int = 0,
    ) -> dict[str, Any]:
        chapter = chapter_plan[chapter_index]
        protagonist = characters[0]["name"]
        brief = chapter_briefs[chapter_index] if chapter_briefs else None
        packet = scene_cards[chapter_index] if scene_cards else None
        return {
            "chapter_number": chapter["chapter_number"],
            "title": chapter["title"],
            "summary": brief["goal"] if brief else chapter["purpose"],
            "text": (
                f"{brief['purpose']}。{packet['scenes'][0]['exit_state']}へ向かう本文。"
                if brief and packet
                else (
                    f"{protagonist}はまだ夜の静けさに慣れずにいた。"
                    f"{story_input.theme}の気配は、窓を叩く風よりも近くで息をしている。"
                    f"目の前の選択は小さく見えて、その実、これから失うものすべてを量っていた。"
                    f"『{logline['title']}』の始まりとして、"
                    f"{story_input.tone}な空気と不穏な予感を前景に置いた導入を書く。"
                )
            ),
        }

    def revise_chapter_draft(
        self,
        story_input: StoryInput,
        chapter_plan: list[dict[str, Any]],
        chapter_draft: dict[str, Any],
        continuity_report: dict[str, Any],
        chapter_index: int = 0,
    ) -> dict[str, Any]:
        target_plan = chapter_plan[chapter_index] if chapter_plan else {}
        original_text = str(chapter_draft.get("text", ""))
        cleaned_text = self._dedupe_sentences(original_text)
        summary = str(target_plan.get("purpose") or chapter_draft.get("summary", ""))
        revised_text = cleaned_text
        if summary and summary not in revised_text:
            revised_text = f"{summary} {revised_text}".strip()
        revised_text = revised_text.replace("その実、", "").replace("不穏な予感を前景に置いた導入を書く。", "不穏さだけを残した。")
        revised_text = re.sub(r"\s+", " ", revised_text).strip()

        return {
            "chapter_number": chapter_draft.get("chapter_number"),
            "title": chapter_draft.get("title"),
            "summary": summary,
            "text": revised_text,
            "revision_notes": [
                f"chapter_plan[{chapter_index}] の purpose に summary を寄せた",
                "重複文を削減した",
                f"{story_input.tone}な文体に合わせて冗長表現を短くした",
            ],
            "chapter_index": chapter_index,
            "source_issue_counts": continuity_report.get("issue_counts", {}),
        }

    def generate_story_summary(
        self,
        story_input: StoryInput,
        logline: dict[str, Any],
        chapter_plan: list[dict[str, Any]],
        revised_chapter_drafts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        chapter_summaries = [
            {
                "chapter_number": chapter.get("chapter_number"),
                "title": chapter.get("title"),
                "summary": draft.get("summary", chapter.get("purpose", "")),
            }
            for chapter, draft in zip(chapter_plan, revised_chapter_drafts)
        ]
        synopsis = " ".join(
            summary["summary"]
            for summary in chapter_summaries
            if summary.get("summary")
        ).strip()
        return {
            "title": logline.get("title"),
            "theme": story_input.theme,
            "genre": story_input.genre,
            "tone": story_input.tone,
            "chapter_count": len(chapter_plan),
            "synopsis": synopsis,
            "chapter_summaries": chapter_summaries,
        }

    def _dedupe_sentences(self, text: str) -> str:
        parts = re.split(r"(?<=[。！？])", text)
        unique_parts: list[str] = []
        seen = set()
        for part in parts:
            normalized = part.strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique_parts.append(normalized)
        return "".join(unique_parts)
