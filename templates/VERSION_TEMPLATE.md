# 分析版本记录

## 当前版本
- **版本**: v1.0
- **分析日期**: {DATE}
- **基于提交**: {COMMIT_HASH} ({COMMIT_SHORT})
- **提交日期**: {COMMIT_DATE}
- **提交消息**: {COMMIT_SUBJECT}
- **分支**: {BRANCH}
- **Tag**: {TAG}（如有）
- **分析深度**: Layer {1/2/3} / 递归深度分析
- **分析模型**: {MODEL}
- **文档数量**: {N} 个
- **总大小**: {SIZE}KB

## 历史版本

| 版本 | 日期 | Commit | 分支 | 变更说明 |
|------|------|--------|------|----------|
| v1.0 | {DATE} | {COMMIT_SHORT} | {BRANCH} | 初始分析 |

---

## 增量更新日志

### 增量分析流程

当项目有新提交时，按以下步骤进行增量分析：

```bash
# 1. 检查是否有更新
python3 $SKILL_DIR/scripts/commit-tracker.py status /path/to/project \
  --output-dir .

# 2. 查看详细变更
python3 $SKILL_DIR/scripts/commit-tracker.py diff /path/to/project \
  --output-dir . --show-stat

# 3. 对变更模块/文件重新分析（参考 diff 输出的模块变更列表）

# 4. 分析完成后，更新 commit 记录
python3 $SKILL_DIR/scripts/commit-tracker.py record /path/to/project \
  --output-dir . --analysis-mode recursive_deep
```

### 版本变更记录

#### v1.0 → v1.1 (待更新)
- **触发原因**: 
- **旧 Commit**: {COMMIT_SHORT}
- **新 Commit**: 
- **新增提交数**: 
- **变更文件**: +N ~N -N
- **影响模块**: 
- **影响文档**: 
- **更新状态**: 待执行
