# reading 图解项目设计与实施计划

**目标：** 将已批准的图解阅读路线落实到 reading 阶段，以已有材料解释项目全景、运行过程与核心原理。

**设计：** 采用三层阅读目录内的图解页，加一个导读入口。相比集中复制所有图到新目录，这样可保留页面来源追踪并避免多份维护；相比仅在普通文档中零散配图，可以显式组织学习顺序。入口使用 `reading/overview/visual-guide.md`，遵循现有正文目录校验。无需增加运行参数或修改来源 schema。

**技术：** Markdown、Mermaid，布局图按需用 ASCII / SVG；复用阶段来源指纹与图表检查工具。

## 实施步骤

1. 更新 `SKILL.md` 与 `guides/READING_SYNTHESIS.md`：路由、触发边界、预算和验收入口。
2. 新建 `guides/READING_VISUAL_GUIDE.md` 与 `templates/reading/VISUAL_EXPLANATION.md`：图解路线、图文单元、来源与增量维护。
3. 更新 `templates/reading/OUTPUT_SPEC.md`、通用图表指南与 README，说明目录兼容和模式边界。
4. 运行 skill lint、quick_validate、差异空白检查；检查新文档链接与现有 reading 来源协议一致。文档修改无需新增行为测试；不把静态检查报告为项目实测。

## 完成标准

普通整理不被强制追加整套图解；用户请求图解时能找到专用指引。图解页计入现有预算并登记底稿依赖；材料不足转为待研究问题，不能自动扩大源码分析。图形语法、渲染结果和论断正确性分别报告。

## 实施记录

- 保留已有 `scripts/evidence-check.py` 工作区修改。
- 根据用户追加要求，以理解目标优先，增加贯穿案例、不变量、推演检查和定向补证循环；原页数作为可调整的起始预算。
- 同步 `scripts/analysis_stages.py` 的准备计划文案，避免生成旧的硬性篇数限制。运行既有阶段测试检查准备与验收兼容性。
- 图解入口采用 overview 子目录，现有验证器无需新增目录豁免。
