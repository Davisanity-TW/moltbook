import { defineConfig } from 'vitepress'
import { readdirSync, existsSync } from 'node:fs'
import { join } from 'node:path'

function listDirNames(dirFromDocsRoot: string) {
  const abs = join(process.cwd(), 'docs', dirFromDocsRoot)
  if (!existsSync(abs)) return []
  return readdirSync(abs, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name)
}

function listMdBasenames(dirFromDocsRoot: string) {
  const abs = join(process.cwd(), 'docs', dirFromDocsRoot)
  if (!existsSync(abs)) return []
  return readdirSync(abs)
    .filter((f) => f.endsWith('.md'))
    .map((f) => f.replace(/\.md$/, ''))
    .filter((name) => name !== 'index')
}

function makeItems(prefix: string, dirFromDocsRoot: string, limit = 62) {
  const names = listMdBasenames(dirFromDocsRoot).sort().reverse().slice(0, limit)
  return names.map((name) => ({ text: name, link: `/${prefix}/${name}` }))
}

function makeMonthGroups(limitMonths = 24) {
  const root = 'reports'
  const months = listDirNames(root).sort().reverse().slice(0, limitMonths)
  return months.map((m) => ({
    text: m,
    collapsed: true,
    items: makeItems(`reports/${m}`, `${root}/${m}`, 62)
  }))
}

export default defineConfig({
  lang: 'zh-Hant',
  title: 'Moltbook Digests',
  description: 'Moltbook 有趣文章精選（繁中摘要 + 可複製任務）',
  base: '/moltbook/',
  themeConfig: {
    nav: [
      { text: 'Home', link: '/' },
      { text: 'GitHub Repo', link: 'https://github.com/Davisanity-TW/moltbook' }
    ],
    sidebar: [
      {
        text: 'Digests',
        items: [
          ...makeMonthGroups(36)
        ]
      }
    ]
  }
})
