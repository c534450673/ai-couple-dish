# SRS-013: 完善 .gitignore 配置

## 1. 需求背景

当前项目的 `.gitignore` 可能不完善，导致以下问题：
- IDE 配置文件（如 `.idea/`）已提交
- 编译产物未忽略
- 环境配置文件可能被误提交
- 临时文件占用仓库空间

## 2. 当前问题

### 2.1 Git Status 显示的问题

```
?? .DS_Store
?? .idea/
```

### 2.2 需要忽略的文件类型

| 类型 | 示例 | 说明 |
|------|------|------|
| IDE 配置 | `.idea/`, `.vscode/`, `*.iml` | IDE 设置 |
| 系统文件 | `.DS_Store`, `Thumbs.db` | 操作系统生成 |
| 构建产物 | `dist/`, `build/`, `target/` | 编译生成 |
| 依赖目录 | `node_modules/`, `.m2/` | 第三方库 |
| 环境配置 | `.env`, `*.local.yml` | 包含敏感信息 |
| 日志文件 | `*.log`, `logs/` | 运行日志 |
| 临时文件 | `*.tmp`, `*.swp` | 编辑器生成 |
| 微信小程序编译 | `unpackage/` | UniApp 编译产物 |

## 3. 解决方案

### 3.1 创建/更新根目录 .gitignore

**位置**: `/Users/zhangsubo/ai-couple-dish/.gitignore`

```gitignore
# ===================
# 系统和 IDE
# ===================
.DS_Store
Thumbs.db
*.swp
*.swo
*~

.idea/
*.iml
.vscode/
*.iws
*.ipr
.project
.classpath

# ===================
# 构建产物
# ===================
dist/
build/
target/
out/
*.class
*.jar
*.war
*.ear

# ===================
# 依赖目录
# ===================
node_modules/
bower_components/
.m2/
.npm/
.yarn/

# ===================
# 环境配置（勿提交）
# ===================
.env
.env.local
.env.*.local
*.local.yml
secrets/
credentials/

# ===================
# 日志和临时文件
# ===================
*.log
logs/
temp/
tmp/

# ===================
# 小程序和 UniApp
# ===================
unpackage/
*.uni.bundle
miniprogram_npm/

# ===================
# 测试覆盖率
# ===================
coverage/
.nyc_output/

# ===================
# 其他
# ===================
*.tgz
*.zip
*.tar.gz
```

### 3.2 子目录 .gitignore

在 `frontend-h5/` 和 `frontend-uniapp/` 添加各自的忽略规则。

**frontend-h5/.gitignore**
```gitignore
dist/
node_modules/
*.local
.env.local
```

**frontend-uniapp/.gitignore**
```gitignore
unpackage/
node_modules/
*.local
```

## 4. 验收标准

- [ ] 根目录 `.gitignore` 包含所有必要规则
- [ ] `.idea/` 已添加到忽略列表
- [ ] `.DS_Store` 已添加到忽略列表
- [ ] 依赖目录（node_modules, .m2）已添加
- [ ] 环境配置文件已添加
- [ ] 前端子目录有独立的 `.gitignore`
- [ ] 执行 `git status` 确认无遗漏的应忽略文件

## 5. 影响范围

- 根目录 `.gitignore`
- `frontend-h5/.gitignore`
- `frontend-uniapp/.gitignore`

## 6. 优先级

**P3** - 低优先级

## 7. 预计工时

1 小时
