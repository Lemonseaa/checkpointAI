# User Preference Plan

## Positioning

人的偏好、审美、风险原则和长期目标，必须由人定义。

Hermes 可以帮助总结，但不能自动写入正式偏好。Agent 只能读取正式偏好，不能修改正式偏好。

核心原则：

```text
USER_PROFILE.md = 人的长期原则
SUGGESTED_PROFILE_NOTES.md = Hermes 的草稿纸
Hermes = 总结助手
人 = 最终作者
```

## File Structure

第一版：

```text
Loop Harness/
└── user/
    ├── USER_PROFILE.md
    └── SUGGESTED_PROFILE_NOTES.md
```

未来按业务线扩展：

```text
business_lines/
├── quant/
│   ├── PROFILE.md
│   └── SUGGESTED_PROFILE_NOTES.md
└── content/
    ├── PROFILE.md
    └── SUGGESTED_PROFILE_NOTES.md
```

## File Roles

| File | Writer | Purpose | Can Agents Treat As Formal Preference |
|---|---|---|---|
| `user/USER_PROFILE.md` | Human | 正式偏好和长期原则 | Yes |
| `user/SUGGESTED_PROFILE_NOTES.md` | Hermes | 建议草稿和证据摘要 | No |
| `business_lines/{id}/PROFILE.md` | Human | 业务线级偏好 | Yes |
| `business_lines/{id}/SUGGESTED_PROFILE_NOTES.md` | Hermes | 业务线级建议草稿 | No |

## USER_PROFILE.md Template

```markdown
# User Profile

## Role

## Core Goals

## Decision Principles

## Aesthetic Preferences

## Content Preferences

## Risk Preferences

## Approval Preferences

## Business Preferences

## Forbidden

## Notes
```

这个文件是人的操作宪法，不是闲聊记忆。

## Hermes Summary Flow

Hermes 可以读取：

```text
DecisionLog
Approval comments
Rejected proposals
Accepted proposals
Validation summaries
Safety findings
Run reports
Historical conversations
Existing USER_PROFILE.md
```

然后生成：

```text
SUGGESTED_PROFILE_NOTES.md
```

标准流程：

```text
历史数据 / 审批记录 / 对话 / proposal / decision log
        ↓
Hermes 读取并总结
        ↓
生成“偏好建议草稿”
        ↓
人查看、修改、确认
        ↓
人手动写入 USER_PROFILE.md
```

Hermes 可以建议措辞，但不能替人确认偏好。

## Approval Comments As Evidence

审批评论、review package 决策、reject 理由都可以作为偏好证据。

但它们不是正式偏好本身。

允许用途：

```text
Hermes 总结“你似乎更重视回撤控制”
系统在 Approval Detail 中展示历史同类决策
人类根据历史评论手动更新 USER_PROFILE.md
```

禁止用途：

```text
根据一次 approve 自动降低风险阈值
根据一次 reject 自动禁止某类策略
把评论直接写入 USER_PROFILE.md
让 Agent 自动改写正式偏好
```

正确关系：

```text
approval comments = evidence
USER_PROFILE.md = policy-like preference source
human = only writer of formal preference
```

## Suggested Notes Format

```markdown
# Suggested Profile Notes

## Possible Preference: Conservative Quant Deployment

Evidence:
- You rejected 4 proposals involving live strategy changes.
- You repeatedly asked for historical/paper validation before deployment.
- You approved small parameter patches only after shadow comparison.

Suggested wording:
“量化交易中，任何实盘相关动作必须经过历史回测、模拟盘、人工确认三步。”

Status:
pending human review
```

## UI Design

页面：

```text
Settings -> User Profile
```

布局：

```text
Left: USER_PROFILE.md
Right: Hermes Suggested Notes
```

左侧功能：

```text
[Edit]
[Preview Diff]
[Save]
[View Version History]
```

右侧功能：

```text
[Ask Hermes to Summarize]
[Copy Suggested Text]
[Dismiss]
```

禁止提供：

```text
[Apply Hermes Suggestion]
```

原因：避免 Hermes 一键污染正式偏好。

## Versioning And Audit

每次保存 `USER_PROFILE.md`，系统必须记录：

```text
profile_version_id
before
after
diff
created_at
created_by = human
reason / comment
```

并写入：

```text
DecisionLog
```

这保证以后可以回答：

```text
什么时候改了偏好
为什么改
改了什么
```

## Agent Access Rules

硬规则：

```text
1. Hermes 可以读取 USER_PROFILE.md
2. Hermes 可以生成 SUGGESTED_PROFILE_NOTES.md
3. Hermes 不可以直接修改 USER_PROFILE.md
4. Agent 不可以修改 USER_PROFILE.md
5. USER_PROFILE.md 是正式偏好唯一来源
6. SUGGESTED_PROFILE_NOTES.md 不能作为正式约束
7. Agent context 注入只读取正式 profile
8. 所有 profile 保存必须产生 diff 和 DecisionLog
```

Agent 读取优先级：

```text
Global USER_PROFILE.md
  ↓
BusinessLine PROFILE.md
  ↓
Scenario config
```

下层可以更具体，但不能违反上层硬约束。

## Implementation Order

```text
V7.UI-Prefs.1
创建 user/USER_PROFILE.md 和 SUGGESTED_PROFILE_NOTES.md 模板

V7.UI-Prefs.2
实现 ProfileStore：读取、保存、版本、diff

V7.UI-Prefs.3
实现 Settings -> User Profile 页面

V7.UI-Prefs.4
实现 Hermes Suggested Notes 生成入口

V7.UI-Prefs.5
Agent context 注入时只读取 USER_PROFILE.md

V7.UI-Prefs.6
增加审计：每次保存写 DecisionLog
```

## Non-Goals

- 不让 Hermes 自动保存正式偏好
- 不让 Agent 自动修改正式偏好
- 不把 suggested notes 当正式约束
- 不做不可追踪的隐式记忆覆盖
- 不把 profile 存成只有机器好写、人不好读的 JSON/YAML
