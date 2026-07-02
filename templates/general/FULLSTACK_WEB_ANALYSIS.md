# 全栈 Web 应用分析模板

> 🔍 分析前后端一体的全栈 Web 应用：前端架构、后端架构、API 层、数据层、部署架构

## 📋 适用场景

- Next.js / Nuxt / Remix / SvelteKit 等全栈框架项目
- 前后端分离但同一仓库的项目（monorepo）
- 包含前端 UI + 后端 API + 数据库的完整应用

**典型案例**: OpenDeepWiki (Next.js + .NET)、DeepWiki (Next.js + FastAPI)、Vercel AI SDK 示例

## 📋 核心问题清单

### 1. 前端架构

#### 1.1 框架与路由
- [ ] 使用什么前端框架？（Next.js / Nuxt / Remix / Vite+React）
- [ ] 路由模式？（App Router / Pages Router / File-based / Config-based）
- [ ] 路由分层？（公共页面 / 管理后台 / 用户中心 / API Routes）
- [ ] 是否使用动态路由？（[owner]/[repo] 模式）
- [ ] 中间件（Middleware）如何使用？（认证/重定向/国际化）

#### 1.2 组件设计
- [ ] 组件库选择？（shadcn/ui / Ant Design / MUI / 自研）
- [ ] 组件组织方式？（按功能/按类型/原子设计）
- [ ] 状态管理方案？（React hooks / Context / Zustand / Redux）
- [ ] 表单处理方案？（React Hook Form / Formik / 原生）

#### 1.3 渲染策略
- [ ] SSR / SSG / ISR / CSR 混合使用？
- [ ] 哪些页面静态生成？哪些动态渲染？
- [ ] 流式渲染（Streaming）是否使用？
- [ ] 首屏优化策略？（loading.tsx / suspense / skeleton）

#### 1.4 实时通信
- [ ] WebSocket 使用场景？（聊天/流式响应/实时更新）
- [ ] SSE (Server-Sent Events) 使用？
- [ ] 降级策略？（WebSocket → SSE → 轮询）
- [ ] 断线重连机制？

#### 1.5 样式与主题
- [ ] CSS 方案？（Tailwind / CSS Modules / Styled Components）
- [ ] 暗色模式支持？
- [ ] 响应式设计？
- [ ] 国际化（i18n）方案？

### 2. 后端架构

#### 2.1 API 设计
- [ ] API 风格？（RESTful / GraphQL / tRPC / MiniApi）
- [ ] API 路由组织？（按资源/按功能/声明式）
- [ ] 版本控制？（URL / Header / 无）
- [ ] API 文档？（Swagger / OpenAPI / 自动生成）

#### 2.2 请求处理
- [ ] 请求验证？（Zod / Joi / Pydantic / 内置）
- [ ] 错误处理统一？（全局异常处理器）
- [ ] 限流/防刷？
- [ ] 请求日志/追踪？

#### 2.3 服务层设计
- [ ] 业务逻辑分层？（Controller → Service → Repository）
- [ ] 依赖注入方式？
- [ ] 中间件管道？（认证 → 日志 → 压缩 → 路由）
- [ ] 后台任务/Worker 设计？

### 3. 数据层

#### 3.1 数据库
- [ ] 数据库选择？（PostgreSQL / MySQL / SQLite / MongoDB）
- [ ] ORM 选择？（EF Core / Prisma / Drizzle / SQLAlchemy / TypeORM）
- [ ] 数据库迁移管理？
- [ ] 多数据库支持？

#### 3.2 缓存
- [ ] 缓存层次？（内存缓存 / Redis / 浏览器缓存）
- [ ] 缓存策略？（TTL / LRU / 主动失效）
- [ ] 缓存键设计？
- [ ] 缓存预热？

#### 3.3 文件存储
- [ ] 文件存储方案？（本地 / S3 / OSS）
- [ ] 大文件处理？（分片上传/断点续传）
- [ ] 静态资源 CDN？

### 4. 前后端交互

#### 4.1 数据获取
- [ ] 数据获取方式？（fetch / axios / SWR / React Query / tRPC）
- [ ] 服务端数据获取？（Server Components / getServerSideProps）
- [ ] 客户端数据获取？（useEffect / hooks）
- [ ] 乐观更新？

#### 4.2 API 代理
- [ ] 是否有 API 代理层？（Next.js rewrites / Nginx）
- [ ] 跨域处理？（CORS / 代理）
- [ ] 统一错误处理？

#### 4.3 认证传递
- [ ] Token 传递方式？（Cookie / Header / localStorage）
- [ ] Session 管理？
- [ ] 刷新机制？

### 5. 部署架构

#### 5.1 容器化
- [ ] Docker 支持？（Dockerfile / docker-compose）
- [ ] 多阶段构建？
- [ ] 镜像大小优化？

#### 5.2 环境管理
- [ ] 环境变量管理？（.env / Vault / 配置中心）
- [ ] 多环境支持？（dev / staging / prod）
- [ ] 配置热更新？

#### 5.3 持久化
- [ ] 数据卷管理？
- [ ] 备份策略？
- [ ] 数据迁移方案？

### 6. SEO 与性能

