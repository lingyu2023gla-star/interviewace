# Rule-based Skill Router

V10.6 adds a lightweight rule-based router for selecting a registered Skill from user intent.

It does not execute the Skill. It only returns the recommended skill name, confidence, reason, and candidate scores.

## 1. Purpose

As the Skill Layer grows, callers need a simple way to map user intent to a skill.

Examples:

- “帮我做一份面试准备” -> `interview_preparation`
- “帮我整理项目讲解” -> `project_pitch`
- explicit `skill_name=project_pitch` -> `project_pitch`

The first version is deterministic and testable. It does not call an LLM.

## 2. SkillRouteRequest

| Field | Description |
| --- | --- |
| `text` | User request text |
| `explicit_skill_name` | Optional explicit skill name; this has priority |
| `metadata` | Optional routing context |

## 3. SkillRouteResult

| Field | Description |
| --- | --- |
| `selected_skill_name` | Recommended skill name, or `None` when no match |
| `confidence` | Float from 0 to 1 |
| `reason` | Human-readable routing reason |
| `candidates` | Candidate skill scores and matched signals |

## 4. RuleBasedSkillRouter

`RuleBasedSkillRouter` takes a `SkillRegistry`:

```python
router = RuleBasedSkillRouter(create_default_skill_registry())
result = router.route(SkillRouteRequest(text="帮我做项目讲解"))
```

Routing rules:

1. If `explicit_skill_name` exists and is registered, return it with `confidence=1.0`.
2. If `explicit_skill_name` exists but is not registered, return `selected_skill_name=None`.
3. Otherwise, normalize `text` and score registered skills by:
   - skill name match
   - tag match
   - predefined keyword match
   - simple description token match
4. Return the highest-scoring skill when score is greater than 0.
5. Return `None` when no skill matches.

The router never calls `skill.run()`.

## 5. Default Keywords

`interview_preparation`:

- `prepare`
- `preparation`
- `interview plan`
- `面试准备`
- `准备计划`
- `复习计划`

`project_pitch`:

- `project pitch`
- `project intro`
- `项目讲解`
- `项目介绍`
- `项目话术`
- `讲项目`

## 6. Boundaries

Current V10.6 does not implement:

- LLM-based router
- multi-step Agent Loop
- automatic skill execution
- API endpoint
- Celery task
- database persistence
- `skill_runs` table

## 7. Roadmap

Possible future extensions:

- LLM-based router
- intent classification eval cases
- route confidence thresholds per product surface
- fallback question when no skill matches
- Agent Loop that can route, run, inspect, and retry
