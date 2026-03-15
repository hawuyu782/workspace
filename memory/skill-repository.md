# 技能仓库说明

## 仓库信息

- **GitHub**: https://github.com/hawuyu782/workspace
- **用途**: 技能仓库，存放 OpenClaw 技能和自动化脚本
- **分支**: master

## Workflow

### Release Workflow

**触发条件**: 推送 `v*` 标签

**功能**:
- 自动打包 workspace 文件
- 生成 release 产物
- 上传 zip/tar.gz 文件

**使用方法**:
```bash
# 1. 修改代码
# 2. 提交并推送
git add .
git commit -m "feat: 更新 xxx"
git push

# 3. 打标签发布
git tag v1.0.0
git push --tags
```

## 维护任务

- [ ] 更新 Workflow 配置
- [ ] 添加新技能
- [ ] 维护发布流程
- [ ] 更新文档

## 文件结构

```
.github/workflows/release.yml  # 发布 Workflow
skills/                       # 技能目录
scripts/                     # 脚本目录
memory/                      # 记忆文件
```

---

*最后更新: 2026-02-25*
