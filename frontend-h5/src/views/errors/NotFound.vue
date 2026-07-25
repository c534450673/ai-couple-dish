<template>
  <main class="not-found-page">
    <p class="not-found-page__eyebrow">
      COUPLE COSMOS
    </p>
    <h1>页面不存在</h1>
    <p>这颗星球暂时没有你要找的坐标。</p>
    <router-link to="/home">
      返回星球
    </router-link>
  </main>
</template>

<style lang="scss" scoped>
.not-found-page {
  display: grid;
  min-height: 100vh;
  padding: $space-8 $page-padding;
  align-content: center;
  justify-items: center;
  gap: $space-3;
  color: $cosmos-text;
  background: $cosmos-bg;
  text-align: center;
}

.not-found-page__eyebrow { color: $cosmos-secondary; font-size: $fs-caption; }
.not-found-page h1 { font-size: $fs-display; }
.not-found-page p:not(.not-found-page__eyebrow) { color: $cosmos-text-muted; }
.not-found-page a { display: inline-grid; min-height: 44px; padding: 0 $space-5; place-items: center; border-radius: 6px; background: $cosmos-primary; color: #fff; text-decoration: none; }
</style>
