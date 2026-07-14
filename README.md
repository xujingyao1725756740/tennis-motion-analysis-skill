# Tennis Motion Analysis Skill

面向 Codex 和其他 AI 编程代理的网球动作逐帧分析 Skill。

它可以辅助完成：

- 上传视频的逐帧检查与有效击球识别；
- MediaPipe 姿态点提取；
- 正手、反手等击球的六阶段标记；
- 与德约科维奇或其他参考球员进行阶段对齐比较；
- 6–8 维训练评分与雷达图；
- 谨慎限定范围的 NTRP-like 水平估计；
- HTML 动作报告与抖音/TikTok/Shorts 短视频工作流。

> 计算机视觉只作为测量辅助。本项目不提供医疗诊断，也不能用单个动作代替正式 NTRP、UTR 或 WTN 评级。

## 安装

### Codex

```bash
git clone https://github.com/xujingyao1725756740/tennis-motion-analysis-skill.git \
  ~/.codex/skills/tennis-motion-analysis
```

重启 Codex 后，可在提示词中使用：

```text
请用 tennis-motion-analysis skill 逐帧分析我的正手视频，给出评分、水平范围和三项训练建议。
```

### 其他 Agent

把仓库克隆到该 Agent 的 skills 目录，并确保 `SKILL.md` 位于技能根目录。

## 首次运行

需要 Python 3.9+。运行下面的脚本会在技能目录创建隔离的 `.venv`，安装依赖，并从 MediaPipe 官方存储下载姿态模型：

```bash
python3 scripts/bootstrap_runtime.py
```

只检查运行环境，不安装：

```bash
python3 scripts/bootstrap_runtime.py --check
```

如需生成或检查视频，建议另外安装 FFmpeg。社交短视频的最终制作由 Agent 调用其可用的视频渲染 Skill 完成。

## 命令示例

提取姿态点：

```bash
.venv/bin/python scripts/tennis_motion.py extract player.mp4 \
  --out player.pose.json
```

生成待人工确认的正手阶段：

```bash
.venv/bin/python scripts/tennis_motion.py suggest-phases player.pose.json \
  --stroke forehand --hand right --out player.phases.json
```

比较两个已确认阶段的视频：

```bash
.venv/bin/python scripts/tennis_motion.py compare \
  player.pose.json reference.pose.json \
  --user-phases player.phases.json \
  --reference-phases reference.phases.json \
  --stroke forehand --hand right --out-dir analysis
```

生成雷达图：

```bash
.venv/bin/python scripts/tennis_motion.py scorecard examples/scores.example.json \
  --out-svg analysis/radar.svg \
  --out-summary analysis/scorecard.json
```

完整参数：

```bash
.venv/bin/python scripts/tennis_motion.py --help
```

## 分析原则

1. 先检查机位、帧率、遮挡、球拍和球是否可见。
2. 按动作阶段对齐，不按视频绝对时间硬对齐。
3. 接触帧必须人工确认，不能只依靠手腕速度峰值。
4. 不跨机位直接比较绝对二维角度。
5. 把训练评分与球员等级分开。
6. 最多给三项修改，每项包含口令、练习和可测复测标准。
7. 公开报告不得直接嵌入没有再利用许可的职业球员视频。

详细规范位于 [`references/`](references/)；入口说明见 [`SKILL.md`](SKILL.md)。

## 仓库内容

```text
SKILL.md
agents/openai.yaml
scripts/bootstrap_runtime.py
scripts/tennis_motion.py
references/analysis-protocol.md
references/scoring-ratings.md
references/report-rubric.md
references/publishing-workflow.md
examples/scores.example.json
```

本仓库不包含用户视频、私人报告、本机虚拟环境或下载后的姿态模型。

## License

MIT。第三方依赖和运行时下载的 MediaPipe 模型遵循其各自许可。
