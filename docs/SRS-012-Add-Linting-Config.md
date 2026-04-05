# SRS-012: 添加 ESLint 和 Prettier 配置

## 1. 需求背景

前端项目 `frontend-h5` 和 `frontend-uniapp` 虽然在 `package.json` 中添加了 ESLint 依赖，但缺少配置文件，导致：
- 代码风格不统一
- 无法进行自动化 lint 检查
- IDE 可能使用不同的默认配置

## 2. 当前问题

### 2.1 package.json 中的 ESLint 依赖

```json
{
  "devDependencies": {
    "eslint": "^8.57.0",
    // ...
  }
}
```

### 2.2 缺失的配置文件

- `.eslintrc.js` 或 `eslint.config.js`
- `.prettierrc`
- `.eslintignore`

### 2.3 问题影响

- 团队成员代码风格不一致
- 无法在 CI 中运行 lint 检查
- Git Hook 无法进行 pre-commit lint

## 3. 解决方案

### 3.1 安装额外依赖

```bash
npm install -D eslint prettier eslint-plugin-vue @vue/eslint-config-prettier
```

### 3.2 创建 ESLint 配置

**frontend-h5/.eslintrc.js**

```javascript
module.exports = {
  root: true,
  env: {
    browser: true,
    es2021: true,
    node: true,
  },
  extends: [
    'eslint:recommended',
    'plugin:vue/vue3-recommended',
    'plugin:prettier/recommended',
  ],
  parserOptions: {
    ecmaVersion: 2021,
    sourceType: 'module',
  },
  rules: {
    'vue/multi-word-component-names': 'off',
    'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
    'no-debugger': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
  },
}
```

**frontend-uniapp/.eslintrc.js**

类似配置，可能需要添加 uniApp 特定规则。

### 3.3 创建 Prettier 配置

**frontend-h5/.prettierrc**

```json
{
  "semi": false,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100,
  "bracketSpacing": true,
  "arrowParens": "avoid",
  "endOfLine": "lf",
  "vueIndentScriptAndStyle": false
}
```

### 3.4 创建 .eslintignore

```
node_modules/
dist/
*.min.js
*.css
/public/
```

### 3.5 添加 Git Hook（可选）

安装 `husky` 和 `lint-staged`：

```bash
npm install -D husky lint-staged
```

添加 `package.json` scripts：

```json
{
  "scripts": {
    "lint": "eslint src --ext .vue,.js,.jsx,.cjs,.mjs --fix",
    "prepare": "husky install"
  },
  "lint-staged": {
    "*.{vue,js,jsx,mjs}": "eslint --fix"
  }
}
```

添加 `.husky/pre-commit`：

```bash
#!/bin/sh
. "$(dirname "$0")/_/husky.sh"

npx lint-staged
```

## 4. 验收标准

- [ ] `frontend-h5/.eslintrc.js` 存在并配置正确
- [ ] `frontend-h5/.prettierrc` 存在并配置正确
- [ ] `frontend-uniapp/.eslintrc.js` 存在并配置正确
- [ ] `.eslintignore` 文件存在
- [ ] `npm run lint` 命令可执行
- [ ] CI 中添加 lint 检查步骤（如有 CI）
- [ ] Husky Git Hook 配置完成（如采用）

## 5. 影响范围

- `frontend-h5/` - 新增配置文件
- `frontend-uniapp/` - 新增配置文件

## 6. 优先级

**P2** - 低优先级

## 7. 预计工时

2-3 小时
