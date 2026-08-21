# Mermaid 图表检验规则

> 配合 `scripts/mermaid-validator.py` 使用，确保生成的 Mermaid 图表语法正确、可渲染。

---

## 检验规则

### 错误级别（会导致渲染失败）

| 规则 | 说明 | 示例 | 修复 |
|------|------|------|------|
| **INVALID_TYPE** | 未知的图表类型声明 | `foo TD` | 使用 `flowchart TD` 等合法类型 |
| **UNCLOSED_BLOCK** | 代码块缺少结束的 ```` ``` ```` | — | 在末尾添加 ```` ``` ```` |
| **MISSING_END** | subgraph 缺少对应的 end | `subgraph A` 无 `end` | 添加 `end` |
| **EXTRA_END** | 多余的 end | 只有 `end` 无 `subgraph` | 移除多余的 `end` |
| **UNDEFINED_NODE_STYLE** | style 引用了未定义的节点 | `style C fill:#f9f` 但 C 未定义 | 先定义节点或移除 style |
| **MMDC_ERROR** | mermaid CLI 报错 | 各种语法错误 | 按 CLI 错误信息修复 |

### 警告级别（可能渲染异常）

| 规则 | 说明 | 示例 | 修复 |
|------|------|------|------|
| **UNESCAPED_PARENS** | 节点文本中的括号未转义 | `A[Node (info)]` | 用引号包裹: `A["Node (info)"]` |
| **NESTED_QUOTES** | 节点文本中嵌套引号 | `A["say "hi""]` | 用 `&quot;` 替代内部引号 |
| **FULLWIDTH_CHARS** | 全角字符 | `A（开始）` | 替换为半角 `A(开始)` |
| **TAB_INDENT** | Tab 缩进 | `\tA --> B` | 替换 Tab 为空格 |
| **INVALID_RELATION** | classDiagram 无效关系 | `A -- B` | 使用 `<|--`、`..|>` 等 |
| **PARTICIPANT_SPACE** | participant 名称含空格 | `participant My Name` | `participant My as "My Name"` |
| **NO_MESSAGES** | sequenceDiagram 无消息 | 只有 participant 声明 | 添加 `A->>B: 消息` |
| **DOUBLE_SEMICOLON** | 行尾多余分号 | `A --> B;;` | 移除多余 `;` |

---

## 常见错误模式

### 1. 节点文本包含括号

```mermaid
❌ 错误
flowchart TD
    A[Node (with parens)] --> B[End]

✅ 正确
flowchart TD
    A["Node (with parens)"] --> B[End]
```

### 2. subgraph 未闭合

```mermaid
❌ 错误
flowchart TD
    subgraph Group1
    A --> B
    C --> D
    %% 忘记 end

✅ 正确
flowchart TD
    subgraph Group1
    A --> B
    C --> D
    end
```

### 3. 全角字符

```mermaid
❌ 错误（某些渲染器不支持）
flowchart TD
    A［开始］--> B（处理）

✅ 正确
flowchart TD
    A["开始"] --> B["处理"]
```

### 4. classDiagram 无效关系

```mermaid
❌ 错误
classDiagram
    ClassA -- ClassB

✅ 正确
classDiagram
    ClassA <|-- ClassB
```

---

## 使用方法

```bash
# 检查单个文件
python3 scripts/mermaid-validator.py path/to/file.md

# 递归检查目录
python3 scripts/mermaid-validator.py path/to/analysis/ --recursive

# 保存报告
python3 scripts/mermaid-validator.py path/to/analysis/ -o mermaid-report.md

# 使用 mermaid CLI 深度验证（需要先安装 mmdc）
npm install -g @mermaid-js/mermaid-cli
python3 scripts/mermaid-validator.py path/to/file.md --use-mmdc
```

---
