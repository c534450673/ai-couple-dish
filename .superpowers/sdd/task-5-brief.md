### Task 5: 重做美食库、菜谱和可恢复编辑器

**Files:**
- Modify: `frontend-h5/src/views/menu/index.vue`
- Modify: `frontend-h5/src/views/menu/detail.vue`
- Modify: `frontend-h5/src/views/menu/add.vue`
- Create: `frontend-h5/src/views/recipe/index.vue`
- Create: `frontend-h5/src/views/recipe/detail.vue`
- Modify: `frontend-h5/src/views/recipe/add.vue`
- Create: `frontend-h5/src/stores/menu.js`
- Create: `frontend-h5/src/stores/recipe.js`
- Create: `frontend-h5/src/composables/useDraft.js`
- Modify: `frontend-h5/src/api/index.js`
- Create: `frontend-h5/src/tests/stores/menu.spec.js`
- Create: `frontend-h5/src/tests/stores/recipe.spec.js`
- Create: `frontend-h5/src/tests/views/menu.spec.js`
- Create: `frontend-h5/src/tests/views/recipe.spec.js`

**Interfaces:**
- Produces: `useMenuStore()` and `useRecipeStore()` with list/detail/mutation states.
- Produces: `useDraft({ userId, resource, resourceId }) -> { draft, hasDraft, save, restore, clear }`.
- Produces: `recipeApi` in `src/api/index.js`; removes direct fetch from recipe view.

- [ ] **Step 1: 写列表、详情和草稿恢复失败测试**

覆盖搜索、筛选、分页、空态、单次重试、详情操作、图片上传失败、草稿恢复、离开提醒和成功后清草稿。草稿 key 精确为：

```js
`couple-cosmos:draft:${userId}:${resource}:${resourceId || 'new'}`
```

- [ ] **Step 2: 实现领域 Store 与 recipe API**

Store 将 API `{ code, data }` 归一为视图状态；mutation 成功只刷新相关实体。`recipe/add.vue` 不得保留 `fetch('/api/...')`。

- [ ] **Step 3: 按 Stitch 重做菜单页**

`menu-list.html` 对应 `/menu`，`menu-detail.html` 对应 `/menu/:id`；新增/编辑页复用设计系统表单而非复制详情卡。图片容器使用固定 aspect-ratio，失败有本地占位。

- [ ] **Step 4: 按 Stitch 实现菜谱页**

`recipe-list.html`、`recipe-detail.html`、`recipe-editor.html` 分别对应 `/recipes`、`/recipes/:id`、new/edit。食材与步骤编辑使用可排序列表和显式删除按钮，不用文本拼接存储结构化字段。

- [ ] **Step 5: 验证与提交**

```bash
cd frontend-h5
npm test -- --run src/tests/stores/menu.spec.js src/tests/stores/recipe.spec.js src/tests/views/menu.spec.js src/tests/views/recipe.spec.js
npm run build
git add src/views/menu src/views/recipe src/stores src/composables/useDraft.js src/api/index.js src/tests
git commit -m "feat: 重做Couple Cosmos美食库与菜谱"
```