#### 6.1 SEO
- [ ] Meta 标签管理？
- [ ] Sitemap 生成？
- [ ] Robots.txt？
- [ ] Open Graph / Twitter Card？
- [ ] 结构化数据（JSON-LD）？

#### 6.2 前端性能
- [ ] 代码分割？（动态 import / lazy loading）
- [ ] 图片优化？（next/image / WebP / 懒加载）
- [ ] Bundle 分析？
- [ ] Core Web Vitals 优化？

## 🔍 代码检查点

```bash
# 前端框架识别
rg "next|nuxt|remix|vite|svelte" package.json

# 路由结构
find . -path "*/app/*" -name "page.*" -o -path "*/pages/*" -name "*.tsx"

# API 路由
find . -path "*/api/*" -name "route.*" -o -path "*/endpoints/*"

# 组件库
rg "shadcn|antd|@mui|chakra-ui" package.json

# 数据库 ORM
rg "prisma|drizzle|@prisma/client|typeorm|sequelize" package.json
rg "sqlalchemy|django|peewee|tortoise" requirements.txt

# Docker
find . -name "Dockerfile*" -o -name "docker-compose*"

# 环境变量
find . -name ".env*" -not -path "*/node_modules/*"
```

## 📊 评估标准

| 维度 | 优秀 (5分) | 良好 (4分) | 一般 (3分) | 需改进 (1-2分) |
|------|-----------|-----------|-----------|---------------|
| **前端架构** | 现代框架+SSR+组件化 | 框架合理 | 基础实现 | 混乱 |
| **后端架构** | 分层清晰+中间件完善 | 分层合理 | 基础分层 | 无分层 |
| **数据层** | 多数据库+缓存层次 | ORM+缓存 | 基础存储 | 无抽象 |
| **前后端交互** | 统一数据层+降级策略 | 交互清晰 | 基础交互 | 混乱 |
| **部署架构** | Docker+CI/CD+多环境 | Docker 支持 | 基础部署 | 无部署 |
| **SEO/性能** | 全面优化 | 部分优化 | 基础优化 | 无优化 |

## 📝 分析输出模板

```markdown
# [项目名] - 全栈 Web 应用分析

## 1. 技术栈总览

| 层 | 技术 | 版本 |
|----|------|------|
| 前端框架 | Next.js 16 | App Router |
| UI 库 | React 19 + shadcn/ui | |
| 后端框架 | ASP.NET Core / FastAPI | |
| 数据库 | SQLite / PostgreSQL | EF Core |
| 缓存 | 内存 + localStorage | |
| 部署 | Docker Compose | |

## 2. 前端架构

### 路由设计
[路由树 + 说明]

### 核心页面
| 页面 | 路由 | 渲染方式 | 功能 |
|------|------|----------|------|
| 首页 | / | SSR | ... |
| 文档页 | /{owner}/{repo} | SSR + Streaming | ... |
| 管理后台 | /admin/* | CSR | ... |

### 组件架构
[组件树 + 状态管理]

## 3. 后端架构

### API 设计
| 端点 | 方法 | 功能 | 认证 |
|------|------|------|------|
| /api/repos | GET | 列表 | JWT |
| /api/wiki | POST | 生成 | JWT |

### 服务层
[服务依赖图]

### Worker/后台任务
| Worker | 职责 | 触发方式 |
|--------|------|----------|
| ProcessingWorker | 仓库处理 | 事件驱动 |
| TranslationWorker | 翻译 | 定时 |

## 4. 数据流

### 核心数据流
[端到端数据流图]

### 实时通信
[WebSocket/SSE 流程图]

## 5. 部署架构

### Docker Compose
[服务拓扑]

### 数据持久化
[卷/存储方案]

## 6. 设计亮点

- ✅ [亮点1]

## 7. 学习价值

- ⭐⭐⭐⭐⭐ [值得借鉴的设计]
```

## 8. 💡 设计洞察

> 从该项目的全栈 Web 架构中提炼的可移植原则

### 8.1 架构设计原则

**原则1**: [原则名称]
- **原理**: [为什么重要]
- **证据**: [项目中的具体实现]
- **适用范围**: [什么场景适用]
- **去名检验**: ✅/⚠️

示例:
> **原则**: 前后端分离应该彻底，而非半分离
>
> **原理**: 半分离（如服务端渲染 + 部分 AJAX）会导致维护困难，彻底分离让前后端可以独立部署和扩展
>
> **证据**: 项目使用 Next.js 纯前端 + FastAPI 纯后端，通过 REST API 通信
>
> **适用范围**: 中大型 Web 应用
>
> **去名检验**: ✅ 通用原则

### 8.2 数据流原则

**原则1**: [同上格式]

## 9. ⚠️ 隐含陷阱

> 从源码分析中发现的非显而易见的 Web 架构陷阱

### 9.1 状态管理陷阱

**陷阱1**: [陷阱名称]
- **现象**: [说明]
- **原因**: [说明]
- **正确做法**: [说明]

### 9.2 实时通信陷阱

**陷阱1**: [同上格式]

---

*模板版本: v2.0 - 增加设计洞察与隐含陷阱章节*
*最后更新: 2026-06-29*
