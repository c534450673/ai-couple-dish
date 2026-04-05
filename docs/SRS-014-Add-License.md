# SRS-014: 添加开源许可证文件

## 1. 需求背景

项目缺少开源许可证文件（LICENSE），这会导致：
- 法律上项目状态不明确
- 其他开发者不清楚如何使用该项目
- 无法明确贡献者权利
- 不利于项目推广和开源

## 2. 当前问题

- 项目根目录缺少 `LICENSE` 文件
- README 中引用了 MIT License 但文件不存在
- 缺少 `CONTRIBUTING.md` 贡献指南

## 3. 解决方案

### 3.1 选择许可证

推荐使用 **MIT License**，原因：
- 简单易理解
- 商业友好
- 被广泛使用
- Vue、React 等项目都在用

### 3.2 创建 LICENSE 文件

**位置**: `/Users/zhangsubo/ai-couple-dish/LICENSE`

```markdown
MIT License

Copyright (c) 2024 AI Couple Dish

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### 3.3 创建 CONTRIBUTING.md

**位置**: `/Users/zhangsubo/ai-couple-dish/CONTRIBUTING.md`

```markdown
# 贡献指南

感谢您对 AI Couple Dish 项目的兴趣！欢迎贡献您的力量。

## 如何贡献

### 报告 Bug

请通过 GitHub Issues 报告 bug，包含：
- 清晰的问题描述
- 复现步骤
- 预期行为
- 实际行为
- 环境信息

### 提交代码

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. Push 到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### 代码规范

- 遵循项目现有的代码风格
- 为新功能添加单元测试
- 确保所有测试通过
- 更新相关文档

## 开发环境

详见 [README.md](README.md) 和 [docs/](docs/)

## 许可证

贡献的代码将使用 MIT 许可证。
```

## 4. 验收标准

- [ ] 根目录存在 `LICENSE` 文件
- [ ] LICENSE 年份和项目名称正确
- [ ] 存在 `CONTRIBUTING.md` 文件
- [ ] README 中 LICENSE badge 正确
- [ ] 文件使用 UTF-8 编码

## 5. 影响范围

- 新建 `/LICENSE`
- 新建 `/CONTRIBUTING.md`

## 6. 优先级

**P3** - 低优先级

## 7. 预计工时

1 小时
